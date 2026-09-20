# 프로젝트 계획서 v1.5

## 1. 아키텍처 개요

```
[Claude 진영]                      [Codex 진영]
1. RunPod Pod 생성 (GraphQL API)    1. 로컬 병렬 다운로드 (Lora/Checkpoint)
2. ComfyUI + 리스너 구축            2. 로컬 무결성 1차 검사
3. hfdown 업로드 및 Jupyter 검증    3. Claude 인프라 완료 대기 (STATUS 확인)
4. HANDOFF.md 작성 (Pod 정보 공유)  4. Pod 업로드 (SSH/rclone)
5. 상태 변경 (INFRA_READY)          5. 원격 무결성 전수 검사
                                    6. 최종 보고서 작성 (COMPLETE)
```

## 2. 디렉터리 구조 (Pod 내 표준)

```bash
/workspace/Civitai/
├── Lora/               # LoRA, LoCon, DoRA, LyCORIS 모델
│   ├── liked-models/
│   ├── bound/
│   └── ... (컬렉션별 slug)
├── Checkpoint/         # Checkpoint, CheckpointMerge 모델
│   ├── liked-models/
│   └── ... (컬렉션별 slug)
├── png/                # 대표 이미지 (모델명과 동일 파일명)
│   ├── Lora/
│   └── Checkpoint/
├── txt/                # 트리거 단어 및 프롬프트
│   ├── Lora/
│   └── Checkpoint/
├── quarantine/         # 무결성 검사 실패 파일 격리 폴더
├── manifest.jsonl      # 다운로드 목록 및 해시 정보
└── integrity_report.md # 최종 무결성 검사 보고서
```

## 3. 기존 인프라 자산 (castle923/AutoRunpod)

이미 존재하는 스크립트와 설정. 중복 작성하지 않고 재사용한다.

| 파일 | 역할 |
|---|---|
| `scripts/runpod_create_pod.py` | RunPod GraphQL API로 Pod 생성 |
| `scripts/runpod_pod_status.py` | Pod 상태 조회 |
| `scripts/bootstrap_pod.sh` | 새 Pod 통합 부트스트랩 (Forge 전용) |
| `scripts/hfdown.sh` | HuggingFace 모델 다운로더 |
| `listener/server.py` | Flask 기반 리스너 서버 (포트 5000) |
| `listener/start.sh` | 리스너 기동 스크립트 |
| `config/nginx.conf` | nginx 리버스 프록시 설정 |

## 4. 마일스톤 및 게이트

| 단계 | 이름 | 담당 | 완료 조건 (STATUS.md) | 비고 |
|---|---|---|---|---|
| M0 | 설계 | 사용자 | `DESIGN_DONE` | 이 계획서 확정 |
| M1 | Pod 생성 | Claude | `INFRA_BUILDING` | Pod 생성, 볼륨 마운트 |
| M2 | 서버 구축 | Claude | `SERVER_READY` | ComfyUI + Forge + 리스너 |
| M2.5 | hfdown 검증 | Claude | `HFDOWN_VERIFIED` | Jupyter 실행 테스트 통과 |
| M3 | 정보 공유 | Claude | `INFRA_READY` | HANDOFF.md 작성 완료 |
| M4 | 로컬 다운로드 | Codex | `LOCAL_DOWNLOAD_DONE` | Civitai → 로컬 저장 |
| M5 | Pod 업로드 | Codex | `UPLOADED` | rclone/rsync 완료 |
| M6 | 무결성 검사 | Codex | `INTEGRITY_CHECKED` | 검사 통과 및 보고서 |
| M7 | 최종 검토 | 사용자 | `COMPLETE` | 프로젝트 종료 |

## 5. 주요 게이트 조건

### Gate C (업로드 허용)
- **전제**: Claude의 STATUS가 `INFRA_READY`
- **공유 정보**: HANDOFF.md에 Pod IP, SSH Port, Jupyter Token
- **인증**: SSH 키 매칭 확인

### 보안 제약
- RUNPOD_API_KEY, GITHUB_TOKEN은 환경변수로만 전달
- rclone.conf는 castle923/Runpod-Backup(비공개)에만 존재
- **Community Cloud 고정** — Secure Cloud 사용 금지
- Pod 정지 금지 주의 (GPU 재확보 불가 위험)
