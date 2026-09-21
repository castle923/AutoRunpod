# CLAUDE.md — Security & Operational Rules

## Critical Security Constraints

- **Pod Protection**: 포드(sydh2pm05u5rg2)를 절대 정지시키지 말 것. RTX 3090은 RunPod에 매물이 없어 한번 내리면 같은 GPU로 복구 불가.
- **Token Security**: GITHUB_TOKEN, rclone.conf의 refresh_token 등 민감 정보는 환경변수로만 전달. 절대 로그/커밋/공개 채널에 남기지 말 것.
- **rclone.conf**: `secrets/rclone.conf`는 **private** `castle923/Runpod-Backup`에만 존재. 절대 public `castle923/AutoRunpod`에 포함 금지.
- **TLS**: 절대 TLS 검증 비활성화 금지, HTTPS_PROXY 해제 금지.
- **RunPod**: Community Cloud만 사용, Secure Cloud 사용 금지.
- **Drive Contents**: 사용자 명시적 확인 없이 Google Drive 콘텐츠 삭제 금지.

## Google Drive — 4팀 공유 드라이브 (ABSOLUTE RULE)

**이 규칙은 모든 세션에 적용되며, 어떤 상황에서도 예외 없이 지켜야 한다.**

- 폴더명: `4팀 공유 드라이브`
- ID: `1rId_zhT9twxCTK8Y9QA2q94-mrMH5mm-`
- 소유자: kkangmyong438@gmail.com

### 금지 사항 (사용자 승인 없이 절대 불가)
- 파일 생성, 수정, 삭제, 업로드, 이동, 이름 변경 등 **어떠한 쓰기 작업도 금지**
- 로컬 파일을 해당 폴더 또는 하위 경로에 업로드하는 행위 금지
- 해당 폴더 내 기존 파일의 내용을 변경하는 행위 금지
- 읽기/조회만 허용

### 사용자가 업로드를 지시한 경우 필수 절차
1. 업로드 대상 파일 목록과 내용을 사용자에게 **명시적으로 제시**
2. 업로드 대상 경로(4팀 공유 드라이브 내 위치)를 사용자에게 **명시적으로 제시**
3. 사용자가 검토 후 **명시적으로 승인**한 경우에만 업로드 실행
4. 승인 없이 자동 업로드 절대 금지 — "업로드해줘"라는 지시만으로는 불충분하며, 반드시 내용 검토 후 최종 승인을 받아야 함
