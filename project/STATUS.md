# Project Status

| Component | Status | Last Updated | Actor | Note |
|---|---|---|---|---|
| Design | DESIGN_DONE | 2026-09-20T00:00Z | User | 계획서 v1.5 확정 |
| Claude Infra | SERVER_READY | 2026-09-20T17:40Z | Claude | ComfyUI 8188 가동 (torch 2.5.1+cu121, RTX 3090 24GB) |
| Codex Download | PLANNED | - | Codex | collections.yaml 확정 대기 |
| hfdown | HFDOWN_VERIFIED | 2026-09-21T00:40Z | Claude | HF 토큰 유효, Agnus6728/wai 접근 확인 (17파일, ~78GB) |
| Handoff | PENDING | - | - | - |
| Integrity | PENDING | - | - | - |

## Status Values
- `PLANNED` → `INFRA_BUILDING` → `SERVER_READY` → `HFDOWN_VERIFIED` → `INFRA_READY`
- `PLANNED` → `LOCAL_DOWNLOAD_DONE` → `UPLOADED` → `INTEGRITY_CHECKED`
- `COMPLETE` (최종)

## Recent Logs
- 2026-09-21T00:40Z: hfdown 검증 완료 — HF 토큰 유효, Agnus6728/wai private repo 접근 확인 (17파일 ~78GB)
- 2026-09-20T23:05Z: Bootstrap 완료 — Forge 가동 확인(port 3000), rclone.conf 배치, 스크립트 5종 crontab 등록, config.json/ui-config.json 배치
- 2026-09-20T18:10Z: Listener 서버 가동 완료 (port 5000, Flask + tmux auto-restart, 메모리 62GB 상한 감시)
- 2026-09-20T17:40Z: ComfyUI 서버 가동 완료 (port 8188, torch 2.5.1+cu121, RTX 3090 24GB VRAM)
- 2026-09-20T17:40Z: extra_model_paths.yaml 설정 — /workspace/Civitai/{Lora,Checkpoint} 경로 연결
- 2026-09-20T12:57Z: Pod sydh2pm05u5rg2 (RTX 3090, CC $0.22/hr) 생성. RTX 4090 재고 없어 3090으로 대체
- 2026-09-20: 프로젝트 번들 v1.5 생성 완료
