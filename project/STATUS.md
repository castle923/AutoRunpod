# Project Status

| Component | Status | Last Updated | Actor | Note |
|---|---|---|---|---|
| Design | DESIGN_DONE | 2026-09-20T00:00Z | User | 계획서 v1.5 확정 |
| Claude Infra | INFRA_READY | 2026-09-21T00:45Z | Claude | Forge+ComfyUI+Listener 가동, bootstrap 완료, hfdown 검증 완료 |
| Codex Download | PLANNED | - | Codex | collections.yaml 확정 대기 |
| Handoff | HANDOFF_DONE | 2026-09-21T00:45Z | Claude | HANDOFF.md 완성, Codex 인수인계 준비 완료 |
| GDrive Restore | RESTORE_DONE | 2026-09-21T07:24Z | Claude | LoRA 681개 (149GB) + Checkpoint (6.9GB) 복원 완료, 무결성 검사 통과 |
| New Pod Script | DONE | 2026-09-21T06:00Z | Claude | new_pod_generate.sh 작성 완료 — GitHub + gdrive 업로드 |
| Integrity | PASSED | 2026-09-21T07:24Z | Claude | verify_lora_integrity.py 실행 — corrupted 0개 |

## Status Values
- `PLANNED` → `INFRA_BUILDING` → `SERVER_READY` → `HFDOWN_VERIFIED` → `INFRA_READY`
- `PLANNED` → `LOCAL_DOWNLOAD_DONE` → `UPLOADED` → `INTEGRITY_CHECKED`
- `COMPLETE` (최종)

## Recent Logs
- 2026-09-21T07:24Z: GDrive 복원 완료 — LoRA 681개 (149GB) + Checkpoint (6.9GB), 무결성 검사 통과 (corrupted 0)
- 2026-09-21T06:00Z: new_pod_generate.sh 작성 완료 — hfdown 우선 경량 포드 초기화 스크립트, GitHub 커밋 + gdrive 업로드
- 2026-09-21T01:00Z: GDrive 복원 시작 — LoRA 680개 + Checkpoint, auto_restore_on_boot.sh 실행 중
- 2026-09-21T00:45Z: M3 HANDOFF 완료 — HANDOFF.md 완성, Codex 인수인계 준비 완료
- 2026-09-21T00:40Z: hfdown 검증 완료 — HF 토큰 유효, Agnus6728/wai private repo 접근 확인 (17파일 ~78GB)
- 2026-09-20T23:05Z: Bootstrap 완료 — Forge 가동 확인(port 3000), rclone.conf 배치, 스크립트 5종 crontab 등록, config.json/ui-config.json 배치
- 2026-09-20T18:10Z: Listener 서버 가동 완료 (port 5000, Flask + tmux auto-restart, 메모리 62GB 상한 감시)
- 2026-09-20T17:40Z: ComfyUI 서버 가동 완료 (port 8188, torch 2.5.1+cu121, RTX 3090 24GB VRAM)
- 2026-09-20T17:40Z: extra_model_paths.yaml 설정 — /workspace/Civitai/{Lora,Checkpoint} 경로 연결
- 2026-09-20T12:57Z: Pod sydh2pm05u5rg2 (RTX 3090, CC $0.22/hr) 생성. RTX 4090 재고 없어 3090으로 대체
- 2026-09-20: 프로젝트 번들 v1.5 생성 완료
