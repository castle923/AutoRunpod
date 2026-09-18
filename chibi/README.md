# Chibi / 아니마 세팅 재현

2026-09-18, 터널 `blackjack-arrangement-then-wear.trycloudflare.com/chibi/` 의
개발자도구 데이터로부터 역산한 환경. 관측값은 `OBSERVED.md` 참조.

## 재현 가능 범위

| 층위 | 상태 |
|---|---|
| 생성 파라미터 | 완전 재현 (`workflow_anima.json`) |
| ComfyUI 워크플로 그래프 | 완전 재현 |
| 터널 + nginx 서브패스 배포 | 완전 재현 (아래) |
| Chibi 프론트엔드 | **파일 복사만** 가능. minify 번들이라 재작성 불가 |
| 모델 가중치 2개 | **재현 불가.** 원본에서 반출 필요 |
| 특정 이미지 1:1 | 시드 필요. PNG 메타데이터에서 추출 |

## 원본 포드에서 반드시 가져와야 하는 것

```
models/checkpoints/animality_baseFlat_trubo.safetensors
models/loras/<달타셀일러_ANIM...>.safetensors     # 정확한 파일명은 probe 로 확인
/workspace/<chibi 배포 경로>/                      # index.html, assets/index.js, assets/index.css, manifest.json
```

LoRA 파일명이 UI 에서 잘려 있으므로 확정은 백엔드에 물어본다:

```bash
python3 comfy_client.py --host https://<tunnel> probe
```

## 새 환경 구성

1. ComfyUI 설치 (관측된 샘플러 목록에 `sa_solver` / `er_sde_cps` 가 있으므로
   구버전으로는 재현되지 않는다. 비교적 최신 리비전이 필요)
2. 위 가중치 2개를 `models/checkpoints`, `models/loras` 에 배치
3. Chibi 정적 파일을 `/chibi/` 서브패스로 서빙. 프론트엔드는
   `window.location.href.replace(/\/chibi\/[^\/]*$/, "")` 로 API base 를 잡으므로
   **UI 와 ComfyUI API 가 같은 오리진**이어야 한다
4. 터널 기동

nginx 예시:

```nginx
location /chibi/ { alias /workspace/chibi/; try_files $uri $uri/ /chibi/index.html; }
location /       { proxy_pass http://127.0.0.1:8188; proxy_http_version 1.1;
                   proxy_set_header Upgrade $http_upgrade;
                   proxy_set_header Connection "upgrade";
                   proxy_read_timeout 3600; }
```

## 주의

- 같은 오리진에 UI 와 ComfyUI API 가 함께 노출되므로, 터널 주소를 아는 누구나
  `/prompt` 로 작업을 주입하고 `/view` 로 생성물을 열람할 수 있다.
  외부 공개 시 Cloudflare Access 나 basic auth 를 반드시 앞에 둘 것.
- 히스토리는 `chibi.history(<url>)` 키로 저장된다. Quick Tunnel 은 재기동마다
  주소가 바뀌므로 새 주소에서는 히스토리가 빈 것처럼 보인다 (데이터는 남아 있음).
- 체크포인트 파일명의 `trubo` 는 `turbo` 오타지만 **바꾸지 말 것.**
  저장된 설정의 체크포인트 참조가 깨진다.

## 대조군 실험

Chibi 는 steps / CFG 를 UI 에서 잠가 두므로 값을 바꿔 검증하려면 API 직접 호출이
필요하다. `comfy_client.py` 가 그 용도다.

```bash
# 관측 세팅 그대로
python3 comfy_client.py --host https://<tunnel> run -n 20 \
    --prompt-file prompts.json --seed-base 1000 --out out_1536

# 해상도만 바꾼 대조군 (같은 시드)
python3 comfy_client.py --host https://<tunnel> run -n 20 \
    --prompt-file prompts.json --seed-base 1000 --size 1024x1024 --out out_1024

# CFG 를 올려 네거티브를 살린 대조군
python3 comfy_client.py --host https://<tunnel> run -n 20 \
    --prompt-file prompts.json --seed-base 1000 --cfg 2.0 --steps 24 --out out_cfg2
```

`prompts.json` 은 `{"positive": "...", "negative": "..."}` 형식.

## 포드 없이 LoRA 이름과 시드 복원하기

ComfyUI 는 출력 PNG 의 tEXt 청크(`prompt`)에 워크플로 JSON 을 통째로 넣는다.
따라서 그 사이트에서 뽑은 PNG 가 한 장이라도 있으면, 포드가 죽어 있어도
UI 에서 잘려 보이던 LoRA 전체 파일명과 실제 사용된 seed 를 복원할 수 있다.
`probe` 를 대신하는 경로다.

```bash
python3 read_png_workflow.py IMG.png              # 요약
python3 read_png_workflow.py IMG.png --raw        # 워크플로 JSON 전문
python3 read_png_workflow.py out/*.png --summary  # 여러 장 한 줄씩
```

A1111/Forge 출력(`parameters` 청크)도 함께 읽는다.

## 체크포인트 동일성 확인

보유 중인 아니마가 원본과 같은 배포본인지는 SHA256 으로 가른다.

```bash
sha256sum animality_baseFlat_trubo.safetensors
```

원본 해시를 구할 수 없다면 차선책은 고정 시드 대조다. PNG 에서 복원한 seed 와
파라미터를 그대로 넣어 재생성했을 때 원본과 같은 그림이 나오면 같은 가중치다.

```bash
python3 comfy_client.py --host http://127.0.0.1:8188 run -n 1 \
    --seed-base <복원한 seed> --prompt-file prompts.json
```

미세하게 다르면 버전 차이, 완전히 다르면 다른 모델이다.
