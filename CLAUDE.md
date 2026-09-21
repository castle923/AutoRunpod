# CLAUDE.md — Security & Operational Rules

## Critical Security Constraints

- **Pod Protection**: 포드(sydh2pm05u5rg2)를 절대 정지시키지 말 것. RTX 3090은 RunPod에 매물이 없어 한번 내리면 같은 GPU로 복구 불가.
- **Token Security**: GITHUB_TOKEN, rclone.conf의 refresh_token 등 민감 정보는 환경변수로만 전달. 절대 로그/커밋/공개 채널에 남기지 말 것.
- **rclone.conf**: `secrets/rclone.conf`는 **private** `castle923/Runpod-Backup`에만 존재. 절대 public `castle923/AutoRunpod`에 포함 금지.
- **TLS**: 절대 TLS 검증 비활성화 금지, HTTPS_PROXY 해제 금지.
- **RunPod**: Community Cloud만 사용, Secure Cloud 사용 금지.
- **Drive Contents**: 사용자 명시적 확인 없이 Google Drive 콘텐츠 삭제 금지.

## Google Drive — 4팀 공유 드라이브 (ABSOLUTE RULE)

**절대로 사용자의 명시적 허락 없이 편집하지 말 것.**

- 폴더명: `4팀 공유 드라이브`
- ID: `1rId_zhT9twxCTK8Y9QA2q94-mrMH5mm-`
- 소유자: kkangmyong438@gmail.com
- 규칙: 파일 생성, 수정, 삭제, 업로드, 이동 등 **어떠한 편집 작업도 사용자의 명시적 허락 없이 절대 수행 금지**. 읽기/조회만 허용.
- 이 규칙은 어떤 상황에서도 예외 없이 적용됨.
