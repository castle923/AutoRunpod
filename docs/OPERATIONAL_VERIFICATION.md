# 운영 검증 결과 보고서
작성일: 2026-09-22
작성자: Claude (코드 검토 세션)
대상: 코덱스 검토자
개정: v2 — 코덱스 검토 보정 6건 반영 (2026-09-22)

## 목적
코드 리뷰(1~7차)에서 합의한 수정 사항이 실제 포드 환경에 반영되었는지, rclone 자동 동기화가 동작하는지 확인한다.
이 검증은 포드의 Jupyter API(읽기 전용)를 통해 수행했으며, 명령 실행이나 파일 수정은 하지 않았다.

## 관찰 시각 및 한계
아래 포드 수치와 상태는 **2026-09-22 약 01:40~02:00 UTC 관찰 당시의 스냅샷**이다. 이 문서를 읽는 시점의 현재 상태와 다를 수 있다. 포드 변경 직전에는 최신 상태를 다시 확인해야 한다.

## 포드 상태 요약 (관찰 시점 스냅샷)

| 항목 | 관찰값 | 비고 |
|---|---|---|
| 포드 ID | sydh2pm05u5rg2 | |
| Forge WebUI (3000) | HTTP 200 응답 | HTTP 경로 응답이며, 서비스 전체 정상과 동일하지 않음 |
| Jupyter Lab (8888) | HTTP 302 응답 | 동일 |
| 리스너 (5000) | state.json 갱신 확인 (간접 증거) | 외부 접근 실패 원인은 미노출/인증/네트워크 중 미확정 |
| 배치 작업 | 67/100, 67.4% (관찰 당시) | 현재 진행/완료 여부는 재확인 필요 |
| 메모리 | 73.5% (45.57GB / 62.0GB), 피크 95.6% | 관찰 시점 값 |
| 마지막 재시작 사유 | memory 95.6% of container limit while idle | |

**주의: 포드 변경 전에 배치 완료 여부와 대기열 상태를 최신으로 확인해야 한다.**

## 핵심 발견

### 1. `sync_rclone_conf.sh`가 `/workspace/scripts/`에 없음

Jupyter API로 조회한 `/workspace/scripts/` 디렉터리 목록에 `sync_rclone_conf.sh`가 포함되지 않았다. 해당 경로에 미배포된 근거로 직접적이다. 다른 위치에 동기화 스크립트가 존재할 가능성까지 배제한 것은 아니다.

배포된 파일 목록:
```
auto_backup_workspace.sh, auto_clean_kernels.py, auto_restore_on_boot.sh,
bootstrap_pod.sh, finish_project.py, hfdown.sh, preventive_restart.py,
submit_job.py, verify_lora_integrity.py, watchdog.sh, runpod_create_pod.py,
runpod_pod_status.py, new_pod_generate.sh
```

### 2. `/workspace/.env` — Jupyter API에서 조회 불가, 파일 존재 미확인

Jupyter API에서 HTTP 404 반환. **단, Jupyter는 기본적으로 숨김 파일(dotfile) 접근을 제한하며 404를 반환할 수 있다** (`ContentsManager.allow_hidden` 설정). 따라서 이 결과만으로 파일 부재를 확정할 수 없다. 다른 환경변수 주입 방식(런타임 환경변수, RunPod 설정 등)도 미확인이므로, .env 부재만으로 GITHUB_TOKEN 부재를 단정하지 않는다.

승인된 운영 확인에서 파일 존재 여부와 권한만 검사하면 된다 (값 자체를 열 필요 없음).

### 3. `sync_rclone.log` — 과거 실행 이력 확인 불가

`/workspace/logs/` 디렉터리 목록에 `sync_rclone.log`가 없었다. 과거 실행 이력을 확인할 수 없다는 의미이며, 삭제·로그 회전·다른 실행 경로의 가능성을 배제하지 못하므로 "한 번도 실행된 적 없다"고 확정하지 않는다. 항목 1에서 해당 경로의 스크립트 미배포가 더 직접적인 근거이다.

### 4. `rclone.conf`는 존재함

- 경로: `/workspace/rclone.conf`
- 크기: 651 bytes
- 최종 수정: 2026-09-21T23:37:16Z
- 내용은 읽지 않음 (메타데이터만 확인)
- 토큰 유효성은 미확인 (`rclone about gdrive:` 미실행)

### 5. 자동 백업 실행 흔적 있으나 할당량 오류 발생

`auto_backup.log` 마지막 기록 (2026-09-21 20:30 UTC):
```
NOTICE: gdrive: This remote uses rclone's shared Google Drive client_id...
ERROR : irikanna_files.txt: Failed to set modification time: googleapi: Error 403: Quota exceeded...
```

