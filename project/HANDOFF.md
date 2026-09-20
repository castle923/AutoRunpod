# Handoff Information (Confidential)

> **M3 HANDOFF 완료** — 2026-09-21T00:45Z
> 이 문서는 Claude가 구축한 인프라를 Codex에게 인수인계하기 위한 문서입니다.

## Pod Connection
- **Pod ID**: `sydh2pm05u5rg2`
- **Pod Name**: `HFdyd`
- **GPU**: RTX 3090 (24GB VRAM)
- **Cloud Type**: Community Cloud ($0.22/hr)
- **Public IP**: `174.94.157.109`
- **SSH Port**: `48031`
- **SSH User**: `root`

## Services
| 서비스 | 포트 | 상태 | URL |
|---|---|---|---|
| Forge WebUI | 3000 | 가동 중 | `https://sydh2pm05u5rg2-3000.proxy.runpod.net/` |
| ComfyUI | 8188 | 가동 중 | `https://sydh2pm05u5rg2-8188.proxy.runpod.net/` |
| Listener | 5000 | 가동 중 | 내부 전용 |
| Jupyter Lab | 8888 | 가동 중 | `https://sydh2pm05u5rg2-8888.proxy.runpod.net/` |
| code-server | 7777 | 가동 중 | `https://sydh2pm05u5rg2-7777.proxy.runpod.net/` |

## Environment
- **OS**: Ubuntu 22.04.4 LTS
- **Python**: 3.10.12
- **CUDA**: 12.1
- **Driver**: 580.65.06
- **torch (system)**: 2.4.0+cu121
- **torch (comfyui venv)**: 2.5.1+cu121
- **Volume**: 300GB (/workspace)
- **Container Memory Limit**: 62GB (cgroup)

## Verification Checklist
- [x] Pod RUNNING
- [x] /workspace 볼륨 마운트 (300GB)
- [x] GPU 확인 (RTX 3090 24GB)
- [x] Forge 응답 (3000) — Docker 이미지 내장, launch.py PID 473 가동 중
- [x] ComfyUI 응답 (8188) — torch 2.5.1+cu121, venv /workspace/venvs/comfyui
- [x] 리스너 응답 (5000) — Flask listener, tmux auto-restart, 메모리 감시 활성
- [x] hfdown 검증 완료 — HF 토큰 유효, Agnus6728/wai 접근 확인
- [x] rclone gdrive 인증 완료 — shared client 1.75.1
- [x] Bootstrap 완료 — config.json, ui-config.json, scripts 12종, crontab 5종

## Civitai 파일 업로드 경로
```
/workspace/Civitai/Lora/          ← LoRA 파일 (.safetensors)
/workspace/Civitai/Checkpoint/    ← Checkpoint 파일 (.safetensors)
/workspace/Civitai/png/           ← 대표 이미지
/workspace/Civitai/txt/           ← 트리거 단어
```

ComfyUI는 `extra_model_paths.yaml`로 위 경로를 자동 인식합니다.

## 설치된 스크립트 (/workspace/scripts/)
| 스크립트 | 용도 |
|---|---|
| `hfdown.sh` | HuggingFace에서 모델 다운로드 (HF 토큰 내장) |
| `auto_backup_workspace.sh` | 30분마다 gdrive 백업 (crontab) |
| `auto_clean_kernels.py` | 5분마다 좀비 Jupyter 커널 정리 (crontab) |
| `auto_restore_on_boot.sh` | 재부팅 시 gdrive에서 LoRA/Checkpoint 복원 (crontab) |
| `preventive_restart.py` | 10분마다 Forge 상태 점검 (crontab) |
| `watchdog.sh` | 재부팅 시 Forge 감시 (crontab) |
| `submit_job.py` | 배치 작업 제출 (pod URL 자동 치환 완료) |
| `finish_project.py` | 프로젝트 완료 처리 |
| `verify_lora_integrity.py` | LoRA 무결성 검사 |
| `bootstrap_pod.sh` | 초기 셋업 (이미 실행 완료) |

## 접속 방법 (Codex)
```bash
# SSH
ssh -p 48031 root@174.94.157.109

# rsync 업로드 (Civitai 파일)
rsync -avz --checksum -e "ssh -p 48031" ~/Desktop/Civitai/ root@174.94.157.109:/workspace/Civitai/

# Listener 상태 확인
curl http://localhost:5000/status

# ComfyUI 상태 확인
curl http://localhost:8188/system_stats
```

## Codex 다음 작업 (M4~M7)
1. **M4**: collections.yaml 기반 Civitai 모델 로컬 다운로드
2. **M5**: rsync/rclone으로 pod에 업로드
3. **M6**: integrity_check.py 실행 → 무결성 검사
4. **M7**: ComfyUI에서 모델 로드 테스트

## 보안 주의사항
- GITHUB_TOKEN, HF 토큰은 절대 로그/커밋/공개 채널에 남기지 말 것
- `secrets/rclone.conf`는 private repo `castle923/Runpod-Backup`에만 존재
- Pod 자체는 절대 정지시키지 말 것 — RTX 3090은 재고 부족으로 복구 불가능할 수 있음
- rclone.conf에 Google Drive refresh_token이 포함되어 있으므로 유출 시 드라이브 전체 접근 위험
