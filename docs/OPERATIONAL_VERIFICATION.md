# 운영 검증 결과 보고서
작성일: 2026-09-22
작성자: Claude (코드 검토 세션)
대상: 코덱스 검토자

## 목적
코드 리뷰(1~7차)에서 합의한 수정 사항이 실제 포드 환경에 반영되었는지, rclone 자동 동기화가 동작하는지 확인한다.
이 검증은 포드의 Jupyter API(읽기 전용)를 통해 수행했으며, 명령 실행이나 파일 수정은 하지 않았다.

## 포드 상태 요약

| 항목 | 상태 |
|---|---|
| 포드 ID | sydh2pm05u5rg2 |
| Forge WebUI (3000) | 응답 중 (HTTP 200) |
| Jupyter Lab (8888) | 응답 중 (HTTP 302) |
| 리스너 (5000) | 내부 동작 중 (state.json 갱신 확인), 외부 프록시 미노출 |
| 배치 작업 | **진행 중** — 100개 중 67번째, 67.4% (job timestamp: 20260921215342) |
| 메모리 | 73.5% (45.57GB / 62.0GB), 피크 95.6% |
| 마지막 재시작 사유 | memory 95.6% of container limit while idle |

**주의: 배치 작업이 진행 중이므로 포드에 대한 어떤 변경 작업도 배치 완료 후에 수행해야 한다.**

## 핵심 발견: rclone 자동 동기화 미작동

### 1. `sync_rclone_conf.sh`가 포드에 배포되지 않음

`/workspace/scripts/` 디렉터리 파일 목록:
```
auto_backup_workspace.sh
auto_clean_kernels.py
auto_restore_on_boot.sh
bootstrap_pod.sh
finish_project.py
hfdown.sh
preventive_restart.py
submit_job.py
verify_lora_integrity.py
watchdog.sh
runpod_create_pod.py
runpod_pod_status.py
new_pod_generate.sh
```

**`sync_rclone_conf.sh` 없음.** 이 스크립트는 브랜치(`claude/backup-repo-review-setup-g9plm3`)에만 존재하며, main에 merge되지 않았고 포드에 배포되지 않았다.

### 2. `/workspace/.env` 파일 없음

Jupyter API에서 HTTP 404 반환. GITHUB_TOKEN이 저장되지 않아 cron에서 `sync_rclone_conf.sh`가 실행되더라도 토큰 없이 실패할 것이다.

### 3. `sync_rclone.log` 없음

`/workspace/logs/` 디렉터리에 `sync_rclone.log`가 존재하지 않는다. 동기화 스크립트가 한 번도 실행된 적 없음을 확인한다.

### 4. `rclone.conf`는 존재함

- 경로: `/workspace/rclone.conf`
- 크기: 651 bytes
- 최종 수정: 2026-09-21T23:37:16Z
- 수동 또는 이전 bootstrap에서 배치된 것으로 추정

### 5. 자동 백업은 동작하지만 할당량 문제 있음

`auto_backup.log` 마지막 기록 (2026-09-21 20:30 UTC):
```
NOTICE: gdrive: This remote uses rclone's shared Google Drive client_id...
ERROR : irikanna_files.txt: Failed to set modification time: googleapi: Error 403: Quota exceeded...
```
rclone 공유 client_id의 API 할당량 초과로 일부 파일 메타데이터 갱신 실패.

## 포드에 배포된 스크립트 버전

현재 포드의 `/workspace/scripts/bootstrap_pod.sh`는 **코드 리뷰 이전 버전**이다. 브랜치의 7차에 걸친 수정 사항(safe_pull 강화, warn 집계, 원자적 교체, flock 구분, expiry 파싱 등)은 포드에 반영되지 않았다.

## rclone 자동 동기화가 작동하기 위한 전제 조건

| 전제 조건 | 현재 상태 | 필요 작업 |
|---|---|---|
| `sync_rclone_conf.sh`가 `/workspace/scripts/`에 존재 | 없음 | main merge 후 배포 또는 수동 복사 |
| `/workspace/.env`에 GITHUB_TOKEN 저장 | 없음 | bootstrap 재실행 또는 수동 생성 |
| crontab에 `sync_rclone_conf.sh` 등록 | 미확인 (등록했더라도 스크립트 없음) | bootstrap 재실행 또는 수동 등록 |
| `rclone.conf`의 토큰이 유효 | 존재함 (651B) — 유효성 미확인 | `rclone about gdrive:` 실행으로 확인 |
| Runpod-Backup 리포에 `secrets/rclone.conf` 존재 | 코드에서 확인 | 실제 리포 확인 필요 |

## 배포 경로

코드 리뷰 수정 사항을 포드에 적용하려면 다음 중 하나를 수행해야 한다:

### 방법 A: main merge 후 bootstrap 재실행
1. `claude/backup-repo-review-setup-g9plm3` → `main` PR 생성 및 merge (양쪽 저장소)
2. 포드에서 `bash /workspace/scripts/bootstrap_pod.sh` 재실행
3. bootstrap이 최신 main을 pull하여 모든 스크립트를 `/workspace/scripts/`에 배포

### 방법 B: 수동 배포 (배치 작업 완료 후)
1. 포드 Jupyter 터미널에서 `sync_rclone_conf.sh`를 수동 복사
2. `/workspace/.env`에 GITHUB_TOKEN 수동 저장
3. crontab에 `sync_rclone_conf.sh` 수동 등록

**어느 방법이든 현재 진행 중인 배치 작업(67/100)이 완료된 후에 수행해야 한다.**

## 코덱스 검토 요청 사항

1. **코드 리뷰는 완결됨** — 7차에 걸친 합의 범위의 코드 수정은 양쪽 저장소 브랜치에 push 완료.
2. **운영 배포는 미완료** — 포드에는 리뷰 이전 버전이 실행 중이며, rclone 자동 동기화 인프라가 갖춰지지 않음.
3. **다음 단계 결정 필요**:
   - main merge (PR 생성) 시점
   - 배치 완료 후 포드 배포 방법 선택
   - rclone 공유 client_id 할당량 문제 대응 (별도 OAuth 앱 등록 여부)
   - GITHUB_TOKEN 배포 방법 (bootstrap 재실행 vs 수동)

## 검증하지 않은 항목 (이번 범위 밖)

- rclone.conf 토큰의 실제 유효성 (`rclone about gdrive:` 미실행)
- OAuth refresh_token 자동 갱신 동작
- crontab 실제 등록 내용 (Jupyter API로는 확인 불가)
- Git 인증 헤더 방식의 실제 네트워크 동작
- 4팀 공유 드라이브 접근 (CLAUDE.md 규칙에 따라 승인 절차 없이 접근하지 않음)

## 보안 규칙 준수 확인

이 검증 과정에서:
- 포드를 정지하지 않음
- 명령을 실행하지 않음 (Jupyter API 읽기만 사용)
- 토큰/비밀값을 조회하거나 로깅하지 않음
- rclone.conf 내용을 읽지 않음 (메타데이터만 확인)
- 4팀 공유 드라이브에 접근하지 않음
- 배치 작업에 영향을 주지 않음
