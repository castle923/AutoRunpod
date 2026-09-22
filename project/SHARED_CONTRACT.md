# 공통 준수 사항 (Claude & Codex)

## 1. 통신 프로토콜
- **상태 공유**: 모든 진행 상황은 `project/STATUS.md`에 기록한다.
- **이벤트 로그**: 주요 변경은 `project/logs/events.jsonl`에 한 줄씩 기록한다.
- **채팅 최소화**: 긴 로그나 데이터는 채팅에 출력하지 말고 파일 경로를 링크한다.

## 2. 보안 규칙
- **비밀정보**: API 키, SSH 개인키, 토큰은 절대 채팅이나 로그에 평문으로 출력하지 않는다.
- **GITHUB_TOKEN 특별 주의**: 유출 시 castle923/Runpod-Backup을 통해 Google Drive refresh_token 접근 가능. 환경변수로만 전달, 로그/커밋/공개 채널에 절대 남기지 말 것.
- **rclone.conf**: castle923/Runpod-Backup(비공개)에만 존재. 공개 저장소에 절대 포함 금지.
- **접근 제어**: Codex는 Claude가 `INFRA_READY` 상태가 될 때까지 Pod에 접속하지 않는다.

## 3. 데이터 무결성
- **원본 보존**: 다운로드된 파일은 수정하지 않는다. 오류 시 원본 삭제 후 재다운로드한다.
- **격리 정책**: 검사 실패 파일은 삭제하지 않고 `quarantine/` 폴더로 이동한다.
- **해시 검증**: 모든 파일은 SHA-256 해시값을 계산하여 `manifest.jsonl`과 대조한다.

## 4. 오류 처리
- **재시도**: 네트워크 오류 발생 시 최대 3회 재시도한다.
- **차단**: 3회 실패 시 `BLOCKED` 상태로 전환하고 사용자 개입을 요청한다.
- **로그**: 모든 오류는 `project/logs/error.log`에 기록한다.

## 5. Git 규칙
- **브랜치**: `claude/backup-repo-review-setup-g9plm3`에서 작업
- **커밋**: 한국어 메시지, Co-Authored-By 라인 포함
- **금지**: main에 직접 push 금지, force push 금지
