# Claude 에이전트 실행 지침

## 1. 역할 정의
- RunPod Pod 생성 및 인프라 구축 (M1~M3)
- ComfyUI + Forge + 리스너 서버 구축
- hfdown 검증
- Codex에 Pod 접속 정보 공유 (HANDOFF.md)

## 2. 상세 작업 절차

### M1. Pod 생성

**전제: 사용자로부터 RUNPOD_API_KEY를 환경변수로 받아야 한다.**

기존 스크립트 사용:
```bash
export RUNPOD_API_KEY="rpa_xxx"  # 사용자가 제공
python3 scripts/runpod_create_pod.py \
    --name "HFdyd-v2" \
    --gpu-type "NVIDIA GeForce RTX 4090" \
    --image-name "runpod/forge:3.3.0" \
    --volume-gb 300 \
    --cloud-type COMMUNITY
```

생성 후 확인:
```bash
python3 scripts/runpod_pod_status.py --pod-id <새_POD_ID>
```

검증 항목:
- [ ] Pod 상태 RUNNING
- [ ] /workspace 네트워크 볼륨 마운트 확인
- [ ] 공인 IP 할당 확인 (과거 machineId 7g1rt1sudg62에서 미할당 문제 있었음)
- [ ] Jupyter (8888), Forge (3000) 포트 접근 가능

### M2. 서버 구축

#### A. Forge (기존 bootstrap_pod.sh 활용)
```bash
export GITHUB_TOKEN="ghp_xxx"  # 사용자가 제공
curl -sL https://raw.githubusercontent.com/castle923/AutoRunpod/main/scripts/bootstrap_pod.sh | bash
```

이 스크립트가 자동으로:
1. AutoRunpod 저장소 클론
2. Runpod-Backup에서 rclone.conf 가져오기
3. config.json, ui-config.json 배치
4. scripts, dynamic_prompts 배치
5. nginx 설정 + reload
6. crontab 등록
7. LoRA/체크포인트 gdrive 복원 시작

#### B. ComfyUI (신규 — SETUP_HISTORY.md 절차 기반)

bootstrap 완료 후 수동 또는 별도 스크립트:
```bash
cd /workspace
git clone https://github.com/comfyanonymous/ComfyUI.git
python3 -m venv /workspace/venvs/comfyui
source /workspace/venvs/comfyui/bin/activate

# torch 설치 (cu126 — SETUP_HISTORY.md의 교훈)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
pip install -r /workspace/ComfyUI/requirements.txt

# 모델 디렉토리 심볼릭 링크 (Forge와 공유)
FORGE_MODELS="/workspace/stable-diffusion-webui-forge/models"
ln -sfn "$FORGE_MODELS/Stable-diffusion" /workspace/ComfyUI/models/checkpoints
ln -sfn "$FORGE_MODELS/Lora" /workspace/ComfyUI/models/loras
ln -sfn "$FORGE_MODELS/ESRGAN" /workspace/ComfyUI/models/upscale_models

# Civitai 전용 경로도 연결
mkdir -p /workspace/Civitai/Lora /workspace/Civitai/Checkpoint
ln -sfn /workspace/Civitai/Lora /workspace/ComfyUI/models/loras_civitai
ln -sfn /workspace/Civitai/Checkpoint /workspace/ComfyUI/models/checkpoints_civitai

# 백그라운드 실행
cd /workspace/ComfyUI
nohup python3 main.py --listen 0.0.0.0 --port 8188 < /dev/null > /workspace/logs/comfyui.log 2>&1 &
```

검증:
```bash
curl -s http://localhost:8188/system_stats | python3 -m json.tool
curl -s http://localhost:8188/object_info | python3 -c "import sys,json; d=json.load(sys.stdin); print('nodes:', len(d))"
```

#### C. 리스너 서버 (기존 listener/server.py)
```bash
cd /workspace/listener
bash start.sh
```

### M2.5. hfdown 검증

```bash
# hfdown.sh 가 /workspace에 있는지 확인
ls -la /workspace/hfdown.sh || cp /workspace/_bootstrap_autorunpod/scripts/hfdown.sh /workspace/

# 도움말 확인
bash /workspace/hfdown.sh --help

# 테스트 다운로드 (작은 파일)
# 실제 hfdown.sh 는 Agnus6728/wai 에서 다운로드하도록 설계됨
```

검증 성공 시:
```bash
echo "hfdown: VERIFIED at $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> /workspace/project/reports/HFDOWN_CHECK.md
```

### M3. HANDOFF.md 작성

Pod 정보를 수집하여 기록:
```bash
POD_ID=$(cat /etc/hostname 2>/dev/null || echo "UNKNOWN")
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "UNKNOWN")
```

HANDOFF.md에 다음을 기록:
- Pod ID, Public IP, SSH Port
- Jupyter Port (8888) + Token
- ComfyUI URL (https://<POD_ID>-8188.proxy.runpod.net/)
- Forge URL (https://<POD_ID>-3000.proxy.runpod.net/)
- 리스너 상태

STATUS.md를 `INFRA_READY`로 변경.

## 3. 금지 사항
- Codex 작업 영역 (`/workspace/Civitai/`) 디렉토리 구조만 생성, 파일은 넣지 않음
- 비밀정보 채팅/로그 출력 금지
- hfdown 검증 없이 업로드 게이트 개방 금지
- **Secure Cloud로 Pod 생성 금지** (Community Cloud만)
- **기존 Pod 정지/삭제 금지** (GPU 재확보 불가 위험)

## 4. 현실적 제약 및 블로커

| 제약 | 영향 | 우회 |
|---|---|---|
| RUNPOD_API_KEY 미설정 | Pod 생성 불가 | 사용자에게 요청 |
| rclone 토큰 만료 (invalid_grant) | gdrive 백업/복원 불가 | 사용자 브라우저 OAuth 필요 |
| civitai.com 이그레스 차단 | Civitai 직접 다운로드 불가 | Codex 로컬 다운로드 위임 |
| 이 세션은 클라우드 컨테이너 | Pod에 직접 SSH 불가 | Jupyter API 또는 runpod API 경유 |
