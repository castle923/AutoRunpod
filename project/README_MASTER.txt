================================================================================
  프로젝트 마스터 번들 v1.5 (RunPod-Claude-Codex 협업)
  저장 위치: /workspace/project/  (Pod)  또는  autorunpod/project/  (저장소)
  목적: 에이전트별 구체적 실행 지침 및 연동 프로토콜 정의
================================================================================

[핵심 변경 사항 v1.5]
1. RunPod GPU 대여 조건 (VRAM, 모델명) 로컬/세션 검색 기능 구체화
2. Pod 생성 후 ID, IP, SSH 포트, Token 을 HANDOFF.md 에 기록하여 Codex 와 공유
3. hfdown (HuggingFace Downloader) Jupyter 실행 및 작동 검증 절차 명시
4. LoRA 와 Checkpoint 폴더 분리 저장 및 전수 무결성 검사 (SHA-256, 헤더, Pickle)
5. 병렬 작업 구조 (Claude 인프라 구축 중 Codex 로컬 다운로드) 확립

[현실 반영 사항 — 원본 계획서 대비]
- runpodctl CLI 미설치. scripts/runpod_create_pod.py (GraphQL API) 사용
- RUNPOD_API_KEY 는 사용자로부터 환경변수로 전달받아야 함
- civitai.com 은 이 세션(클라우드)에서 이그레스 정책으로 차단됨
  → Codex 로컬 다운로드 후 Pod 업로드 구조가 필수
- 리스너 서버(listener/server.py)와 hfdown.sh 는 기존 저장소에 이미 존재
- Community Cloud 고정 (Secure Cloud 사용 금지 — 예산 원칙)

[에이전트별 시작 가이드]
- Claude (Opus): AGENT_CLAUDE.md 부터 읽으십시오.
- Codex: AGENT_CODEX.md 부터 읽으십시오.
- 공통 준수 사항: SHARED_CONTRACT.md 를 반드시 숙지하십시오.
================================================================================
