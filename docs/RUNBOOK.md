# 운영 가이드 — 구동 방식과 구성 요소

새 포드에서 이 저장소만으로 같은 환경을 재현하고 운영하기 위한 문서다.

## 1. 새 포드 구축

```bash
export GITHUB_TOKEN="ghp_xxx"    # 비공개 Runpod-Backup 에서 rclone 인증을 가져오려면 필수
curl -sL https://raw.githubusercontent.com/castle923/AutoRunpod/main/scripts/bootstrap_pod.sh | bash
```

`bootstrap_pod.sh` 한 번으로 아래가 끝난다.

| 단계 | 내용 |
|---|---|
| 1 | git HTTP/1.1 설정 (구버전 git 의 GitHub clone 실패 회피) |
| 2 | AutoRunpod 클론 |
| 3 | 비공개 Runpod-Backup 에서 `secrets/rclone.conf` 를 가져와 배치 |
| 4 | `config.json` / `ui-config.json` 배치 |
| 5 | `scripts/`, `dynamic_prompts/` 배치 |
| 6 | `submit_job.py` 의 포드 URL 을 현재 포드로 치환 |
| 6-2 | **리스너 서버 + `restart_forge_clean.sh` 배치** |
| 6-3 | **nginx 설정 배치 (Gradio SSE 블록 포함) 후 reload** |
| 6-4 | `rclone.conf` 를 `/workspace` 에도 복사 |
| 7 | crontab 등록 |
| 8 | `auto_restore_on_boot.sh` 즉시 1회 실행 (LoRA/체크포인트 복원 시작) |
| 9 | **리스너 기동 및 `:5000/health` 응답 확인** |

`GITHUB_TOKEN` 이 새면 이 저장소에 접근 가능한 누구나 사용자의 구글 드라이브 전체에
접근할 수 있는 refresh_token 을 얻는다. 환경변수로만 전달하고 로그·커밋·공개 채널에
남기지 않는다.

## 2. 서비스 구성

| 포트 | 프로세스 | 역할 |
|---|---|---|
| 3001 | Forge | WebUI 본체 (`--listen --api --xformers --no-half-vae`) |
| 3000 | nginx | 3001 리버스 프록시 → `https://{POD_ID}-3000.proxy.runpod.net` |
| 8888 | jupyter-lab | 원격 제어 채널 |
| 5000 | 리스너 | 감시 · 자동복구 · 업로드 API |

## 3. 원격 조작

SSH 없이 `scripts/jupyter_exec.py` 로 포드 안에서 파이썬을 실행한다.

```bash
POD_ID=xyru66nh4emucs python3 scripts/jupyter_exec.py 'print(1)'
cat some_script.py | python3 scripts/jupyter_exec.py
```

Jupyter REST API 는 토큰 없이 `_xsrf` 쿠키만으로 커널을 만들 수 있다. 커널을 닫지
않으면 계속 쌓이므로 `auto_clean_kernels.py` 가 20분 이상 유휴인 것을 정리한다.

상태 확인은 포드에서 직접 하는 편이 가볍다.

```bash
curl -s localhost:5000/status
```

## 4. 리스너 서버 (`listener/server.py`)

포드에서 유일하게 Forge 를 되살리는 주체다. tmux 세션 `listener` 안에서
`while true` 루프로 돌아 프로세스가 죽어도 3초 뒤 다시 뜬다.

### 스레드 3개

| 스레드 | 주기 | 하는 일 |
|---|---|---|
| `monitor_forge_process` | 5초 | 프로세스·API·고착 감시 후 재시작 |
| `monitor_batch_progress` | 5초 | 배치 진행률, 시작 인덱스, 완료/중단 판별 |
| `monitor_memory` | 30초 | 컨테이너 메모리 감시 |

### 임계값

| 감시 항목 | 임계값 | 동작 |
|---|---|---|
| 프로세스 실종 | 2회 연속 **+ API 도 무응답** | 재시작 |
| API 무응답 | 6회 × 5초 = 30초 | 재시작 |
| interrupted 고착 | 120회 × 5초 = 10분, **로그 활동이 없을 때만** | 재시작 |
| 메모리 | 80% 경고 / 90% 이상 **+ 유휴일 때만** | 재시작 (쿨다운 15분) |
| 재시작 폭주 방지 | 5분 내 3회 | 자동 재시작 중단 |
| 기동 유예 | 재시작 후 120초 | 중복 기동 방지 |

**작업 도중에는 메모리가 아무리 높아도 재시작하지 않는다.** 진행 중인 배치를 죽이면
막으려던 손실을 그대로 일으키기 때문이다.

교차 확인 두 가지가 오탐을 막는다. `psutil` 이 부하 중에 프로세스를 놓칠 수 있으므로
API 응답으로 한 번 더 확인하고, `interrupted` 플래그는 Reload UI 나 수동 중단으로도
남기 때문에 Forge 로그가 최근에 쓰였는지로 진짜 고착과 가른다.

### 엔드포인트

| 메서드 | 경로 | 용도 |
|---|---|---|
| GET | `/health` | 살아있는지 |
| GET | `/status` | 배치·메모리·재시작 이력 전체 |
| POST | `/restart` | Forge 수동 재시작 |
| POST | `/upload` | 지정 범위를 zip 으로 묶어 드라이브 업로드 |

### `/status` 주요 필드

