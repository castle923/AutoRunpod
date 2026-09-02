# AutoRunpod

RunPod GPU 포드 자동화 스크립트 모음입니다. RunPod GraphQL API를 통해 포드 생성/상태 조회 등을 관리합니다.

## 스크립트

- `scripts/runpod_pod_status.py` — 포드 상태 조회 (전체 목록 또는 특정 포드)
- `scripts/runpod_create_pod.py` — 새 온디맨드 포드 생성

## 사용법

```bash
export RUNPOD_API_KEY="rpa_xxx"

# 포드 상태 확인
python3 scripts/runpod_pod_status.py
python3 scripts/runpod_pod_status.py <pod_id>

# 포드 생성
python3 scripts/runpod_create_pod.py \
    --name my-pod \
    --gpu-type "NVIDIA GeForce RTX 4080 SUPER" \
    --image-name "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04" \
    --volume-gb 50
```

API 키는 항상 환경변수(`RUNPOD_API_KEY`)나 `--api-key` 플래그로 전달하며, 소스에 하드코딩하지 않습니다.

> 이 저장소는 원래 안드로이드 만화 번역 오버레이 앱 프로젝트였습니다. 해당 내용은 [castle923/Translator](https://github.com/castle923/Translator) 저장소로 이전되었습니다.
