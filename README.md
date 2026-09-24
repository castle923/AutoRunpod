# AutoRunpod (유콘)

RunPod GPU 포드 자동화 저장소입니다. 포드 생성/상태 조회, Forge WebUI 크래시 자동 복구(리스너 서버),
배치 작업 모니터링, 백업/복원 자동화를 통합 관리합니다.

이 저장소는 [castle923/Runpod-Backup](https://github.com/castle923/Runpod-Backup)와 내용을
동일하게 유지합니다 (양쪽에 동시 갱신).

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────┐
│  RunPod Pod (RTX 4080 SUPER, 500GB)                 │
│                                                     │
│  ┌──────────────┐    ┌──────────────────────────┐   │
│  │ Listener     │    │ Forge WebUI              │   │
│  │ (Flask:5000) │───→│ (launch.py:3001)         │   │
│  │              │    │ nginx proxy → :3000      │   │
│  │ - 프로세스감시│    └──────────────────────────┘   │
│  │ - 자동재시작  │                                   │
│  │ - 배치추적   │    ┌──────────────────────────┐   │
│  │ - 업로드API  │───→│ rclone → Google Drive    │   │
│  └──────────────┘    └──────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │ Cron Jobs                                    │   │
│  │ - auto_clean_kernels.py (5분)                │   │
│  │ - preventive_restart.py (10분)               │   │
│  │ - auto_backup_workspace.sh (30분)            │   │
│  │ - auto_restore_on_boot.sh (@reboot)          │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 구성

### 리스너 서버 (Forge 감시 데몬)
- `listener/server.py` — **Flask 기반 상주 감시 서버 (포트 5000).** Forge 프로세스 생존을 2초 간격으로
  감시하고, 크래시 시 `restart_forge_clean.sh`로 자동 복구. 배치 진행률 추적, 업로드 트리거 제공.
  5분 내 3회 이상 재시작 시 재시작 폭풍 방지(storm detection) 동작.
- `listener/start.sh` — tmux 세션으로 리스너 백그라운드 실행
- `scripts/restart_forge_clean.sh` — **Forge 클린 재시작 스크립트.** `env -i`로 환경변수를 완전 격리하여
  MPLBACKEND 오염 등 Jupyter 환경변수 충돌을 원천 차단.

### 리스너 API 엔드포인트
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | `"ok"` 반환 (생존 확인) |
| GET | `/status` | Forge 상태, PID, 배치 진행률, 크래시 이력, 가동시간 JSON |
| POST | `/restart` | Forge 수동 재시작 트리거 |
| POST | `/upload` | 이미지 zip 압축 + gdrive 업로드 (project_name, date_folder, start_idx) |

### 포드 관리 스크립트
- `scripts/runpod_pod_status.py` — 포드 상태 조회 (전체 목록 또는 특정 포드)
- `scripts/runpod_create_pod.py` — 새 온디맨드 포드 생성

### Forge 설정/자동화 백업
- `config.json`, `ui-config.json` — Forge webui 설정 전체
- `scripts/watchdog.sh` — Forge 다운 감지 시 자동 재시작 + rclone.conf 자동 복구
- `scripts/auto_clean_kernels.py` — Jupyter 고아 커널 정리 (5분마다 cron)
- `scripts/preventive_restart.py` — 5시간마다 예방적 Forge 재시작 (배치 idle일 때만)
- `scripts/submit_job.py` — 프롬프트 조합 후 Forge API로 배치 제출
- `scripts/finish_project.py` — 프로젝트 완료 표준 처리(zip → gdrive 업로드 → 미러링 → 검증)
- `scripts/hfdown.sh` — Hugging Face에서 체크포인트/LoRA 다운로드
- `scripts/auto_restore_on_boot.sh` — 포드 부팅 시 LoRA/체크포인트/dynamic_prompts 자동 복원
- `scripts/auto_backup_workspace.sh` — 30분마다 워크스페이스 스냅샷을 gdrive에 백업
- `scripts/bootstrap_pod.sh` — 새 포드 통합 부트스트랩 (한 줄 실행으로 전체 재구축)
- `dynamic_prompts/` — submit_job.py가 참조하는 프롬프트 조합 텍스트

### 문서
- `BACKUP_AND_RESTORE.md` — rclone 작동 원리, 백업/복원 구조, 재설정 절차
- `MONITORING_ROUTINES.md` — 모니터링 체계 정리 (리스너 서버 + Claude Routine)
- `SETUP_HISTORY.md` — 최초 구축(2026-08-27) 당시 작업 내역
- `docs/H3_MOBILE_REQUIREMENTS.md` — MiniMax H3 모바일 킷 도입 요청 사항 정리 (결정·제공 항목, 킷 수정, 승인 게이트)
- `docs/QWEN_IMAGE_2_1_RESEARCH.md` — Qwen-Image-2.1(2026-09-20 공개) 조사 보고서
- `docs/LOCAL_AGENT_MODEL_FEASIBILITY.md` — RunPod에서 8GB 노트북용 AI 에이전트 모델 제작 현실성 조사

## 사용법

### 리스너 서버 실행

```bash
# 포드 내에서 실행 (Flask, psutil 필요)
pip3 install flask psutil
cd /workspace/listener
bash start.sh

# 상태 확인
curl localhost:5000/health    # → "ok"
curl localhost:5000/status    # → JSON 상태
```

### 포드 관리

```bash
export RUNPOD_API_KEY="rpa_xxx"

python3 scripts/runpod_pod_status.py
python3 scripts/runpod_pod_status.py <pod_id>

python3 scripts/runpod_create_pod.py \
    --name my-pod \
    --gpu-type "NVIDIA GeForce RTX 4080 SUPER" \
    --image-name "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04" \
    --volume-gb 50
```

## 새 포드 구축 시 복원 순서

### 빠른 방법: `bootstrap_pod.sh` 한 방에 실행

```bash
export GITHUB_TOKEN="ghp_xxx"
curl -sL https://raw.githubusercontent.com/castle923/AutoRunpod/main/scripts/bootstrap_pod.sh | bash
```

rclone gdrive 인증 정보는 **`castle923/Runpod-Backup`(비공개 저장소)의 `secrets/rclone.conf`**에만
저장. AutoRunpod는 공개 저장소이므로 실제 인증 정보를 절대 커밋하지 않음.

### 수동 단계별 순서

1. RunPod 포드 생성 (이미지: `runpod/forge:3.3.0`, 볼륨 300GB 이상)
   - **반드시 `cloudType: COMMUNITY`로 생성** — Secure Cloud는 시간당 요금 2배+
   - GPU 재고 상태(`stockStatus`)가 낮으면 resume 실패 가능 → 새 포드 생성이 더 빠를 수 있음
2. rclone 설정 후 gdrive에서 LoRA/체크포인트 복원 + 무결성 검증
3. 저장소 파일들을 포드에 배치 (config, scripts, dynamic_prompts)
4. crontab 등록 + watchdog 실행
5. **리스너 서버 배포**: `listener/` 디렉토리를 `/workspace/listener/`에 복사, `bash start.sh`
6. Forge 정상 동작 확인 (`curl localhost:5000/status`)

## 알려진 함정 (Known Pitfalls)

- **MPLBACKEND 환경변수 오염**: Jupyter의 `matplotlib_inline` 환경변수가 Forge 프로세스에 유입되면
  `ValueError: Key backend: 'module://matplotlib_inline.backend_inline'` 크래시 발생.
  `restart_forge_clean.sh`가 `env -i`로 환경을 완전 격리하여 해결.
- **Jupyter 커널 누적**: `jupyter_exec.py` 류의 도구로 반복 호출하면 커널이 100개 이상 쌓여
  새 커널 생성 자체가 500 에러로 실패. `auto_clean_kernels.py`가 주기적으로 정리하되,
  급할 때는 직접 `/api/kernels` DELETE로 일괄 정리 필요.
- **git HTTP/2 파싱 오류**: 오래된 git 버전(2.34.1)에서 `git clone` 실패 →
  `git config --global http.version HTTP/1.1`로 해결
- **config.json 배치 실수**: 반드시 `/workspace/stable-diffusion-webui-forge/config.json`에 직접
  덮어쓸 것 (임시 폴더에만 복사하면 Forge는 기본값 사용)

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-09-15 | 리스너 서버(listener/) 추가, restart_forge_clean.sh 추가, README 최신화 |
| 2026-09-03 | 초기 자동화 스크립트 일괄 정리, 부트스트랩/백업/모니터링 문서화 |
| 2026-08-27 | 최초 구축 (SETUP_HISTORY.md 참고) |
