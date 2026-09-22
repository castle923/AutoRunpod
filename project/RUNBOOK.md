# 서버 운영 및 복구 매뉴얼

기존 docs/RUNBOOK.md 와 중복되는 내용은 참조만 한다. 이 문서는 Civitai 협업 프로젝트에 특화된 운영 절차.

## 1. 서비스 포트 맵

| 서비스 | 포트 | 프록시 URL 패턴 |
|---|---|---|
| Forge WebUI | 3000 (내부 7860) | `https://<POD_ID>-3000.proxy.runpod.net/` |
| ComfyUI | 8188 | `https://<POD_ID>-8188.proxy.runpod.net/` |
| Jupyter Lab | 8888 | `https://<POD_ID>-8888.proxy.runpod.net/` |
| code-server | 7777 | `https://<POD_ID>-7777.proxy.runpod.net/` |
| Listener | 5000 (Flask) | 내부 전용 |

## 2. ComfyUI 재시작

```bash
# 프로세스 확인
ps aux | grep "ComfyUI/main.py" | grep -v grep

# 중지
pkill -f "ComfyUI/main.py"

# 재시작 (LD_LIBRARY_PATH 설정 필수 — cuDNN 9)
/workspace/start_comfyui.sh
# 또는 수동:
export LD_LIBRARY_PATH=/usr/local/lib/python3.10/dist-packages/nvidia/cudnn/lib:/usr/local/lib/python3.10/dist-packages/nvidia/cublas/lib:$LD_LIBRARY_PATH
source /workspace/venvs/comfyui/bin/activate
cd /workspace/ComfyUI
nohup python3 main.py --listen 0.0.0.0 --port 8188 < /dev/null > /workspace/logs/comfyui.log 2>&1 &

# 헬스체크
sleep 5 && curl -s http://localhost:8188/system_stats | python3 -m json.tool
```

## 3. 업로드 중 장애 복구

rsync/rclone 이 중단된 경우:
```bash
# rsync 는 --checksum 으로 이미 전송된 파일을 건너뛴다
rsync -avz --checksum <source> <dest>
```

## 4. 무결성 검사 재실행

```bash
cd /workspace/Civitai
python3 /workspace/project/scripts/integrity_check.py
cat integrity_report.md
```

## 5. quarantine 처리

격리된 파일 확인:
```bash
ls -la /workspace/Civitai/quarantine/
```

재다운로드 후 원래 위치로 복원:
```bash
mv /workspace/Civitai/quarantine/<file> /workspace/Civitai/Lora/<collection>/
```

## 6. 디스크 사용량 모니터링

```bash
du -sh /workspace/Civitai/Lora/ /workspace/Civitai/Checkpoint/
df -h /workspace
```
