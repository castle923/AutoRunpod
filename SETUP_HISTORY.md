# 셋업 히스토리 (gdrive `런포드 자동화/HFdyd 런포드 셋업 요약.docx` 원문 정리)

원본 작성일: 2026-08-27 (KST). gdrive `런포드 자동화/` 폴더에서 발견되어 이 저장소로 옮겨 정리함.

## 포드 정보 (최초 구축 당시, 지금은 포드가 재생성되어 ID 등은 다름)

- 이름: HFdyd
- Pod ID: tetk9qntwfk3mv (현재는 재생성되어 다른 ID)
- GPU: NVIDIA GeForce RTX 4090
- **클라우드 타입: Community Cloud** ($0.34/hr)
- Volume: 50GB (region: any) — *현재는 300GB로 확장해서 사용 중*
- 템플릿: Stable Diffusion WebUI Forge (이미지: `runpod/forge:3.3.0`)

## 접속 URL 패턴 (포드 ID가 바뀌면 서브도메인도 바뀜)

- Forge WebUI: `https://<POD_ID>-3000.proxy.runpod.net/`
- **ComfyUI: `https://<POD_ID>-8188.proxy.runpod.net/`**
- Jupyter Lab: `https://<POD_ID>-8888.proxy.runpod.net/` (비밀번호 없음)
- code-server: `https://<POD_ID>-7777.proxy.runpod.net/`

## 원래 진행했던 작업

1. `hfdown.sh`(Hugging Face `Agnus6728/wai` 저장소에서 체크포인트/LoRA zip 다운로드)를 우선순위
   (체크포인트 > part3.zip > 로라 추정(styleil, lilpa) > 나머지)로 실행
   - 체크포인트(`waiNSFWIllustrious_v140.safetensors`) → `models/Stable-diffusion`
   - 압축 해제된 LoRA(.safetensors) → `models/Lora`
   - 업스케일러(.pth) → `models/ESRGAN`
2. **ComfyUI를 `/workspace/ComfyUI`에 git clone, 전용 venv(`/workspace/venvs/comfyui`) 구성**
3. ComfyUI의 `models/checkpoints`, `models/upscale_models`, `models/loras`를 Forge의
   `models/Stable-diffusion`, `ESRGAN`, `Lora`로 심볼릭 링크 연결 (모델 파일을 이중으로 안 두고 공유)
4. ComfyUI를 8188 포트로 백그라운드 실행, HTTP 200 확인

> **⚠️ 현재 포드에는 위 2~4번(ComfyUI)이 복원되어 있지 않음.** 지금까지는 Forge만 사용 중이라
> 미복원 상태이며, ComfyUI가 필요해지면 이 문서의 절차대로 새로 구성해야 함.

## 겪었던 문제와 해결 (참고용 — 같은 증상 재발 시 참조)

1. torch 최신 버전(cu13x)이 호스트 NVIDIA 드라이버(570.195.03, CUDA 12.8)와 호환되지 않아
   "driver too old" 오류 → torch를 cu124로 재설치했더니 이번엔 `comfy-kitchen`(0.2.31)이
   구버전 torch API와 호환 안 돼서 임포트 실패 → torch/torchvision/torchaudio + 전체
   `nvidia-*` 패키지 완전 삭제 후 **cu126** 인덱스로 재설치, comfy-kitchen 재설치로 해결
2. 백그라운드 실행 명령(`nohup ... &`)이 stdin 리다이렉트 누락으로 행업 → `< /dev/null` 추가로 해결
   (이 패턴은 현재 watchdog.sh/submit_job.py에도 이미 반영되어 있음)
3. RunPod 커뮤니티 클라우드 특정 호스트(machineId 7g1rt1sudg62)에서 공인 IP가 안 잡히는 문제
   → 다른 호스트로 포드를 재생성해서 해결

## LoRA/체크포인트/업스케일러 파일 판별 기준 (신규 파일 분류 시 적용)

- `.pth` / `.pt` → 업스케일러로 분류
- `.safetensors` → 헤더(JSON 메타데이터)의 텐서 키로 판별:
  - LoRA: `lora_unet_` / `lora_te_` / `alpha` 등의 키 포함
  - 체크포인트: `model.diffusion_model.` / `first_stage_model.` / `cond_stage_model.` 등의 키 포함
- 크기 보조 판단: 체크포인트 2GB 이상, LoRA 수십~수백MB, 업스케일러 수십MB 이내
- `.safetensors` + `.png` 미리보기 + `.txt` 캡션 세트 형식도 지원 대상

## 비용 관리 원칙 (사용자 명시 요청, 지금도 유효)

- **Community Cloud 고정, 시간당 요금 상한 의식할 것** (최초 기준 $0.34/hr)
- **Secure Cloud 사용 금지** (예산 초과 방지 — 실제로 2026-09-02 재구축 때 이 원칙을 어겨서
  Secure Cloud로 잘못 생성한 적 있음, `README.md`의 "새 포드 구축 시 복원 순서" 참고)

## 모니터링 (당시 방식 — 현재는 RunPod Routine으로 전환됨)

- 당시엔 5분 간격 자동 체크인을 세션 내 스케줄러로 운영
- 정상 시 조용히, 변화/오류 시에만 즉시 알림(KST 표기)
- **현재는 이 방식 대신 RunPod Routine(매시간 정밀검사 + 잔여시간 경고)으로 전환되어 있음.**
  자세한 내용은 `MONITORING_ROUTINES.md` 참고.
