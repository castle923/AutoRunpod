# AutoRunpod

RunPod GPU 포드 자동화 저장소입니다. 포드 생성/상태 조회 스크립트와, 포드 내부(Stable Diffusion
Forge) 설정/자동화 스크립트 백업을 함께 관리합니다.

이 저장소는 [castle923/Runpod-Backup](https://github.com/castle923/Runpod-Backup)와 내용을
동일하게 유지합니다 (양쪽에 동시 갱신).

## 구성

### 포드 관리 스크립트
- `scripts/runpod_pod_status.py` — 포드 상태 조회 (전체 목록 또는 특정 포드)
- `scripts/runpod_create_pod.py` — 새 온디맨드 포드 생성

### Forge 포드 설정/자동화 백업
- `config.json`, `ui-config.json` — Forge webui 설정 전체 (확장 활성화 여부 등 포함)
- `scripts/watchdog.sh` — Forge 다운 감지 시 자동 재시작 + rclone.conf 자동 복구
- `scripts/auto_clean_kernels.py` — Jupyter 고아 커널 정리 (5분마다 cron)
- `scripts/preventive_restart.py` — 5시간마다 예방적 Forge 재시작 (배치 idle일 때만, 10분마다 cron 체크)
- `scripts/submit_job.py` — 프롬프트 조합 후 Forge API로 배치 제출
- `scripts/finish_project.py` — 프로젝트 완료 표준 처리(zip → gdrive 업로드 → 백업 미러링 → 검증)
- `scripts/hfdown.sh` — 체크포인트/LoRA 원본을 Hugging Face(`Agnus6728/wai`)에서 받는 스크립트
  (토큰은 마스킹되어 있음, 실제 토큰은 gdrive `런포드 자동화/hfdown.sh` 비공개본 참고)
- `scripts/auto_restore_on_boot.sh` — 포드 부팅 시 자동 실행(crontab `@reboot`). LoRA/체크포인트/
  dynamic_prompts가 비어있거나 gdrive와 개수가 다르면 자동으로 복원하고 무결성 검증까지 수행함.
  이미 완전하면 즉시 종료(idempotent) — 매 부팅마다 실행해도 안전.
- `scripts/auto_backup_workspace.sh` — `/workspace`에 새로 생긴 잡다한 파일(느슨한 스크립트/노트북),
  scripts/config/dynamic_prompts 최신본, 최근 로그(24시간)를 30분마다 gdrive
  `런포드 백업/workspace_snapshot/`에 스냅샷 백업(crontab `*/30 * * * *`). 그래픽카드 셧다운 등으로
  포드가 갑자기 사라져도 GitHub/gdrive에 아직 반영 안 된 최신 작업 파일 손실을 최소화하기 위함.
- `dynamic_prompts/` — submit_job.py가 참조하는 프롬프트 조합 텍스트
- `SETUP_HISTORY.md` — 최초 구축(2026-08-27) 당시 작업 내역, 겪은 문제/해결, ComfyUI 설정 방법 등
- `MONITORING_ROUTINES.md` — 시간별 정밀검사/잔여시간 경고 Routine의 내용 정리 (참고용, 실행 코드 아님)

## 사용법 (포드 관리)

```bash
export RUNPOD_API_KEY="rpa_xxx"

# 포드 상태 확인
python3 scripts/runpod_pod_status.py
python3 scripts/runpod_pod_status.py <pod_id>

# 포드 생성
python3 scripts/runpod_create_pod.py \
    --name my-pod \
    --gpu-type "NVIDIA GeForce RTX 4080 SUPER" \
    --image-name "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04" \
    --volume-gb 50
```

API 키는 항상 환경변수(`RUNPOD_API_KEY`)나 `--api-key` 플래그로 전달하며, 소스에 하드코딩하지 않습니다.

## 새 포드 구축 시 복원 순서

1. RunPod 포드 생성 (이미지: `runpod/forge:3.3.0`, 볼륨 300GB 이상)
   - **반드시 `cloudType: COMMUNITY`(커뮤니티 클라우드)로 생성할 것.** `ALL`이나 기본값으로 생성하면
     Secure Cloud로 배정되어 시간당 요금이 2배 이상 비싸질 수 있음 (실제로 4090에서 겪은 실수:
     의도한 $0.34/hr 대신 Secure Cloud $0.74/hr로 배정됨). GraphQL로 생성 시
     `podFindAndDeployOnDemand(input: {cloudType: COMMUNITY, ...})`처럼 명시적으로 지정.
   - 또한 원하는 GPU 모델(RTX 4080 SUPER 등)의 재고 상태(`stockStatus`)가 낮으면 포드가 꺼졌다가
     재시작(resume)이 안 될 수 있음 — GPU 재고가 부족하면 재시작 대신 커뮤니티 클라우드에서
     새 포드를 생성하는 쪽이 더 빠를 수 있다는 점을 감안할 것.
2. 부팅 후 rclone 설정 (`gdrive` remote), 구글드라이브 `런포드 백업/Lora/`, `체크포인트/`를
   `models/Lora/`, `models/Stable-diffusion/`로 복원 (전수 무결성 검증 필수: `rclone check` + safetensors 헤더 검증)
3. **이 저장소의 파일들을 포드로 복사**:
   - `config.json`, `ui-config.json` → `/workspace/stable-diffusion-webui-forge/`
   - `scripts/watchdog.sh`, `auto_clean_kernels.py`, `preventive_restart.py`, `submit_job.py`,
     `finish_project.py`, `hfdown.sh` → `/workspace/scripts/` (submit_job.py의 포드 URL은 새 포드 주소로 수정 필요)
   - `dynamic_prompts/*` → `/workspace/dynamic_prompts/`
4. watchdog.sh 백그라운드 실행 + crontab 5종 등록:
   ```
   */5 * * * * /usr/bin/python3 /workspace/scripts/auto_clean_kernels.py >> /workspace/logs/auto_clean_kernels.log 2>&1
   */10 * * * * /usr/bin/python3 /workspace/scripts/preventive_restart.py >> /workspace/logs/preventive_restart_cron.log 2>&1
   @reboot /workspace/scripts/watchdog.sh >> /workspace/logs/watchdog_stdout.log 2>&1
   @reboot /workspace/scripts/auto_restore_on_boot.sh >> /workspace/logs/auto_restore.log 2>&1
   */30 * * * * /workspace/scripts/auto_backup_workspace.sh >> /workspace/logs/auto_backup.log 2>&1
   ```
   - `auto_restore_on_boot.sh`가 있으면 2번 단계(LoRA/체크포인트/dynamic_prompts 복원)를 사람이
     직접 하지 않아도 포드 재부팅 시 자동으로 진행되므로, 이 스크립트를 먼저 배포해두면 이후
     재구축 시간이 크게 단축됨.
   - `auto_backup_workspace.sh`는 워크스페이스에 새로 생긴(아직 백업 안 된) 파일들을 주기적으로
     gdrive `런포드 백업/workspace_snapshot/`에 저장해, 포드가 갑자기 사라져도 최신 작업 손실을
     최소화함.
5. Forge 재시작 후 `config.json`의 `disable_all_extensions` 값이 `"none"`인지 확인
   (이 값이 `"all"`이면 확장이 전혀 로드되지 않음 — 과거 실제로 발생했던 문제)

## 알려진 함정 (Known Pitfalls)

- **git이 GitHub 확장 설치를 실패시킴**: 오래된 git 버전(2.34.1)이 GitHub의 HTTP/2 응답 파싱에 실패해
  `git clone`이 "could not read Username" 오류로 실패할 수 있음.
  해결: `git config --global http.version HTTP/1.1`
- **config.json을 백업 위치에만 복사하고 실제 Forge 경로에 적용하지 않는 실수**:
  반드시 `/workspace/stable-diffusion-webui-forge/config.json`를 직접 덮어써야 함
  (임시 백업 폴더에만 복사하면 Forge는 도커 이미지 기본값을 계속 사용함).
- **Jupyter 커널 누적**: `jupyter_exec.py` 류의 도구로 반복 호출하면 커널이 계속 쌓여 결국 커널 고갈로
  Jupyter API가 마비될 수 있음 (과거 실제 크래시 원인). 주기적으로 `/api/kernels`를 DELETE 해서 정리 필요.

## ⚠️ 현재 이 백업에 없는 것 (알려진 공백)

- **ComfyUI 설정**: 최초 구축 때는 Forge와 ComfyUI를 함께 구성했었으나(`SETUP_HISTORY.md` 참고),
  현재 포드에는 ComfyUI가 복원되어 있지 않음. Forge만 쓰는 상황이면 문제 없지만,
  ComfyUI가 필요해지면 `SETUP_HISTORY.md`의 절차대로 새로 구성해야 함.
- **`런포드 자동화/` 폴더의 개별 zip/safetensors 파일들**: 2026-09-03 기준 전부 gdrive
  `런포드 백업/Lora/`의 668개 안에 이미 포함되어 있음을 확인함 (교차 검증 완료, 추가 조치 불필요).

## 저장소 히스토리

이 저장소는 원래 안드로이드 만화 번역 오버레이 앱 프로젝트였습니다. 해당 내용은
[castle923/Translator](https://github.com/castle923/Translator) 저장소로 이전되었고,
이후 이 저장소는 RunPod 자동화 전용으로 재구성되었습니다.
