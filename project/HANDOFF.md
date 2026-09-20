# Handoff Information (Confidential)

## Pod Connection
- **Pod ID**: `sydh2pm05u5rg2`
- **Pod Name**: `HFdyd`
- **GPU**: RTX 3090 (24GB VRAM)
- **Cloud Type**: Community Cloud ($0.22/hr)
- **Public IP**: `174.94.157.109`
- **SSH Port**: `48031`
- **SSH User**: `root`

## Services
- **Forge WebUI**: `https://sydh2pm05u5rg2-3000.proxy.runpod.net/`
- **ComfyUI**: `https://sydh2pm05u5rg2-8188.proxy.runpod.net/`
- **Jupyter Lab**: `https://sydh2pm05u5rg2-8888.proxy.runpod.net/`
- **code-server**: `https://sydh2pm05u5rg2-7777.proxy.runpod.net/`

## Environment
- **OS**: Ubuntu 22.04.4 LTS
- **Python**: 3.10.12
- **CUDA**: 12.1
- **Driver**: 580.65.06
- **torch**: 2.4.0+cu121
- **Volume**: 300GB (/workspace), 297GB free

## Verification Checklist
- [x] Pod RUNNING
- [x] /workspace 볼륨 마운트 (300GB)
- [x] GPU 확인 (RTX 3090 24GB)
- [ ] Forge 응답 (3000) — 미설치
- [x] ComfyUI 응답 (8188) — torch 2.5.1+cu121, 가동 중
- [x] 리스너 응답 (5000) — Flask listener 가동 중, 메모리 모니터링 활성
- [ ] hfdown 검증 완료

## Civitai 파일 업로드 경로
```
/workspace/Civitai/Lora/          ← LoRA 파일
/workspace/Civitai/Checkpoint/    ← Checkpoint 파일
/workspace/Civitai/png/           ← 대표 이미지
/workspace/Civitai/txt/           ← 트리거 단어
```

## 접속 방법 (Codex)
```bash
# SSH
ssh -p 48031 root@174.94.157.109

# rsync 업로드
rsync -avz --checksum -e "ssh -p 48031" ~/Desktop/Civitai/ root@174.94.157.109:/workspace/Civitai/
```
