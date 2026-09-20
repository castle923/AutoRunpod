# Codex 에이전트 실행 지침

## 1. 역할 정의
- Civitai 컬렉션 로컬 다운로드 (M4)
- Pod 업로드 (M5)
- 무결성 전수 검사 (M6)

## 2. 사전 조건
- `collections.yaml`에 대상 컬렉션 정의 완료
- 로컬에 충분한 디스크 공간 (수십~수백 GB)
- Claude의 STATUS가 `INFRA_READY`가 될 때까지 Pod 접속 금지

## 3. 상세 작업 절차

### M4. 로컬 병렬 다운로드

1. `collections.yaml` 기반 Civitai API 스캔
2. 모델 타입 분류:
   - `Lora`: `.safetensors` (Lora, LoCon, DoRA, LyCORIS)
   - `Checkpoint`: `.safetensors` (Checkpoint, Merge)
   - `Reject`: `.ckpt`, `.pt` (Pickle 위험 — 다운로드하지 않음)
3. 로컬 폴더 `~/Desktop/Civitai/{Lora,Checkpoint,png,txt}/`에 저장
4. `manifest.jsonl`에 SHA-256 해시 미리 계산하여 기록

manifest.jsonl 형식:
```json
{"filename": "example.safetensors", "type": "Lora", "collection": "liked-models", "sha256": "abc123...", "size_bytes": 12345678, "civitai_model_id": 123456, "civitai_version_id": 789012}
```

### M5. Pod 업로드 (Gate C 이후)

1. `STATUS.md`가 `INFRA_READY`인지 확인
2. `HANDOFF.md`에서 Pod IP 및 SSH 포트 읽기
3. SSH 접속 테스트
4. 파일 전송:
   ```bash
   rsync -avz --checksum ~/Desktop/Civitai/ root@<IP>:<Port>/workspace/Civitai/
   ```
   또는 RunPod proxy URL 경유:
   ```bash
   # HANDOFF.md에 기록된 Jupyter 터미널을 통한 업로드도 가능
   ```
5. 전송 완료 시 `STATUS.md`를 `UPLOADED`로 변경

### M6. 무결성 전수 검사

`scripts/integrity_check.py` 실행. 검사 항목:

| 검사 | 방법 | 실패 시 |
|---|---|---|
| 파일 존재 | manifest vs 실제 파일 수 비교 | 누락 목록 작성 |
| SHA-256 | 로컬 해시와 원격 해시 대조 | quarantine/ 이동 |
| safetensors 헤더 | JSON 메타데이터 파싱 | quarantine/ 이동 |
| HTML 오염 | 첫 20바이트에 `<html` 등 | quarantine/ 이동 |
| Pickle 스캔 | picklescan (checkpoint만) | quarantine/ 이동 |
| 짝 검증 | .safetensors당 .png, .txt 존재 | 경고만 (블로커 아님) |

결과물:
- `integrity_report.md` (통과율, 실패 사유 목록)
- `STATUS.md`를 `INTEGRITY_CHECKED`로 변경

## 4. 금지 사항
- Claude의 `INFRA_READY` 전에 Pod 접속 시도 금지
- 무결성 검사 실패 파일 자동 삭제 금지 (격리만)
- Pickle 파일 (.ckpt) 실행 로드 금지
- 비밀정보 (API 키, SSH 키) 채팅 출력 금지

## 5. Pod 디렉토리 구조 (업로드 목표)

```
/workspace/Civitai/
├── Lora/
│   ├── liked-models/
│   ├── bound/
│   └── ... (collections.yaml의 slug별)
├── Checkpoint/
│   ├── liked-models/
│   └── ...
├── png/
│   ├── Lora/
│   └── Checkpoint/
├── txt/
│   ├── Lora/
│   └── Checkpoint/
├── quarantine/
├── manifest.jsonl
└── integrity_report.md
```

## 6. safetensors 타입 판별 기준

SETUP_HISTORY.md에서 가져온 판별 로직:

- `.pth` / `.pt` → 업스케일러 (또는 reject)
- `.safetensors` 헤더의 텐서 키:
  - LoRA: `lora_unet_` / `lora_te_` / `alpha` 등
  - Checkpoint: `model.diffusion_model.` / `first_stage_model.` / `cond_stage_model.` 등
- 크기 보조 판단: Checkpoint 2GB+, LoRA 수십~수백MB, 업스케일러 수십MB 이내
