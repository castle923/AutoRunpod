# 인증정보 및 GPU 조건 탐색 절차

## 1. 필요한 인증정보

| 키 | 용도 | 상태 |
|---|---|---|
| `RUNPOD_API_KEY` | Pod 생성/관리 (GraphQL API) | 사용자 제공 필요 |
| `GITHUB_TOKEN` | Runpod-Backup(비공개) 접근 → rclone.conf 획득 | 사용자 제공 필요 |
| rclone OAuth | Google Drive 백업/복원 | **만료됨** (invalid_grant) — 재인증 필요 |

## 2. GPU 대여 조건 (기본값)

- **GPU 모델**: NVIDIA GeForce RTX 4090 (우선) 또는 24GB VRAM 이상
- **클라우드 타입**: **Community Cloud 고정** (Secure Cloud 사용 금지 — 예산 원칙)
- **시간당 요금 상한**: $0.34/hr 이하 의식
- **볼륨**: 네트워크 볼륨 300GB (기존 사용량 기준)
- **템플릿**: `runpod/forge:3.3.0`
- **리전**: any (특정 리전 지정 안 함)

## 3. 탐색 명령어 (보안 주의)

```bash
# 환경변수 존재 여부만 확인 (값 출력 금지)
env | grep -Ei 'runpod|github_token' | sed 's/=.*/=<SET>/'

# 기존 Pod 상태 확인
python3 scripts/runpod_pod_status.py
```

## 4. 과거 문제 이력 (SETUP_HISTORY.md에서)

- machineId `7g1rt1sudg62`에서 공인 IP 미할당 → 다른 호스트로 재생성
- Secure Cloud로 잘못 생성한 전례 있음 → `--cloud-type COMMUNITY` 필수
- torch cu13x가 호스트 드라이버와 충돌 → cu126 사용

## 5. 기록 규칙
- 탐색 결과는 `project/reports/ENV_CHECK.md`에 `SET` 또는 `MISSING`으로만 기록
- 실제 키 값은 절대 기록하지 않는다