| 필드 | 의미 |
|---|---|
| `batch_job` | 진행 중인 작업명. 비어 있으면 유휴 |
| `batch_start_idx` | 대량배치가 시작된 이미지 인덱스 — **후처리의 기준점** |
| `batch_completed` | 작업이 비었는지 |
| `batch_aborted` | **재시작으로 끊겼는지.** true 면 미완성이므로 업로드 금지 |
| `mem_usage_gb` / `mem_pct` | 페이지 캐시를 뺀 실사용량 |
| `restart_count` / `last_restart_reason` | 재시작 이력 |

## 5. 배치 후처리

### 자동

```bash
python3 /workspace/scripts/auto_finish_watcher.py 프로젝트명_R_1 \
    --lora 캐릭터로라이름 \
    --spec 2026-09-16:437 --spec 2026-09-17:0
```

2분마다 `/status` 를 보다가 완료되면 zip → 업로드 → 검증 → **Forge 재시작**까지 한다.
`batch_aborted` 가 true 면 업로드하지 않고 경보만 남긴다.

### 수동

```bash
python3 /workspace/scripts/finish_multiday.py 프로젝트명_R_1 \
    --lora 캐릭터로라이름 --spec 날짜:시작인덱스 [--dry-run]
```

### 규약

- 명명: `{프로젝트명}_R_{숫자}`
- 업로드: `gdrive:{프로젝트명}/` + 미러 `gdrive:런포드 백업/압축파일/`
- 검증: 원격·로컬 바이트 수 일치
- 압축: `ZIP_STORED` 무압축, **PNG 만** (JPG 는 동일 해상도 압축 사본)
- **프로젝트 판별은 인덱스가 아니라 PNG 메타데이터의 `<lora:...>`**
- UTC 자정을 넘긴 배치는 `--spec` 을 날짜별로 여러 번 준다 (Forge 가 새 폴더를
  만들고 인덱스를 0부터 다시 시작한다)
- 프로젝트명이 애매하면 임의로 정하지 말고 사용자에게 확인

## 6. 메모리 관리

컨테이너 상한은 **62GB** 다. `free` 는 호스트 전체(251GB)를 보여주므로 믿으면 안 된다.

상한을 넘으면 커널이 가장 무거운 프로세스(= Forge)를 죽인다. **포드나 GPU 를 잃는 게
아니라 진행 중이던 배치의 대기열을 잃는다.** 컨테이너는 그대로 살아남는다.

배치가 돌면 메모리가 계속 오르고 끝나도 내려오지 않는다. 증가폭은 배치 종류에 따라
크게 다르다 — 같은 800장인데 48.8% 와 98.0% 로 갈렸다. **시간 기준 외삽은 신뢰할 수
없다.**

재시작으로 약 40GB 를 회수한다 (85% → 20%). 비용은 기동 15초 + 첫 모델 로드 11초로
2시간 배치의 0.3% 다. **긴 배치를 시작하기 직전, 또는 업로드 검증이 끝난 뒤**가 적기다.
낱장 작업마다 하는 것은 낭비다.

근본 대책은 **배치를 잘게 쪼개는 것**이다. 100배치를 25배치씩 4회로 나누면 손실
위험도 4분의 1이 된다.

## 7. crontab

```
*/5  * * * *  auto_clean_kernels.py      유휴 20분↑ Jupyter 커널 정리
*/30 * * * *  auto_backup_workspace.sh   workspace 스냅샷 → gdrive
@reboot       auto_restore_on_boot.sh    LoRA/체크포인트 복원 (idempotent)
@reboot       listener/start.sh          리스너 기동
```

`watchdog.sh` 와 `preventive_restart.py` 는 **의도적으로 등록하지 않는다.** 둘 다
독자적으로 `pkill` 후 Forge 를 직접 띄우는데 리스너도 같은 일을 하므로, 동시에 뜨면
포트 3001 점유에 실패한다. 게다가 `preventive_restart.py` 는 작업이 돌고 있으면
무기한 미루므로 정작 막아야 할 긴 배치 도중의 메모리 누적에 아무 효과가 없다.

## 8. 영구 볼륨 밖 — 컨테이너 재생성 시 소실

| 경로 | 내용 | 복구 |
|---|---|---|
| `/var/spool/cron/` | crontab | `bootstrap_pod.sh` |
| `/root/.config/rclone/` | rclone 인증 | `bootstrap_pod.sh` (+ `/workspace/rclone.conf` 사본) |
| `/etc/nginx/nginx.conf` | SSE 블록 포함 설정 | `bootstrap_pod.sh` |

**컨테이너가 새로 만들어지면 `bootstrap_pod.sh` 를 반드시 한 번 실행해야 한다.**

## 9. 절대 규칙

- **포드를 정지·터미네이트하지 말 것.** RTX 4080 SUPER 는 RunPod 에 매물이 없어 한 번
  내리면 같은 GPU 로 복구할 수 없다. 터미네이트는 `/workspace` 볼륨까지 삭제한다.
- `rclone.conf` 는 구글 드라이브 전체 접근 권한이다. 공개 저장소
  (`castle923/AutoRunpod`) 에 절대 커밋하지 않는다. 비공개 `Runpod-Backup` 의
  `secrets/` 에만 둔다.
- 포드를 조작하는 주체는 리스너 하나로 유지한다. 여러 세션·스크립트가 각자 Forge 를
  재시작하면 중복 기동과 프로젝트 혼입이 생긴다.
