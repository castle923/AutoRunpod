# 모델 복원 상태 (Google Drive → Pod)

> **최종 업데이트**: 2026-09-21T01:00Z
> **실행 주체**: Claude
> **스크립트**: `/workspace/scripts/auto_restore_on_boot.sh`

## 현재 상태: `RESTORING`

| 항목 | 소스 (gdrive) | 대상 (pod) | 상태 |
|---|---|---|---|
| LoRA | `gdrive:런포드 백업/Lora/` (680개) | `/workspace/stable-diffusion-webui-forge/models/Lora/` | 전송 중 |
| Checkpoint | `gdrive:런포드 백업/체크포인트/` | `/workspace/stable-diffusion-webui-forge/models/Stable-diffusion/` | 대기 (LoRA 완료 후) |
| dynamic_prompts | `gdrive:런포드 백업/extensions/sd-dynamic-prompts/` | `/workspace/stable-diffusion-webui-forge/extensions/sd-dynamic-prompts/` | 대기 |

## 복원 명령

```bash
# rclone 설정
rclone copy --transfers 6 --checkers 8

# LoRA 복원
rclone copy "gdrive:런포드 백업/Lora/" "/workspace/stable-diffusion-webui-forge/models/Lora/" --transfers 6 --checkers 8

# Checkpoint 복원 (키 파일)
waiNSFWIllustrious_v140.safetensors

# 무결성 검사 (복원 완료 후 자동 실행)
python3 /workspace/scripts/verify_lora_integrity.py
```

## 진행 모니터링 방법

Pod SSH 접속 후:
```bash
# 복원 프로세스 확인
ps aux | grep auto_restore_on_boot | grep -v grep

# 로그 실시간 확인
tail -f /workspace/logs/auto_restore.log

# LoRA 파일 수 확인
find /workspace/stable-diffusion-webui-forge/models/Lora/ -name "*.safetensors" | wc -l

# 디스크 사용량
du -sh /workspace/stable-diffusion-webui-forge/models/Lora/
du -sh /workspace/stable-diffusion-webui-forge/models/Stable-diffusion/
df -h /workspace
```

## 복원 완료 후 Codex 작업

1. **무결성 확인**: `verify_lora_integrity.py` 결과 확인 (`/workspace/logs/auto_restore.log` 끝부분)
2. **파일 수 대조**: gdrive 원본 680개 vs pod 복원 수량 일치 여부
3. **ComfyUI 연동 확인**: `extra_model_paths.yaml`이 Forge 경로도 인식하는지 확인
4. **M4-M7 진행**: Civitai 신규 모델 다운로드는 복원 완료 후 시작

## 주의사항

- 복원 중 Pod를 정지하지 말 것 (RTX 3090 재고 부족 — 복구 불가능)
- rclone shared client_id 경고는 무시 가능 (2026년 내 정상 동작)
- Google Drive 소스의 중복 파일(Duplicate object) 경고는 정상 — rclone이 자동으로 건너뜀
- 복원 대상은 Forge 경로(`/workspace/stable-diffusion-webui-forge/models/`)이며, `/workspace/Civitai/`가 아님
