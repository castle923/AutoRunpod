# Handoff Information (Confidential)

## Pod Connection
- **Pod ID**: `FILL_BY_CLAUDE`
- **Pod Name**: `FILL_BY_CLAUDE`
- **GPU**: `FILL_BY_CLAUDE`
- **Cloud Type**: Community Cloud (Secure Cloud 사용 금지)
- **Public IP**: `FILL_BY_CLAUDE`
- **SSH Port**: `FILL_BY_CLAUDE`
- **SSH User**: `root`

## Services
- **Forge WebUI**: `https://<POD_ID>-3000.proxy.runpod.net/`
- **ComfyUI**: `https://<POD_ID>-8188.proxy.runpod.net/`
- **Jupyter Lab**: `https://<POD_ID>-8888.proxy.runpod.net/`
- **Jupyter Token**: `FILL_BY_CLAUDE`
- **Listener**: `FILL_BY_CLAUDE`

## Verification Checklist
- [ ] Pod RUNNING
- [ ] /workspace 볼륨 마운트
- [ ] Forge 응답 (3000)
- [ ] ComfyUI 응답 (8188)
- [ ] Jupyter 응답 (8888)
- [ ] 리스너 응답
- [ ] hfdown 검증 완료

## Civitai 파일 업로드 경로
```
/workspace/Civitai/Lora/          ← LoRA 파일
/workspace/Civitai/Checkpoint/    ← Checkpoint 파일
/workspace/Civitai/png/           ← 대표 이미지
/workspace/Civitai/txt/           ← 트리거 단어
```
