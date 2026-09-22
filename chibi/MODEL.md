# animality_baseFlat_trubo.safetensors 조사 결과

## 계보

```
NVIDIA Cosmos-Predict2-2B-Text2Image
  └─ Anima  (CircleStone Labs + Comfy Org, 2B 파라미터)
       ├─ Anima-Base / Aesthetic / Turbo / preview·preview2·preview3
       └─ Animality  (커뮤니티 파생, Anima-preview-3 기반)
            └─ animality_baseFlat_trubo.safetensors   ← 관측된 파일
```

- Anima 는 **SDXL 이 아니다.** 텍스트 인코더는 Qwen3-0.6B, VAE 는 Qwen-Image VAE
- Animality 는 Civitai 모델 2532722. "Anima-preview-3 기반으로 생성을
  간결하게 하고 일관성을 해치지 않으면서 스타일 이탈을 줄인 것"
- 파일명 `baseFlat_trubo` 는 Civitai 의 `{모델명}_{버전명}` 규칙. 즉 버전 이름이
  "baseFlat trubo" 로 추정된다 (`trubo` 는 `turbo` 오타). base 계열 + flat 스타일에
  turbo 증류가 들어간 버전으로 읽힌다

## 입수 경로

### A. 원본 그대로 (권장)

Civitai 모델 2532722 의 해당 버전을 내려받는다.
**이 세션에서는 civitai.com / civarchive.com 이 이그레스 프록시 정책으로
차단돼 있어 내가 직접 확인하거나 받을 수 없다.** 사용자가 직접 받아야 한다.

### B. Hugging Face 분리 파일로 근사 재현

`circlestone-labs/Anima` 는 접근 가능하며 아래가 들어 있다.

| 파일 | 크기 | 배치 위치 |
|---|---|---|
| split_files/diffusion_models/anima-preview3-base.safetensors | 4.18 GB | models/diffusion_models |
| split_files/text_encoders/qwen_3_06b_base.safetensors | 1.19 GB | models/text_encoders |
| split_files/vae/qwen_image_vae.safetensors | 254 MB | models/vae |
| (별도 repo) Anima-Official-LoRAs/anima-turbo-lora-v0.2.safetensors | 149 MB | models/loras |

`anima-preview3-base` + `anima-turbo-lora-v0.2` 조합이 Animality baseFlat trubo 의
**출발점**에 해당한다. 다만 Animality 는 그 위에 별도 파인튜닝/머지가 들어간
파생본이므로 **같은 그림이 나오지는 않는다.** 스타일이 다르다.
`workflow_anima_split.json` 이 이 경로용이다.

```bash
huggingface-cli download circlestone-labs/Anima \
    split_files/diffusion_models/anima-preview3-base.safetensors \
    split_files/text_encoders/qwen_3_06b_base.safetensors \
    split_files/vae/qwen_image_vae.safetensors --local-dir .
huggingface-cli download circlestone-labs/Anima-Official-LoRAs \
    anima-turbo-lora-v0.2.safetensors --local-dir .
```

분리 파일 구성은 Chibi 의 "Checkpoint" 드롭다운(단일 파일 = CheckpointLoaderSimple)과
맞지 않는다. Chibi UI 로 쓰려면 머지해서 단일 체크포인트로 만들어야 하고,
API 직접 호출만 할 거라면 그대로 써도 된다.

## 라이선스 (확인 필요)

Anima 는 **CircleStone Labs Non-Commercial License** + NVIDIA Open Model License
(파생 모델 조항) 적용이다.

- **생성된 이미지(Outputs)의 상업적 이용은 허용된다.** 판매, 유료 커미션,
  유료 제품의 에셋으로 사용 모두 허용
- **모델 자체**를 API 뒤에 두고 접근료를 받거나, 유료 생성 플랫폼에 호스팅하거나,
  수익화된 제품에 가중치를 포함하는 것은 별도 라이선스 없이는 불가

현재 터널 구성은 개인 사용이라 문제되지 않지만, 외부에 유료로 열 계획이라면
걸린다. 파생본인 Animality 에도 같은 제약이 승계된다.

## 출처

- https://huggingface.co/circlestone-labs/Anima (README, 분리 파일, 공식 워크플로)
- https://civitai.com/models/2532722/animality (Animality, 접근 차단으로 검색 결과만 확인)
- https://civitai.com/models/2458426/anima (Anima 공식 배포)