30분 간격 실행 흔적은 있으나 **crontab 원문은 미확인**이므로, 현재 cron 정상 등록 및 모든 파일 백업 완료를 보증하지 않는다. 할당량 오류의 세부 reason, quota metric/limit은 로그에서 생략되어 있어, 공유 client_id가 원인인지 프로젝트·사용자·저장공간 제한인지 구분하려면 전체 오류 사유(토큰을 가린 상태)를 확인해야 한다. client_id를 바꾸면 해결된다고 단정하거나 즉시 재인증할 단계는 아니다.

## 포드에 배포된 스크립트 버전

현재 포드의 `/workspace/scripts/bootstrap_pod.sh`는 **코드 리뷰 이전 버전**이다. 브랜치의 7차에 걸친 수정 사항(safe_pull 강화, warn 집계, 원자적 교체, flock 구분, expiry 파싱 등)은 포드에 반영되지 않았다.

## rclone 자동 동기화 전제 조건

| 전제 조건 | 관찰 결과 | 필요 작업 |
|---|---|---|
| `sync_rclone_conf.sh`가 `/workspace/scripts/`에 존재 | 해당 경로에 없음 | 배포 |
| GITHUB_TOKEN이 cron 실행 시 접근 가능 | .env 존재 미확인 (Jupyter dotfile 제한), 다른 주입 방식도 미확인 | 운영 확인에서 존재·권한 검사 |
| crontab에 `sync_rclone_conf.sh` 등록 | 미확인 | 운영 확인에서 등록 여부 검사 |
| `rclone.conf`의 토큰이 유효 | 파일 존재 (651B) — 유효성 미확인 | `rclone about gdrive:` 실행으로 확인 |
| Runpod-Backup 리포에 `secrets/rclone.conf` 존재 | 코드에서 확인 | 실제 리포 확인 필요 |

## 배포 경로

### 방법 A: main merge 후 bootstrap 재실행
1. `claude/backup-repo-review-setup-g9plm3` → `main` PR 생성 및 merge (양쪽 저장소)
2. 포드에서 최신 bootstrap 실행

**보정 (코덱스 지적):** 기존 `/workspace/scripts/bootstrap_pod.sh`를 그대로 재실행하면 구버전 코드가 실행된다. 기존 clone이 feature 브랜치라면 main merge만으로 해당 checkout이 main으로 전환되지 않는다. 배포 시에는:
- 대상 commit을 확정한 최신 bootstrap을 별도로 받아 확인한 뒤 실행하거나
- 필요한 변경만 검증된 파일로 배포하는 방식을 사용한다
- 기존 설정과 crontab을 먼저 보존하고, bootstrap이 수행하는 복원·nginx·listener 작업의 영향을 확인한다

### 방법 B: 수동 배포
1. 검증된 최신 파일을 직접 복사
2. GITHUB_TOKEN을 포드의 보호된 인증 전달 경로로 설정
3. crontab에 수동 등록
4. 적용 후 파일 readback, cron, 서비스, 동기화 결과 확인

**어느 방법이든 포드 변경 직전에 배치 완료·대기열 비어 있음을 최신 상태로 확인한다.**

## 코덱스 검토 반영 사항 (v2)

| # | 보정 내용 | 반영 |
|---|---|---|
| 1 | .env 404는 Jupyter 숨김 파일 제한일 수 있음 — "존재 미확인"으로 변경 | O |
| 2 | 로그 부재는 "과거 실행 이력 확인 불가"이며 "한 번도 실행 안 됨" 확정 아님 | O |
| 3 | 67/100은 관찰 당시 스냅샷 — 현재 상태와 다를 수 있음 | O |
| 4 | 백업 실행 흔적과 cron 등록/백업 성공은 구분 | O |
| 5 | 할당량 원인은 세부 reason 확인 필요 — client_id 변경으로 해결 단정 금지 | O |
| 6 | HTTP 응답과 내부 서비스 전체 정상은 다름 | O |
| 추가 | 배포 방법 A 보정 — 구버전 bootstrap 재실행의 한계 명시 | O |

## 권장 순서 (코덱스 합의)

1. PR 준비/검토는 포드와 독립적으로 진행 가능
2. 포드 변경 전 배치 완료·대기열 비어 있음을 최신 상태로 확인
3. 배포 대상 commit, 기존 파일/설정/cron 백업, 적용 범위 확정
4. 토큰은 포드의 보호된 인증 전달 경로로 설정 — 값이 아닌 존재·권한·Git 동작 결과로 검증
5. 검증된 최신 코드 적용 후 파일 readback, cron, 서비스, 실제 refresh와 동기화 결과 확인
6. quota 문제는 오류의 세부 reason 확인 후 별도 대응

## 검증하지 않은 항목 (이번 범위 밖)

- rclone.conf 토큰의 실제 유효성 (`rclone about gdrive:` 미실행)
- OAuth refresh_token 자동 갱신 동작
- crontab 실제 등록 내용
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
