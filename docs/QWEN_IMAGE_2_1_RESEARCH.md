# Qwen2.1(추정: Qwen-Image-2.1) 조사 보고서

- 작성 기준일: 2026-09-23
- 근거:
  - Hugging Face를 직접 조회했다(API, config, 파일 목록, discussion; 2026-09-23 조회).
  - PyPI 메타데이터와 휠 내용을 확인했다.
  - 프록시가 차단한 사이트(qwen.ai, ModelScope, comfy.org 계열, comfyui-wiki, 다수 언론, x.com)는 검색 스니펫만 봤다.
  - GitHub는 조회하지 않았다.
- 표기:
  - **미검증**: 1차 출처로 확인하지 못함. 스니펫이나 커뮤니티 주장만 있는 경우.
  - **추론**: 계산이나 정황으로 판단한 것.
  - 시각은 별도 표기가 없으면 UTC.
- 모델 가중치는 받지 않았다. 메타데이터, config, 헤더만 조회했다.

---

## 0. 요약

- **정체**
  - "20일에 출시된 Qwen2.1"은 Alibaba Qwen 팀이 **2026-09-20**에 공개한 오픈 웨이트 이미지 모델 **Qwen-Image-2.1**(`Qwen/Qwen-Image-2.1`)로 판단한다. 신뢰도는 높다(약 95%).
  - 공식 "Qwen2.1" LLM은 존재하지 않는다(Qwen2에서 바로 Qwen2.5로 넘어갔다).
  - 커뮤니티 HF repo들이 "Qwen2.1"을 이 모델의 약칭으로 쓰고 있다.
- **기능과 규모**
  - 모델 하나로 T2I, 이미지 편집(참조 이미지 최대 10장), RGBA 투명 이미지 생성·편집·배경 제거를 한다.
  - 구성은 DiT 7,115,124,736 + Qwen3-VL-8B급 텍스트 인코더 8,767,123,696 + RGBA VAE 337,740,404로, 합계 약 16.2B 파라미터다.
- **라이선스**
  - 이전 Qwen-Image 계열의 Apache-2.0에서 **Qwen Research License(비상업, 연구·평가 전용)**로 바뀌었다.
  - 생성물의 상업 이용 가능 여부는 공식 X 게시물과 LICENSE 본문이 엇갈려 **미확정**이다.
- **3090 적합성**
  - **2026-09-24 HF 전수 점검(4.6) 결과 권장 세트를 바꿨다.** 권장: Comfy-Org **bf16 DiT**(14.23 GB) + Comfy-Org/Qwen3-VL **fp8_scaled TE**(10.59 GB) + VAE(0.68 GB) = 25.49 GB. 특수 커널(ConvRot) 없이 코어 로더만으로 동작하는 조합이다. 1024² 피크는 약 16–18 GB로 추정(미검증)해 24 GB에 들어간다.
  - 이전 권장이던 int8 세트(17.28 GB)는 comfy-kitchen ConvRot 커널이 필요한데, sm_86(3090)에서의 동작이 미검증이라 **2순위**로 내렸다. 3090 1차 실측은 아직 없다.
  - **텍스트 인코더는 사용자 결정으로 heretic 변형을 쓴다(4.7).** 선택 파일: `pottokao/Qwen-Image-2.1-Text-Encoder-Heretic`의 `qwen3vl_8b_bf16_heretic.safetensors`(17.53 GB). 적용 세트(안 H)는 bf16 DiT + heretic bf16 TE + VAE = 32.44 GB다.
  - 전제 조건은 ComfyUI ≥0.37.0, cu130 PyTorch(PyPI 기준 torch ≥2.11), 호스트 드라이버 r580+이다.
  - 드라이버(580.65.06, `project/HANDOFF.md`)는 충족하지만, 현재 ComfyUI venv의 torch 2.5.1+cu121은 **미달**한다.
- **다른 모델과의 관계**
  - MiniMax H3 텍스트 인코더(Qwen3-VL-32B, hidden 5120)와 호환되지 않는다.
  - Anima(Qwen3-0.6B TE, Qwen-Image VAE)와 공유하는 가중치가 없다.
  - Forge는 지원하지 않는 것으로 간주한다.
- **권고**
  - 3090 포드에 Qwen-Image-2.1 전용 ComfyUI(≥0.37.x)와 **새 venv**(cu130 torch)를 별도 경로에 만들고, 안 H(bf16 DiT + heretic bf16 TE + VAE, 32.44 GB)로 시험한다(4.6, 4.7, 5.2). 같은 시드로 공식 TE(안 S)와 비교해 품질 차이를 확인한다.
  - 기존 `/workspace/venvs/comfyui`는 롤백용으로 그대로 둔다.
  - H3 키트와 한 환경으로 합치는 것은 권하지 않는다. `docs/H3_MOBILE_REQUIREMENTS.md`는 H3를 새 32GB+ 포드에서 돌리고(D2) 킷이 검증한 ComfyUI 0.30.0으로 고정할 것(D16)을 권한다. 2.1은 ≥0.37.0이 필요하므로, 한 ComfyUI로 합치려면 H3를 0.37에서 따로 검증해야 한다.
  - 포드 정지·재시작은 필요 없다. ComfyUI 프로세스 재시작만 승인 후 진행한다. 비상업·연구 용도로만 쓴다.

---

## 1. 모델 식별

### 1.1 결론
- "Qwen2.1"은 **Qwen-Image-2.1**이다.
  - repo: `Qwen/Qwen-Image-2.1`
  - 한국 언론 표기: "큐원 이미지 2.1"
- README 원문: "We are excited to open-source **Qwen-Image-2.1**, a unified text-to-image generation and image editing model" ([HF README](https://huggingface.co/Qwen/Qwen-Image-2.1), 2026-09-23 조회).
- 블로그 제목(스니펫): "Qwen-Image-2.1: Compact, Efficient, and Unified ..." (https://qwen.ai/blog?id=qwen-image-2.1, 차단됨).

### 1.2 출시일 근거

| 근거 | 내용 | 출처(표기 날짜) |
|---|---|---|
| LICENSE | "Qwen RESEARCH LICENSE AGREEMENT Release Date: September 20, 2026". 파일 자체는 2026-09-18T10:28:46Z 커밋으로 추가됨 | https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE |
| 커밋 이력 | 09-14T03:47:26Z initial commit → 09-15T10:54:50Z 업로드 → 09-18 LICENSE → 09-19T00:40:14Z "Update to 0919 release checkpoint; fix vae scale_factor_spatial=16, remove transformer causal_block" → **09-20T09:41:05Z README 소개** → 09-21 README/WeChat 수정 | https://huggingface.co/api/models/Qwen/Qwen-Image-2.1/commits/main |
| 공개 시각 | QwenDevs 예고 "Qwen-Image-2.1 open source in 10hrs". 게시물 ID를 해석하면 2026-09-20T02:51:54Z이므로 공개는 **약 12:50–13:00Z**(한국 21:50–22:00, 모든 관련 시간대에서 9/20) | https://x.com/QwenDevs/status/2101504596623630787 (스니펫, ID 해석) |
| 첫 공개 활동 | HF discussion #1 12:59:24Z, @Alibaba_Qwen 게시물 13:06:43Z(ID 해석), 첫 커뮤니티 양자화(tsolful) 14:04:05Z | HF discussions API; https://x.com/Alibaba_Qwen/status/2101659321549660610 |
| 동반 공개물 | PE-T2I 2026-09-20T08:45:29Z, PE-I2I 08:46:47Z, Space `Qwen/Qwen-Image-2.1` 10:15:59Z, `Qwen-Image-2.1-workflow` 15:21:29Z 생성 | HF API |
| 언론 | Sina 2026-09-20, MarkTechPost 2026-09-21, TechNode 2026-09-21. AI타임스·AI매터스는 "현지 시각 9월 20일 … 허깅페이스와 모델스코프에 공개"(스니펫). **Tencent News 날짜는 미검증** | 9장 출처 |

- 09:41Z README 커밋은 공개 약 3시간 **전**, 비공개 상태에서 이뤄졌다. 이 커밋을 공개 시점으로 보면 안 된다.
- HF의 "Created: 14 Sep"는 비공개 스테이징 날짜로 본다(추론이지만 정황이 강함). HF API는 공개 전환 시각을 노출하지 않는다.

### 1.3 이름 근거
- **공식 "Qwen2.1"은 없다.**
  - HF API에서 `Qwen/Qwen2.1`, `Qwen/Qwen2.1-7B`는 공개 repo가 없다.
  - Qwen2-7B는 2024-06-04, Qwen2.5-7B는 2024-09-15에 생성됐다.
- 이름이 문자 그대로 "Qwen2.1"인 2024년 repo는 무관한 커뮤니티 LLM 2개다.
  - `cong-gu/qwen2.1` (2024-07-04)
  - `bunnycore/Qwen-2.1-7b-Persona-lora_model` (2024-11-12)
- 2026-09-20 이후의 "Qwen2.1" repo들은 모두 Qwen-Image-2.1 파생물이다.
  - `tsolful/Qwen2.1_INT4W4A8` (2026-09-20T14:04Z): `base_model: Qwen/Qwen-Image-2.1`을 명시한다. 파일은 `qwen_image_2.1W4A8.safetensors`.
  - `Felldude/QWEN_2.1_HDR_VAE` (2026-09-22T03:33Z): base_model을 명시한다.
  - `Winnougan/Qwen-2.1-ComfyUI-AIO` (2026-09-21T17:03Z): base_model은 없다. 파일명이 `Qwen2.1_AIO_*`이고, Qwen-Image-2.1 Comfy 파일과 같은 W4A8 TE를 쓴다.
  - `KoalaNation/Qwen2.1-prompt-rewrite-clip` (2026-09-23T03:57Z): base_model은 없다. license_link가 Qwen-Image-2.1-PE-T2I LICENSE를 가리킨다.
  - 즉 4개 중 2개만 base_model을 공식 선언했고, 나머지 2개는 내용과 라이선스 링크로 연결된다. 그래도 결론은 유지된다.
- **Qwen HF org 활동**
  - 2026-09-03부터 09-23까지 생성되거나 수정된 모델은 2.1 3종뿐이다. 그 밖에는 데이터셋 `Qwen/RecreationBench`(09-18)만 있다.
  - 직전 모델은 Qwen-Drive-1.0-4B(2026-08-27 생성)다.
- **다른 Alibaba org의 최신 생성일**
  - Wan-AI 2026-08-06
  - FunAudioLLM 08-29
  - Alibaba-NLP 08-31
  - Tongyi-MAI 2026-01-23
  - alibaba-pai `MiniMax-H3-Fun-Controlnet-Union-2.0` 09-22(Qwen 아님)
- HF 트렌딩(2026-09-23): `Qwen/Qwen-Image-2.1` 2위, `abenzerps/Qwen-Image-2.1-Uncensored-GGUF` 5위, `Comfy-Org/Qwen-Image-2.1` 7위.

### 1.4 검토 후 기각한 대안

| 후보 | 날짜(출처 표기) | 기각 이유 | 출처 |
|---|---|---|---|
| Qwen3.8-Omni-Flash | 2026-09-18 | 이름·날짜 불일치. 대부분 API 전용으로 보도됨(startupfortune만 오픈 웨이트라고 했으나 Qwen HF org에 repo 없음) | technode 09-18, marktechpost 09-18 |
| Qwen3.8-LiveTranslate | 2026-09-19 | API 전용(스니펫) | mindstudio, orcarouter |
| Qwen-Audio-3.1 계열 | 2026-09-22(Apsara 보도자료) | "3.1"·날짜 불일치. 오픈 웨이트 여부 미검증 | pandaily |
| Qwen 4 (Max/Flash/Plus/27B) | 2026-09-22 발표 | 아직 학습 중이며 가중치·가격·일정 없음 | manilatimes 09-22, technology.org 09-22, pandaily |
| Wan2.1 | 2025-02-25(HF createdAt 2025-02-25T07:26Z) | "2.1"은 맞지만 연도가 다름 | HF, comfyui-wiki 2025-02-25 |
| Wan3.0 | 공개 베타 2026-08-06, 정식 08-24 | API 전용, 날짜 불일치 | winbuzzer 08-25, dataconomy 08-24 |
| Qwen-Image-2.0 | 2026-02-10 | API 전용이며 HF repo 없음 | gigazine, qwenimages.com(비공식) |
| Qwen-Image-3.0 | 2026-07-21 | API 전용, 가중치·벤치마크 없음, HF repo 없음. 사실상 Alibaba의 플래그십 이미지 모델(스니펫, 미검증) | unite.ai |
| 문자 그대로 "Qwen2.1" LLM | 출시된 적 없음 | Qwen2에서 Qwen2.5로 넘어감 | HF API |

---

## 2. 개요와 사양

### 2.1 공개 구성

| 항목 | Qwen-Image-2.1 | Qwen-Image-2.1-PE-T2I | Qwen-Image-2.1-PE-I2I |
|---|---|---|---|
| 역할 | T2I, 편집, RGBA 통합 모델 | 선택 사항인 프롬프트 재작성기 | 선택 사항인 편집 지시 재작성기 |
| 파라미터 | DiT 7,115,124,736(HF의 "7115.1M"은 **DiT만** 센 값) + TE 8,767,123,696 + VAE 337,740,404 = 16,219,988,836 | 9,409,813,744 (`qwen3_5`, "Qwen3.5-VL 9B" 파인튠) | 동일 |
| bf16 용량 | DiT 14.23 GB + TE 17.53 GB + VAE 1.35 GB(fp32) = 33.1 GB | 18.82 GB | 약 18.8 GB |
| 입력 | 텍스트와 참조 이미지 0–10장. 원·페인트 주석·마스크로 편집 영역 지정 | 임의 언어로 된 짧은 요청 | 이미지와 편집 요청 |
| 출력 | RGB 또는 RGBA 이미지 1장 | `<think>` 후 JSON `{rewritten_prompt, wh_ratio}`(영어) | JSON(편집 지시, `wh_ratio`, `ratio_follow`) |
| 요구 라이브러리 | git diffusers, `transformers>=5.17`, `torch>=2.4.0` | `transformers>=5.4.0` | 동일 |
| 라이선스 | qwen-research(비상업) | 동일 | 동일 |
| 공개일·채널 | 2026-09-20. HF, ModelScope, qwen.ai 블로그, GitHub `QwenLM/Qwen-Image-2.1`, HF Space | HF 2026-09-20 | HF 2026-09-20 |
| HF 통계(2026-09-23) | text-to-image, 다운로드 28.4K, 좋아요 1,977, Spaces 88 | 수정일 2026-09-20 | 수정일 2026-09-20 |

- PE의 파라미터 수는 stock Qwen3.5-9B(9,653,104,368)보다 약 243M 적다. 이유는 미검증이다.
- PE의 max_new_tokens는 README 기준 T2I 16,256, I2I 24,000이다. 공식 workflow Space는 1024를 쓴다.
- 출처: [PE-T2I](https://huggingface.co/Qwen/Qwen-Image-2.1-PE-T2I), [PE-I2I](https://huggingface.co/Qwen/Qwen-Image-2.1-PE-I2I) (2026-09-20).

### 2.2 아키텍처
출처: HF config, sha 790c926, 2026-09-23 조회.

- **DiT `QwenImage21Transformer2DModel`**
  - 32개 single-stream 레이어, 32 heads × 128(폭 4096), mlp_ratio 3.
  - in/out channels 64, patch 1, RoPE axes [16,56,56], context_in_dim 4096, `causal_condition: true`.
  - README 표현: "7B parameters in its visual generation component (32 Single-Stream DiT layers)". mixed-granularity attention과 prefix KV cache 재사용을 쓴다.
  - 블로그 설명(스니펫): 텍스트·지시는 token 단위 causal mask, 이미지는 chunk 단위 mask를 쓴다. 입력 이미지와 지시는 첫 스텝에 한 번 계산해 캐시한다.
  - 일부 보도는 "optimized MMDiT"라고 쓰지만 공식 카드(single-stream)와 맞지 않는다.
- **TE `Qwen3VLForConditionalGeneration`**
  - 텍스트 부분: 36층, hidden 4096, 32 query / 8 KV heads, FFN 12288, vocab 151,936, max_pos 262,144.
  - 비전 부분: depth 27, patch 16, deepstack [8,16,24].
  - 파라미터 8,767,123,696은 stock `Qwen/Qwen3-VL-8B-Instruct`(2025-10-11 생성)와 **정확히 같다**.
  - 다만 shard 경계와 sha256이 달라 파일이 byte 단위로 같지는 않다.
  - 커뮤니티(Qwen discussion #5, 2026-09-21)는 tensor 단위로 비교해 SHA가 같다고 주장한다. 공식 확인은 없어 **미검증**이다.
- **VAE `AutoencoderKLQwenImage21`**
  - in/out 4채널(RGBA), z_dim 64, 공간 16배 압축.
  - base_dim 96 / decoder_base_dim 144(비대칭), dim_mult [1,2,4,8,8], `scale_factor_temporal` 8 필드가 있다.
  - fp32 헤더에서 직접 센 값은 337,740,404 파라미터다.
  - Qwen-Image-VAE-2.0(arXiv 2605.13565) 계열인지는 미검증이다.
- **스케줄러**: FlowMatchEulerDiscrete, dynamic shift(exponential). base_shift 0.5, max_shift 0.9, base/max seq len 256/8192, shift_terminal 0.02.
- **규모 비교**
  - 기존 오픈 모델 Qwen-Image, 2512, Edit-2511은 모두 20,430,401,088 파라미터다. 2.1은 생성부를 약 7B로 줄였다.
  - API 전용이었던 Qwen-Image-2.0도 7B였다는 보도가 있다(aibase 스니펫, 미검증). 그렇다면 2.1은 7B급 첫 오픈 웨이트다.

### 2.3 입출력과 한계
- **네이티브 해상도(약 4MP)**: 2048×2048, 2400×1792 / 1792×2400, 2528×1696 / 1696×2528, 2752×1536 / 1536×2752. README 예제는 bf16, 40 steps, 2048².
- **Comfy 템플릿 기본값**: 1024×1024. 노트: "Official default is 1024. The model supports up to 2048". 크기는 32의 배수로 한다.
- **이미지 토큰 수(추론)**: 1024²는 4,096, 2048²는 16,384. 참조 이미지를 넣으면 그만큼 더해진다.
- **RGBA 출력**: 고정 래퍼 문구가 필요하다("This is an RGBA image with transparency. … The image has alpha channel and the background is transparent."). PNG로 저장해야 한다.
- **문서화되지 않은 부분**
  - 최대 프롬프트 길이는 미문서화(미검증)다.
  - 영상 기능은 없다.
  - 학습 데이터, 연산량, 레시피는 비공개다.
  - 2.1 기술 보고서는 HF Papers에 없다(2026-09-23). "GitHub에 게시됐다"는 스니펫은 미검증이다.
- **데모 주의**
  - 공식 Space의 `app.py`는 오픈 웨이트가 아니라 DashScope POC 엔드포인트 `pre-qwen-image-2.1-pro-yunqi`를 호출한다. `prompt_extend`는 기본으로 켜져 있다.
  - 따라서 데모 결과가 배포된 가중치와 같다고 볼 근거는 없다(미검증).
  - `Qwen-Image-2.1-workflow` Space는 오픈 diffusers 가중치를 쓴다. 28 steps로 돌며, 96 GB ZeroGPU에서 "~15s"라는 주석이 있다.
  - 출처: https://huggingface.co/spaces/Qwen/Qwen-Image-2.1/blob/main/app.py

### 2.4 라이선스
LICENSE 전문을 직접 확인했다(2026-09-23).

- **라이선스와 라이선서**: Qwen Research License. 라이선서는 Hangzhou Tongyi Laboratory Technology Co., Ltd.
- **허용 범위**
  - 2.a "FOR NON-COMMERCIAL PURPOSES ONLY". 1.i에서 Non-Commercial은 "for research or evaluation purposes only"로 정의된다.
  - 2.b 상업 이용은 별도 라이선스가 필요하다(model-business@notice.qwencloud.com). discussion #7에 이 주소로 보낸 메일이 반송된다는 커뮤니티 주장이 있다(미검증).
- **배포와 표기 의무**
  - 3.c 재배포 시 NOTICE 파일과 수정 파일 표시가 필요하다.
  - 4.b Materials나 그 **출력**으로 AI 모델을 만들어 배포하면 "Built with Qwen" 또는 "Improved using Qwen"을 표기해야 한다.
  - 4.c "Qwen"을 파생물의 주 이름으로 쓸 수 없다. "fine-tuned from Qwen Image"는 허용된다.
- **종료와 관할**
  - 5.c 라이선서를 상대로 IP 소송을 내면 라이선스가 종료된다.
  - 7.b 위반 시 종료되며 Materials를 삭제해야 한다.
  - 8 중국법이 적용되고 항저우 법원이 관할한다.
  - 9.a 본 계약에 없는 약정은 별도 약정으로 취급한다.
- **생성물의 상업 이용: 모호, 미검증**
  - @QwenDevs 게시물(2026-09-21T06:12Z, ID 해석, 스니펫만 확인): "Outputs are not part of the licensed Materials. Users retain the rights to images and o…"
  - 그러나 LICENSE 본문은 개정되지 않았다(마지막 커밋 09-21T04:50Z, LICENSE 커밋은 09-18).
  - 모델 실행 자체를 상업 목적으로 하는 것은 여전히 금지이고, 9.a에 따라 계약 밖 발언은 별도로 취급된다.
  - HF discussion #40(2026-09-23)에는 공식 답변이 없다. 법률 자문이 아니다.
- **이전 Qwen-Image 계열은 모두 apache-2.0이었다.** 2.1이 첫 비상업 라이선스다.
  - Qwen-Image 2025-08-02
  - Qwen-Image-2512 2025-12-30
  - Qwen-Image-Edit-2511 2025-12-17
  - Qwen-Image-Layered 2025-12-17
- `Winnougan/Qwen-2.1-ComfyUI-AIO`처럼 apache-2.0으로 표기한 커뮤니티 repo는 상위 라이선스와 충돌한다.

---

## 3. 성능

### 3.1 제작사 발표
자체 벤치마크이며 측정도 제작사가 했다.

- **Qwen-Image-Bench 종합 점수**
  - 2.1: **60.28**. 비교 대상은 Nano Banana 2.0 59.82, GPT Image 1.5 59.65, FLUX 2 Max 55.33.
  - 출처는 datanorth, buildfastwithai, 36kr 스니펫과 Tom's Hardware 헤드라인이다. 세부 점수는 **미검증**이다.
- **벤치마크 구조** (arXiv 2605.28091, 2026-05-27, Alibaba 저자)
  - 이중언어 프롬프트 1,000개.
  - 5개 축, 23개 하위 능력, 56개 루브릭.
  - 채점은 Q-Judger가 한다. Qwen3.6-27B 기반이며 전문 주석자 80명의 라벨로 학습했다.
- **보도에서 빠진 기준선**
  - 논문 Table 2에서 **GPT Image 2가 64.69**로 최고점이고, 2.1보다 높다.
  - Table 2의 나머지: Nano Banana Pro 59.45, Qwen Image 2.0 Pro 57.84, Seedream 5.0 57.22, Qwen Image 2512 52.06, Qwen Image 49.23.
  - 2.1과 비교된 기준선 수치가 Table 2와 정확히 같다. 5월 측정값을 재사용했을 가능성이 있다(추론).
  - 블로그 비교표에 GPT Image 2가 들어 있는지는 미검증이다.
- **없는 지표**: GEdit, ImgEdit, GenEval, DPG 수치가 없고, 편집·RGBA 전용 지표도 없다.
- **정성적 주장**(README/블로그): 타이포그래피, 인물 조명, 세부 묘사가 개선됐고 인물·제품 정체성을 유지한다.

### 3.2 독립 평가와 커뮤니티 측정

**Arena 인간 선호 평가** (스니펫만 확인, 미검증; https://x.com/arena/status/2102416020678008986, orcarouter)
- Image Edit Arena: 1,367점. 오픈 모델 1위, 전체 16위. GPT-Image-1.5-high-fidelity보다 3점, 선두보다 159점 낮다("as of September 22, 2026").
- Text-to-Image Arena: 1,228점(2,843표). 오픈 모델 1위, 전체 17위. nano-banana-pro보다 4점 낮다.
- Artificial Analysis는 차단돼 수치를 확인하지 못했다.

**속도와 메모리.** 3090 1차 측정은 없다.

| 환경 | 설정 | 결과 | 출처(날짜) | 비고 |
|---|---|---|---|---|
| RTX 5090, ComfyUI 0.36.0, torch 2.14.0+cu130, comfy-kitchen 0.2.35 | 1024², 40 steps, TE 포함 전체 | BF16 15.629 s, 공식 INT8 7.553 s, NVFP4 6.746 s | BennyDaBall/Qwen-Image-2.1-NVFP4 README (2026-09-20) | 커널이 켜진 상태에서 INT8이 BF16보다 약 2배 빠름 |
| RTX 5090, diffusers 0.41.0.dev0, torch 2.11+cu128, transformers 5.17.0 | 40 steps | 8-bit(torchao FP8 가중치+활성): 피크 21.3 GB(1024²) / 22.6 GB(2048²), 19.3 s / 42.5 s(1920×1088) / 115.7 s(2048²). NF4: 15.2 / 15.4 GB, 속도는 비슷 | Qwen disc #32 (2026-09-22) | FP8 활성은 sm_86에서 불가. Ampere에 해당하는 수치는 NF4 15.2 GB. 참조 2장이면 8-bit 25.6 GB, 4-bit 19.1 GB |
| RTX 4060 Ti 16GB, ComfyUI | INT8 DiT + INT8 TE + BF16 VAE | 피크 약 15 GB(보통 13–14 GB), T2I 약 20 s, 편집 약 60 s. 해상도·스텝 미기재 | Qwen disc #35 (2026-09-22) | 17.28 GB가 동시에 상주할 수 없으므로 TE는 스왑된 것 |
| 2× T4, torch 2.10.0+cu130, driver 580 | INT8 ConvRot, 1024², 40 steps | 139–147 s(FP32 연산 + Comfy Kitchen INT8 attention). PyTorch FP32 attention으로는 248–272 s | Comfy disc #8 (2026-09-21) | 3090 속도 추정에는 쓸 수 없음 |
| RTX 3090(@superalesha / alesha-pro, 3090 4장 리그) | INT8 ConvRot, 2048×1152, euler/simple, CFG 1, 50 steps | 작업당 82–96 s, 재실행 83.527 s / 85.271 s | GitHub alesha-pro/tools 스니펫 | **미검증** |
| RTX 3090(@superalesha) | CPU 오프로드 | 512²: VRAM 3.05 GiB, RAM 약 15.2 GiB. 1024²: VRAM 6.14 GiB(TE는 CPU) | https://x.com/superalesha/status/2101940249735634998 스니펫 | 미검증. 출처로 알려졌던 @Oluwaphilemon1 게시물은 인용으로 보임 |
| RTX 4090 | — | 1024² 약 7.5 s, 2048² 약 30 s | mindstudio 스니펫 | 미검증 |
| RTX 4090 **48GB**, Nunchaku W4A4 | 1024², 40 steps | 11.576 s, 상주 21.35 GB(bf16 TE 약 16.3 GB 포함) | ModelsLab README (2026-09-21) | 24 GB에는 빠듯함 |
| ComfyUI 0.37.0 (#16470) | 같은 템플릿 | INT8 ConvRot 308 s, Q8 GGUF 158 s | GitHub 이슈 스니펫 | GPU와 torch 불명, 미검증 |
| I2I | — | TE 약 30 s, DiT 약 10 s | Qwen disc #31 | GPU 미기재 |

### 3.3 알려진 품질 이슈 (2026-09-20~09-23)

| 이슈 | 대응 | 출처 |
|---|---|---|
| 템플릿 기본값(25 steps, 1024²)에서 옅은 타일링·밴딩. int8과 bf16 모두 발생 | 35–40 steps로 올림. "disappeared completely at 40" | Comfy-Org disc #11 (2026-09-22) |
| 황색 톤 | ComfyUI-Bleachery 노드, 또는 CFG를 올리고 네거티브 프롬프트 추가 | Comfy-Org disc #10 (~09-22) |
| 이미지 내 글자가 깨지는 경우 | PE가 도움이 되지만 해결되지 않음 | Comfy-Org disc #6 (~09-21) |
| 밝은 피부에서 VAE 다이아몬드 격자 무늬 | 커뮤니티 우회책뿐, 공식 수정 없음 | Qwen disc #12 (~09-20) |
| 손가락·발가락 | CFG를 올리고 네거티브 프롬프트 추가 | Qwen disc #29 (~09-21) |
| NSFW를 직접 출력함 | — | Comfy-Org disc #9 |

- **생성과 편집의 CFG 설정이 다르다.** 공식 템플릿은 CFG 1이다. 커뮤니티 조언은 "생성은 CFG를 올리고 네거티브 프롬프트를 써도 되지만, 편집은 올리지 말라"다(Qwen disc #14, 2026-09-22).
- **ComfyUI 버그**(GitHub 스니펫만 확인, 미검증)
  - #16447: 해상도와 무관하게 mu가 0.69로 고정된다. 공식 dynamic shift로는 2048²에서 약 1.31이므로 2K 결과가 흐려질 수 있다.
  - #16470: int8_convrot가 Q8 GGUF보다 훨씬 느리고 신체 왜곡이 잦다.
  - #16496: 편집 시 이미지가 왼쪽으로 밀린다.
  - #16443: Windows 멀티 GPU 문제로, 이 환경과 무관하다.
- **애니 스타일**: 일본어 테스트에서 "anime 스타일이 약할 수 있음", 3면도 캐릭터 일관성이 어렵다는 평가가 나왔다(https://note.com/sepiablue/n/n02026f718c3f, ~2026-09-22, 스니펫, 미검증).
- **라이선스 반발이 커뮤니티의 주된 화제다.** Qwen discussion #6 "License renders this model useless"에 댓글 19개가 달렸고, #9, #23, #39(Apache로 되돌려 달라), #40(상업 이용 문의)도 같은 주제다.

---

## 4. 배포 요구사항

### 4.1 공식 가중치
`Qwen/Qwen-Image-2.1`, sha 790c926, 수정일 2026-09-21.

| 구성 | 바이트 |
|---|---|
| DiT bf16 (shard 2개: 9,968,332,504 + 4,261,951,904) | 14,230,284,408 |
| TE bf16 (shard 4개) | 17,534,339,488 |
| VAE fp32 | 1,350,989,512 |
| 합계 | 33,115,613,408 (약 33.1 GB) |
| PE-T2I bf16 (shard 4개) | 18,819,721,168 |

### 4.2 Comfy-Org 리팩
[Comfy-Org/Qwen-Image-2.1](https://huggingface.co/Comfy-Org/Qwen-Image-2.1): 생성 2026-09-15, 수정 2026-09-23, qwen-research, 다운로드 2.22M.

| 파일 | 바이트 |
|---|---|
| diffusion_models/qwen_image_2.1_int8_convrot.safetensors | 7,256,783,064 |
| diffusion_models/qwen_image_2.1_bf16.safetensors | 14,230,280,616 |
| text_encoders/qwen3vl_8b_int8_convrot.safetensors | 9,350,798,360 |
| text_encoders/qwen3vl_8b_w4a8.safetensors | 6,312,105,364 |
| text_encoders/qwen3vl_8b_bf16.safetensors | 17,534,334,616 |
| text_encoders/qwen3.5_9b_qwen_image_2.1_pe_t2i.int8_convrot / pe_i2i | 각 9,471,072,252 (`TextGenerate` 노드용) |
| vae/qwen_image_2.1_vae_bf16.safetensors | 675,509,688 |

- **묶음 합계**(VAE 포함)

| 묶음 | 바이트 |
|---|---|
| int8 세트 | **17,283,091,112** |
| int8 DiT + w4a8 TE | 14,244,398,116 |
| bf16 DiT + int8 TE | 24,256,588,664 |
| bf16 세트 | 32,440,124,920 |
| repo 전체 | 74,301,956,212 |

  - VAE를 빼면 두 번째 묶음은 13,568,888,428, 세 번째 묶음은 23,581,078,976이다.
- **업로드 이력**
  - DiT 파일은 2026-09-19T10:03Z에 다시 올라왔고, 구버전은 같은 날 23:50Z에 삭제됐다. **이 시각 이전에 받은 파일은 구버전이다.**
  - VAE는 09-18T14:26Z에 다시 올라왔다.
  - TE int8·bf16 파일은 09-15 이후 바뀌지 않았다.
  - w4a8 TE는 09-20T07:54Z, PE int8 파일은 09-20T16:09–16:14Z에 올라왔다.
- **템플릿 3종**: `image_qwen_image_2_1_t2i`, `image_qwen_image_2_1_image_edit`, `image_qwen_image_2_1_background_removal`.
- 같은 `qwen3vl_8b` int8·w4a8 파일이 `Comfy-Org/Qwen3-VL`(apache-2.0, 수정 2026-09-20)에도 있다.

### 4.3 커뮤니티 양자화
HF에서 2026-09-23에 조회했다.

| repo (생성일) | 형식 | 크기 | 3090 관련 비고 |
|---|---|---|---|
| unsloth/Qwen-Image-2.1-GGUF (09-21T13:04Z) | GGUF, DiT만 | Q2_K 2.47 / Q3_K_M 3.17 / Q4_K_M 4.20 / Q5_K_M 5.39 / Q6_K 6.27 / Q8_0 7.64 / F16 14.23 GB | GGUF 메타데이터(architecture)가 없어 stock city96 ComfyUI-GGUF에서 "Unknown model architecture!" 발생. stable-diffusion.cpp와 Unsloth Desktop용. 권장 TE는 unsloth/Qwen3-VL-8B-Instruct-GGUF UD-Q4_K_XL(5.15 GB). 예제의 cfg 6.0 / 20 steps는 공식 권장이 아님 |
| leejet/Qwen-Image-2.1-GGUF (09-20T13:16Z) | GGUF | Q4_0/Q4_K 4.20 / Q5_0 5.07 / Q6_K 6.00 / Q8_0 7.69 GB | 메타데이터 없음. leejet ComfyUI-GGUF fork 권장. 라이선스 미기재 |
| Abiray/Qwen-Image-2.1-GGUF (09-20T13:08Z) | GGUF | Q3_K_M 3.19 … Q8_0 7.59 GB | `architecture=qwen_image`가 들어 있어 **stock city96 ComfyUI-GGUF로 로드 가능**. T2I/Edit 워크플로 포함 |
| realrebelai/Qwen-Image-2.1_GGUFs (09-20T15:36Z) | GGUF | Q4 5.96 / Q8 7.69 GB | architecture 메타데이터 포함 |
| unsloth/Qwen-Image-2.1-FP8 (09-21T11:28Z) | FP8·INT8 (diffusers) | FP8 7.12 / INT8 7.26 / TE FP8 9.39 / VAE 0.68 GB | bf16 대비 LPIPS: INT8 0.064, FP8 0.112. diffusers main 필요. sm_86에서는 FP8 연산 이득 없음 |
| toxicdog/Qwen-Image-2.1-INT4ConvRot-ComfyUI (09-20T14:43Z) | ConvRot W4A4 | DiT int4 3.67 / TE int4 6.88 GB (int8·w4a8·bf16 사본 포함) | macOS(Radiant Canvas) 테스트용. sm_86 동작 미검증 |
| NidAll/Qwen-Image-2.1-Mixed-Balanced (09-20T21:39Z) | W4A8/INT8 혼합 ConvRot | 4.20 GB | 실험적. w4a8 TE와 함께 쓰라고 권장 |
| ModelsLab/Qwen-Image-2.1-W4A4-int4 (09-21T06:45Z) | Nunchaku SVDQuant | 4.66 GB | sm_75–sm_120 지원 주장. torch==2.12.1, nunchaku cu13.0 고정. w4a4_build.json에는 "scheme": "nvfp4"로 적혀 라벨과 불일치 |
| SamuelTallet SDNQ-4bit (09-20T15:13Z) | SDNQ (diffusers) | DiT 4.10 / TE 6.74 / VAE 0.68 GB | — |
| Rin247/Qwen-Image-2.1-INT8 (09-22T19:32Z) | weight-only INT8 (diffusers) | DiT 8.83 / TE 8.77 GB | — |
| BennyDaBall/Qwen-Image-2.1-NVFP4 (09-20T18:39Z) | NVFP4 | DiT 4.20 / TE 7.55 / VAE 0.68 GB | NVFP4 텐서코어는 SM ≥10.0이 필요해 3090에서는 가속되지 않음. eager dequant로 느리게 돌 수는 있으나 미검증. **쓸 이유가 없음** |
| Viggle/Qwen-Image-2.1-viggle-turbo (09-22T04:14Z) | 4-step DMD 증류 | LoRA r64 0.34 GB, 전체 transformer 14.23 GB | v0.1 preview. CFG 1, 참조 1–3장, 복잡한 편집은 "clearly worse". diffusers 키 형식이라 ComfyUI 로드는 미검증 |
| Winnougan/Qwen-2.1-ComfyUI-AIO (09-21T17:03Z) | 단일 파일 | INT8+W4A8 14.24 / BF16 32.44 GB | apache-2.0 표기가 상위 라이선스와 충돌 |
| pottokao/Qwen-Image-2.1-Text-Encoder-Heretic-GGUF (09-20T17:08Z) | 검열 해제 TE | Q4_K_M 5.03 + mmproj 1.16 / fp8 9.34 GB | apache-2.0 표기. 변형 가중치 |
| abenzerps/Qwen-Image-2.1-Uncensored-GGUF (09-20T15:51Z) | 검열 해제 DiT·TE | Q4_0–Q8_0 4.15–7.59 GB 등 | 다운로드 351k. 출처 불명 수정 가중치 |

- 그 밖의 PE 관련 파생물
  - prithivMLmods PE-T2I/PE-I2I GGUF: 세부 미검증.
  - 증류 PE ML-Intern-lab Pocket-0.8B / Pocket-2B (2026-09-22): Pocket-2B README는 평가 300행에서 JSON 100% 유효, 평균 482.8 토큰, 3.22 s를 보고한다(하드웨어 미기재).

### 4.4 소프트웨어 요구

| 경로 | 요구 사항 | 검증 상태와 출처 |
|---|---|---|
| **ComfyUI** | **≥0.37.0** | 확인됨. 공식 템플릿 인덱스 `comfyui-workflow-templates-json` 0.1.88 (2026-09-20T05:12Z)과 0.1.95 (2026-09-23T17:08Z)에 세 템플릿 모두 `"minComfyUIVersion": "0.37.0"`, `"date": "2026-09-20"`. 0.36.0에서 동작했다는 보고(BennyDaBall, pottokao)는 0.36.0으로 표시되던 출시 전 master 빌드였을 것(추론). v0.37.0 출시일은 09-20과 09-21로 출처가 엇갈림. v0.37.1은 2026-09-22(스니펫) |
| comfyui-workflow-templates | **≥0.11.66** | 0.11.64 (09-20T01:11Z)에는 없음. 0.11.65 (09-20T05:13Z)에서 T2I·Edit 추가. 0.11.66 (09-20T12:59Z)에서 background_removal 추가, CLIPLoader를 `qwen3vl_8b_int8_convrot`로 변경. 최신 0.11.69 (09-23T17:08Z). PR #1277은 확인하지 않음 |
| 템플릿 기본값 | UNETLoader int8_convrot, CLIPLoader `[qwen3vl_8b_int8_convrot, qwen_image]`, KSampler 25 steps / cfg 1 / euler / simple / denoise 1, 1024×1024 | 템플릿 JSON |
| 코어 노드 | `TextEncodeQwenImage21`, `QwenImage21Cache`(캐시 장치 auto/gpu/cpu/off, dtype default/int8/int4), PE용 `TextGenerate` | 노드 이름은 템플릿 JSON에서 확인. 노드 설명은 comfyui-wiki 스니펫. PR #16400은 미검증 |
| **PyTorch(ConvRot 고속 경로)** | **cu130 빌드**: PyPI torch ≥2.11(Linux는 cuda-toolkit 13.0.x 의존, 2.14.0 설치 시 CUDA 13.0.3) 또는 PyTorch 인덱스의 +cu130 | PyPI 메타데이터 기준 2.7.0은 cu12.6.77, 2.8–2.10은 cu12.8.90이라 부족함. 2.11.0 (2026-03-23)부터 cu13. 최신 2.14.0 (2026-09-02). docs.comfy.org의 "2.7 and above"(스니펫)는 하한일 뿐 |
| cu130 요구 근거 | Comfy-Org/MiniMax-H3 README: "prefer `int8_convrot` if you are able to use pytorch with cu130". obsxrver README: "If you are using an older version, you will encounter memory and performance issues". docs.comfy.org 스니펫: cu130 이상 필요 | quant_ops.py가 CUDA 13 미만에서 comfy-kitchen CUDA 백엔드를 끈다는 내용은 disc #8의 로그 인용("You need pytorch with cu130 or higher...")뿐이고 코드는 보지 못함 |
| comfy-kitchen 0.2.35 (2026-09-17) | README 기준 PyTorch ≥2.7.0. CUDA 휠은 런타임 ≥13.0, **드라이버 r580+** 필요. 빌드 arch는 sm_75/80/89/90a/100f/120f. FP8은 SM ≥8.9, NVFP4는 SM ≥10.0 | 휠을 확인함. **sm_86 전용 코드는 없고**, 3090은 sm_80 바이너리 호환으로 동작할 것(추론, 미시험). 메타데이터에 torch 고정 없음 |
| diffusers 경로 | git main(0.40.0 릴리스에는 QwenImage21 없음), `transformers>=5.17`, `torch>=2.4.0` | diffusers 0.40.0 (2026-08-20) 휠 확인. Viggle은 커밋 80c7ed262a 고정. transformers 5.17.0 (2026-09-09). torch 2.5.1에서 막힌다는 근거는 메타데이터에 없으나 시험하지 않음. 쓰려면 별도 venv 필요 |
| PE (transformers) | `transformers>=5.4.0` | PE README |
| vLLM-Omni / SGLang | 릴리스 휠에 2.1 없음 | vllm-omni 0.30.0rc1 (2026-09-23)은 diffusers==0.40.0, transformers<5.15로 고정. sglang 0.5.20 (2026-09-18)도 없음. PR 상태는 미검증. ComfyUI 계획과 무관 |
| GGUF DiT | Abiray·realrebelai는 stock city96 ComfyUI-GGUF 사용 가능. unsloth·leejet은 leejet fork 필요 | 헤더를 range 요청으로 확인. pottokao README (2026-09-23) |
| GGUF TE | add-on `ComfyUI-GGUF-Qwen3VL-TE` 필요. 없으면 `[1, 512, 12288]` shape 오류. 로더 type은 `qwen_image` | pottokao가 2026-09-23 ComfyUI 0.36.0 + ComfyUI-GGUF 6ea2651에서 검증 |

### 4.5 Forge와 기타 도구
- **Forge**: 지원하지 않는 것으로 간주한다.
  - Forge Neo에 기능 요청 #1481 "[Feature Request] Qwen-Image-2.1 support in Forge Neo"가 올라와 있다(스니펫, ~2026-09-20).
  - 비공식 확장 "Project Invisible"은 미검증이다.
  - Forge의 기존 Qwen-Image 지원은 구 아키텍처용이다. 2.1은 DiT, VAE, TE가 모두 다르다(추론).
- **학습 도구**: DiffSynth-Studio에 Qwen-Image-2.1 문서 페이지가 있다(스니펫). musubi-tuner와 ai-toolkit 지원은 미검증이다.


### 4.6 Hugging Face 전수 점검 (2026-09-24)

3090 포드 조건(24 GB VRAM, sm_86, ComfyUI 로드 가능, safetensors/GGUF만, 출처·라이선스, 비게이트)으로 HF를 다시 훑었다.

- **범위**: base_model 트리, 키워드 검색, 공식 repo를 합쳐 226개를 찾았고, 관련 있는 204개를 판정했다.
- **판정**: 권장 1, 대안 24, 보조 25, 부적합 154. 권장·대안 25개는 별도 검증자가 다시 확인했고, 그중 20개가 부적합으로 내려갔다. 보조 25개는 반박 검증을 하지 않았다.
- **확인 방법**: HF API의 파일 크기·sha256·라이선스·게이트 여부, safetensors/GGUF 헤더 Range 읽기, 일부 텐서를 업스트림 0919 체크포인트와 바이트 비교.

**권장**

| repo | 파일 | 바이트 | 비고 |
|---|---|---|---|
| Comfy-Org/Qwen-Image-2.1 | `diffusion_models/qwen_image_2.1_bf16.safetensors` | 14,230,280,616 (sha256 앞자리 89f4158d066cc339) | 업스트림 0919 가중치와 바이트 일치를 표본 확인. 코어 로더만 필요 |
| Comfy-Org/Qwen3-VL | `text_encoders/qwen3vl_8b_fp8_scaled.safetensors` | 10,588,637,512 (4ba424cf62e51392) | 공식, apache-2.0. comfy_quant `float8_e4m3fn`(ConvRot 아님). sm_86에서는 저장 형식으로만 쓰여 속도 이득 없음(미시험) |
| Comfy-Org/Qwen-Image-2.1 | `vae/qwen_image_2.1_vae_bf16.safetensors` | 675,509,688 (bb21f7473051e1ac) | |

- 2.1 TE는 stock Qwen3-VL-8B-Instruct와 같다(750개 키 동일, 표본 텐서 6개 동일). 그래서 Comfy-Org/Qwen3-VL의 TE를 그대로 쓸 수 있다.
- 같은 repo의 int8_convrot(DiT 7,256,783,064 / TE 9,350,798,360)와 w4a8 TE는 comfy-kitchen ConvRot 커널이 필요하다. sm_86 동작이 미검증이라 2순위다.

**대안 (검증 통과)**

| repo | 비고 |
|---|---|
| Abiray/Qwen-Image-2.1-GGUF | 헤더 arch=qwen_image. Q8_0이 0919 가중치의 재양자화와 정확히 일치. stock city96 로드는 미검증. 커뮤니티 제작 |
| AlperKTS/Qwen-Image-2.1-GGUF | arch=qwen_image, Q8_0이 0919와 일치. ComfyUI 워크플로 포함. 커뮤니티 제작 |
| realrebelai/Qwen-Image-2.1_GGUFs | 가중치는 정상이나 라이선스 미표기, 파일 라벨과 내용 불일치. 약한 대안 |
| pottokao/Qwen-Image-2.1-DiT-GGUF | Q8_0만 확인. 제작자 계정의 repo 대부분이 검열 해제·파생판이라 공식 TE와만 조합할 것 |

**부적합으로 판정한 주요 유형**

- GGUF에 architecture 메타데이터가 없어 포크 로더가 필요: unsloth, leejet, molbal(`qwen_image21`), vantagewithai(`flux`로 잘못 표기).
- 가중치 변형: abenzerps "Uncensored"(DiT attention 가중치가 업스트림과 다름. 표본에서 bf16 값의 2–18%가 바뀜).
- 공식 repo의 단순 복제본(HF "Duplicate"): chfm, EllipsesMark, taurusduan, toxicdog, TopherAU 등. 공식 repo가 비게이트라 쓸 이유가 없다.
- 실험적 INT4/W4A8/DF11: toxicdog·chfm INT4ConvRot, NidAll, tsolful, mingyi456. 커널·로더가 미검증이다.
- 공식 `Qwen/Qwen-Image-2.1`: diffusers 레이아웃이라 ComfyUI에서 직접 로드할 수 없다. 출처 기준으로만 쓴다.
- Qwen3-VL GGUF TE(Qwen 공식, unsloth): 검토되지 않은 add-on 노드가 필요하고, fp8_scaled 대비 이점이 없다.

**보조 (선택, 반박 검증 없음)**

- Viggle/Qwen-Image-2.1-viggle-turbo: 4–5 step 증류 LoRA, 제작사 원본. ComfyUI 키 변환본은 t8star(원본과 페이로드 일부 일치 확인).
- 공식 PE-T2I/PE-I2I(bf16, 단독 실행만 24 GB에 들어감), prithivMLmods PE GGUF, ML-Intern-lab Pocket-2B(증류 PE).
- 커뮤니티 LoRA 다수(편집·스타일). 라이선스 표기가 업스트림과 다른 것이 있어 비상업으로 취급한다.

**다운로드 주의**: Comfy-Org DiT는 2026-09-19T10:04Z, VAE는 09-18T14:26Z에 교체됐다. 그 전에 받은 파일(구 DiT 14,230,284,584 B, 구 VAE 675,508,656 B)은 구버전이다. TE는 바뀌지 않았다.


### 4.7 텍스트 인코더 heretic·abliterated 변형 (2026-09-24, 사용자 선택)

사용자가 TE를 heretic 또는 abliterated 변형으로 쓰기로 했다. HF에서 Qwen3-VL-8B-Instruct 기반 변형을 찾아(59개 repo) ComfyUI 적합성과 변경 범위를 확인했다. ComfyUI에서 실제로 로드해 보지는 않았다.

**ComfyUI 키 레이아웃 기준**
- 코어 CLIPLoader(type `qwen_image`)용 Comfy-Org `qwen3vl_8b_bf16`은 750개 키다: `model.layers.*` 396, `model.embed_tokens`, `model.norm`, `model.visual.*` 351, `lm_head.weight`.
- HF 원본(4개 분할 파일)과의 차이는 접두사 `model.language_model.` → `model.` 하나뿐이다. 텐서 내용은 같다.
- 따라서 HF 레이아웃 변형은 분할 파일을 합치고 접두사를 바꿔야 한다. 합치기만 하면 키가 맞지 않는다. ComfyUI가 HF 키를 자동으로 바꿔 주는지는 미검증이다.

**순위**

| 순위 | repo / 파일 | 크기(B) | 로드 방식 | 변경 범위(원본 대비) | 비고 |
|---|---|---|---|---|---|
| **1 (적용)** | pottokao/Qwen-Image-2.1-Text-Encoder-Heretic / `qwen3vl_8b_bf16_heretic.safetensors` | 17,534,334,584 | 코어 CLIPLoader 그대로. 750개 키의 이름·dtype·shape·오프셋이 Comfy-Org bf16과 일치 | 57개 텐서만 다름(o_proj L5–35, down_proj L10–35). 비전 타워 351개, embed_tokens, lm_head는 원본과 동일 | Heretic v2.0.0.dev0, 카드 기준 거부 5/100, KL 0.0220. apache-2.0, 비게이트. sha256 `b1f17ffe…4b1`, 리비전 `047e5434…` |
| 2 | DreamFast/Qwen3-VL-8B-Heretic-1.3.0 / `comfyui/qwen3-vl-8b-heretic-1.3.0.safetensors` | 17,534,334,584 | 코어 CLIPLoader 그대로(Comfy 레이아웃) | 53개 텐서(o_proj L9–35, down_proj L10–35). 비전 타워 동일 | 거부 6/100, KL 0.0314. 제작자 이력이 더 길다. 같은 repo의 fp8·nvfp4 파일은 쓰지 않는다 |
| 3 | AEmotionStudio/qwen3vl-8b-abliterated-fp8-scaled | 10,588,637,512 | 공식 fp8_scaled와 오프셋까지 동일 구조 | 가중치 분석상 huihui abliteration을 재양자화한 것 | 디스크를 줄이려면 이것. 카드에 방법·지표 없음 |
| 4 | heretic-org/Qwen-3-VL-8B-Instruct-heretic | HF 분할 | 병합 + 접두사 변경 필요 | 59개 텐서, 비전 타워 동일 | 문서화가 가장 좋음(KL 0.0214, 거부 6/100) |
| 5 | huihui-ai/Huihui-Qwen3-VL-8B-Instruct-abliterated | HF 분할 | 병합 + 접두사 변경 필요 | 72개 텐서(모든 층의 o_proj, down_proj) | 널리 쓰이는 원조 abliteration. 지표 없음 |

**쓰지 않는 것**
- pottokao의 fp8(스케일 없음, 약 3% 가중치 오차)·int8 convrot·W4A8 파일: 로드 또는 3090 커널이 미검증이다.
- GGUF TE(HauhauCS, mradermacher, noctrex 등): 검토되지 않은 add-on 노드가 필요하고, mmproj가 없으면 편집에 쓸 수 없다.
- 미러 repo(alexbird, beycanai, kkxao, chfm 등): 원본에서 받는다.
- catplusplus: lm_head가 없고 Heretic 도구가 아닌 자체 방법이다.
- 8B-Instruct가 아닌 변형(Thinking, 4B, 32B, Qwen2.5-VL): 호환되지 않는다.

**주의**
- Qwen-Image-2.1 본체는 원본 TE로 학습됐다. 변경 범위는 o_proj·down_proj 일부지만, 프롬프트 반영이나 품질이 달라질 수 있다. 공식 TE와 같은 시드로 비교한다(7.3).
- HF 레이아웃 변형을 쓸 때의 변환(포드에서 실행, 62 GB RAM에 들어감):

```python
import glob
from safetensors.torch import load_file, save_file
sd = {}
for f in sorted(glob.glob('model-0000*-of-0000*.safetensors')):
    sd.update(load_file(f))
sd = {('model.' + k[len('model.language_model.'):] if k.startswith('model.language_model.') else k): v for k, v in sd.items()}
assert len(sd) == 750
save_file(sd, 'models/text_encoders/<이름>.safetensors', metadata={'format': 'pt'})
```

---

## 5. 현재 포드(RTX 3090 24GB) 적용 가능성

### 5.1 선결 조건

| 조건 | 요구 | 현재 | 판정 |
|---|---|---|---|
| ComfyUI | ≥0.37.0 | 미확인 | 확인 필요 |
| PyTorch | cu130 빌드(torch ≥2.11 또는 +cu130) | 2.5.1+cu121 | **미달** |
| NVIDIA 드라이버 | r580+ | 580.65.06 (`project/HANDOFF.md`, 2026-09-21 기록). Community Cloud 호스트 드라이버는 **바꿀 수 없음** | **충족**(기록 기준). `nvidia-smi`로 재확인 |
| GPU | comfy-kitchen sm_80 코드의 sm_86 호환 | sm_86 | 미검증(추론상 가능) |
| 커스텀 노드 | cu121용 xformers, sageattention 등을 새 torch에 맞게 재설치·재빌드 | — | 새 venv에서 처리 |

- 기록상 드라이버는 580.65.06이라 cu130 경로가 열려 있다. 만약 재확인 결과 580 미만이면 cu130과 ConvRot 고속 경로는 막힌다.
  - 이 경우 torch 2.7–2.10(cu12.x), ComfyUI ≥0.37, GGUF 또는 bf16 조합만 남는다(추론).
  - ConvRot eager 폴백은 GGUF보다 느릴 수 있다(#16470 스니펫).
  - ROCm에서는 NaN이나 검은 이미지가 나왔다는 보고가 있다(#15084 스니펫). 미검증.

### 5.2 구성안

| 안 | 파일 | 디스크 | 예상 VRAM | 조건 | 평가 |
|---|---|---|---|---|---|
| **S (권장, 2026-09-24 갱신)** | Comfy-Org bf16 DiT + Comfy-Org/Qwen3-VL `qwen3vl_8b_fp8_scaled` + VAE bf16 | 25.49 GB | 1024² 피크 약 16–18 GB로 추정(미검증). TE는 인코딩 후 RAM으로 오프로드 | ComfyUI ≥0.37. ConvRot·comfy-kitchen 불필요. FP8 TE는 sm_86에서 저장 형식으로만 쓰여 속도 이득은 없음(미시험) | 특수 커널 의존이 없어 가장 안전 |
| S' | S에서 TE만 `qwen3vl_8b_bf16`(17.53 GB) | 32.44 GB | S와 같음 | ComfyUI ≥0.37 | FP8 TE에 문제가 있을 때 |
| **H (사용자 선택, 적용)** | Comfy-Org bf16 DiT + pottokao `qwen3vl_8b_bf16_heretic` + VAE bf16 | 32.44 GB | S'와 같음(TE 크기 동일) | ComfyUI ≥0.37. 코어 CLIPLoader(type `qwen_image`)로 그대로 로드(키 레이아웃 일치, 실제 로드는 미시험) | heretic TE. 비교 기준으로 공식 fp8_scaled TE(10.59 GB)도 함께 받는다 |
| H' | H에서 TE만 AEmotionStudio `qwen3vl8b_abliterated_fp8_scaled`(10.59 GB) | 25.49 GB | S와 같음 | 공식 fp8_scaled와 구조 동일 | abliterated(huihui 계열), 디스크 절약용. 카드에 방법·지표 없음 |
| A (2순위) | Comfy-Org int8 DiT + `qwen3vl_8b_int8_convrot` + VAE bf16 | 17.28 GB | 1024² 기준 피크 12–18 GB로 추정. 16 GB 카드 실측은 약 15 GB | cu130 torch, 드라이버 r580+, ComfyUI ≥0.37, **comfy-kitchen ConvRot의 sm_86 동작(미검증)** | 공식 템플릿 기본값. S가 동작한 뒤 속도·디스크 절약용으로 시험 |
| A' | int8 DiT + `qwen3vl_8b_w4a8` + VAE | 14.24 GB | A보다 낮을 것(추론) | A 조건에 더해 w4a8 커널의 Ampere 동작이 필요(미검증) | 선택 사항 |
| B | bf16 DiT + int8 TE + VAE | 24.26 GB | 17–21 GB로 추정. TE는 인코딩 후 오프로드 | A와 같음(TE가 ConvRot) | 품질 기준선 비교용 |
| C (대체) | Abiray 또는 AlperKTS Q8_0 GGUF(약 7.6 GB) + stock city96 ComfyUI-GGUF + `qwen3vl_8b_fp8_scaled` TE + VAE | 약 18.9 GB | DiT 약 7.6 GB, TE는 스왑 | ComfyUI ≥0.37. stock city96에서의 끝까지 로드는 미검증. GGUF TE는 검토되지 않은 add-on이 필요해 쓰지 않는다 | 디스크·VRAM을 더 줄이고 싶을 때 |
| 비권장 | 전체 bf16 동시 상주(33.1 GB), NVFP4, FP8(연산 이득 없음), Nunchaku W4A4(torch 2.12.1 고정, 상주 21.35 GB), 검열 해제 커뮤니티 가중치 | — | — | — | — |

### 5.3 예상 성능
모두 추정이며 미검증이다.

- **INT8, ConvRot CUDA 백엔드 활성**
  - 1024², 40 steps: 약 25–40 s.
  - 2048², 40 steps: 약 2–3분.
  - 근거는 3090 스니펫(2048×1152, 50 steps에 82–96 s)을 거꾸로 계산한 값이다. 9,216 토큰에서 스텝당 약 1.6–1.9 s.
- **BF16 DiT**
  - 5090에서 INT8보다 약 2배 오래 걸렸다(15.6 s 대 7.6 s). 3090에서도 INT8보다 느릴 것이다.
  - 1024², 40 steps 기준 55–70 s로 추정한다.
- **공통 변수**
  - CFG를 1보다 높이면 시간이 약 2배가 된다.
  - Viggle 4-step은 1024²에서 약 6–10 s에 TE·VAE 시간이 더해진다. ComfyUI 로드는 미검증이다.
  - 편집은 TE 인코딩이 병목이다(disc #31).
- **RAM**
  - 어떤 단일 구성도 62 GB 안에 들어간다(bf16 세트가 32.4 GB, 안 S가 25.5 GB).
  - 로드 중 피크 RAM은 측정되지 않았다.
  - 단, Forge 배치 중 컨테이너 메모리는 45.57 GB(73.5%), 피크 95.6%(약 59.3 GB)가 관측됐다(`docs/OPERATIONAL_VERIFICATION.md:23`). 오프로드된 DiT·TE가 RAM에 올라가면 62 GB 한도를 넘을 수 있으므로 **Forge 배치와 동시에 돌리지 않는다**(추정).

### 5.4 MiniMax H3 키트와의 충돌
- **가중치는 호환되지 않는다.**
  - H3 TE는 `qwen3vl_32b_minimax_h3_*`(Qwen3-VL-32B, hidden 5120, 64층)이고, 2.1 TE는 `qwen3vl_8b`(hidden 4096)다.
  - 잘못 연결하면 "expected [*,4096] but got [1,338,5120]" 오류가 난다(Comfy-Org disc #2, 2026-09-20).
- **소프트웨어 스택은 기술적으로는 공유할 수 있다.**
  - 둘 다 comfy-kitchen ConvRot를 쓴다. H3 README도 cu130에서 int8_convrot을 권장한다. Merserk는 H3에 "ComfyUI 0.30.0+"를 요구한다.
  - 따라서 ComfyUI ≥0.37 + cu130 venv 하나로 둘 다 운용할 수도 있다(추론).
  - 그러나 H3 모바일 킷은 0.30.0에서만 검증되었고, DaSiWa 노드가 0.37에서 동작하는지는 미검증이다. H3 문서(D16)는 0.30.0 고정을 권하므로 기본은 **분리 운용**이다.
- **디스크**
  - H3 키트의 모바일 UI 필수 4개는 약 41.74 GB다(`docs/H3_MOBILE_REQUIREMENTS.md` §6.2. fp16 video VAE 기준, DiT 크기는 미검증).
  - Qwen 안 H(32.44 GB, heretic TE 적용)를 더하면 약 74.2 GB다. 비교용 공식 fp8 TE(10.59 GB)까지 받으면 약 84.8 GB다(안 S 25.49 GB면 약 67.2 GB). 300 GB 볼륨의 알려진 사용량(약 159 GB)을 고려하면 들어갈 가능성이 높지만, 실제 여유 공간은 확인하지 않았다(H3 문서 §5 디스크 행). H3 문서가 권하는 대로 H3를 새 포드에 두면 3090 포드에는 Qwen 세트만 추가된다.
  - 선택 추가분은 bf16 DiT +14.23 GB, PE 파일당 +9.47 GB다.
  - 현재 여유 공간은 확인하지 않았다.
- **VRAM**: 둘을 동시에 올릴 수 없으므로 순차로 쓴다. H3는 32GB+가 필요해 24 GB에서는 강한 오프로드가 필요하다.
- **RAM**
  - 두 세트의 디스크 합계가 약 58.6 GB다. ComfyUI가 둘 다 RAM에 캐시하면 62 GB 한도에 가까워진다.
  - 전환할 때 모델 캐시를 비우거나 ComfyUI를 재시작해야 할 것이다(추정, 실측 없음).
- **H3 TE 대안**: `qwen3vl_32b_minimax_h3_nvfp4_awq`(15,687,142,551 B)는 Comfy-Org 설명상 Blackwell이 필요 없다. 참고로 int8은 27,141,342,152 B, bf16은 51,506,295,256 B다.

### 5.5 포드 정지와 재시작
- **포드 정지·재시작은 필요 없다.** 드라이버는 호스트에 고정돼 있어 어차피 바꿀 수 없다.
- 필요한 작업은 새 venv 생성과 **ComfyUI 프로세스 재시작**(또는 다른 포트로 두 번째 인스턴스 실행)이다. 둘 다 사용자 승인을 받는다.
- Forge는 별도 프로세스라 설정에는 영향이 없다. 다만 동시에 GPU를 쓰면 VRAM을 두고 경합한다(추론).

---

## 6. 활용 방안 (우선순위순)

1. **ComfyUI 이미지 도구 시험** (가치 높음)
   - RGBA 투명 에셋과 배경 제거(공식 템플릿), 글자가 들어간 이미지, 다중 참조 편집(최대 10장)으로 캐릭터 시트나 포즈 변형을 만든다.
   - 결과를 Forge img2img나 ControlNet 입력으로 넘길 수 있다.
   - 3090에 여유 있게 들어가는 몇 안 되는 신규 모델이다. 비상업 용도에 한한다.
2. **H3 키프레임 보조**
   - H3의 I2V, FL2V, Ref2VA 템플릿에 쓸 첫·마지막 프레임과 참조 이미지를 정체성을 유지하는 편집으로 만든다.
   - 두 모델은 순차로 실행한다.
3. **자연어 프롬프트 확장**
   - PE-T2I(int8 9.47 GB, TextGenerate 노드)나 Pocket-2B로 짧은 요청을 JSON `{rewritten_prompt, wh_ratio}`로 바꾼다. Qwen-Image-2.1과 Anima의 자연어 프롬프트에 유용하다.
   - PE-T2I 시스템 프롬프트는 정지 프레임 1장을 약 20문장, 400–500단어로 묘사하고 품질 부스터("masterpiece", "8K")를 금지한다.
   - 그래서 **H3의 샷·모션·오디오 프롬프트에는 맞지 않는다.** 첫 프레임 묘사 정도로만 쓸 수 있다.
   - SDXL 태그 프롬프트에는 쓸모가 없다(CLIP 77토큰 단위).
4. **캡셔닝** (대체로 무관)
   - 2.1은 캡셔너가 아니다.
   - TE가 stock Qwen3-VL-8B-Instruct(apache-2.0)와 같다는 보고가 있으나 미검증이다. 자연어 캡셔너가 필요하면 그 모델을 따로 받는 편이 낫다.
   - Illustrious LoRA 학습에는 Danbooru 태거를 계속 쓴다.

**해당 없음**

| 항목 | 이유 |
|---|---|
| H3 TE 교체 | 불가. 폭이 5120 대 4096이다. PE 모델도 TE가 아니다(Comfy-Org README: "for prompt enhancement, to be used with the TextGenerate node"). Comfy-Org disc #4의 "The PE models only for PE"는 Qwen 직원이 아니라 커뮤니티 사용자의 발언이다 |
| Anima | 공유하는 구성요소가 없다. VAE는 z16·8배·RGB 대 z64·16배·RGBA로 호환되지 않고, TE도 0.6B 대 8B VL이다. 브랜드만 같다 |
| Forge·SDXL·Illustrious | 로드할 수 없고 SDXL LoRA도 옮길 수 없다. 애니 품질이 약하다는 보고도 있다(미검증). 대체재가 아니다 |
| 2.1 LoRA 학습 | 연구용 라이선스와 "Built with Qwen" 의무가 붙는다. 트레이너 지원도 미검증이다. 현재는 우선순위가 낮다 |

---

## 7. 시험 도입 시 요청 사항

### 7.1 사용자가 결정하거나 제공할 것
1. **용도**: 비상업(연구·평가) 한정 사용에 동의하는가? 상업 용도라면 도입을 보류하거나 별도 라이선스가 필요하다.
2. **H3와 환경을 합칠지**: 권장안은 분리다. 2.1은 3090 포드의 별도 ComfyUI(≥0.37)로 시험하고, H3는 `docs/H3_MOBILE_REQUIREMENTS.md`의 D2·D16 결정을 따른다.
3. **새 venv 경로와 운용 방식**
   - 경로 예: `/workspace/venvs/comfyui-next`
   - 기존 ComfyUI를 새 venv로 재시작할지, 다른 포트에서 병행할지.
4. **파일 세트**: 기본은 S(25.49 GB, 2026-09-24 갱신). S가 동작하면 A(int8, 17.28 GB)를 추가로 시험할지, PE-T2I·PE-I2I(각 +9.47 GB)를 추가할지.
5. **가중치 출처**: DiT와 VAE는 공식(Comfy-Org)만 쓴다. TE는 사용자 결정으로 heretic 변형을 쓰되, 4.7에서 원본 대비 변경 범위를 확인한 파일만 쓰고 sha256으로 검증한다. 출처 불명·가중치 변형 DiT(예: abenzerps Uncensored)는 제외한다.
6. **결과물 저장·백업 위치**: 4팀 공유 드라이브는 대상에서 제외한다. 자동 동기화 경로에도 넣지 않는다.

### 7.2 절차와 승인 게이트

**단계 0: 읽기 전용 사전 점검** (시스템을 바꾸지 않음)
- `nvidia-smi`: 드라이버가 기록대로 580.65.06(580 이상)인지 재확인.
- `df -h /workspace`, `free -g`.
- `git -C <ComfyUI> describe --tags`: ComfyUI 버전.
- `/workspace/venvs/comfyui/bin/python -c "import torch;print(torch.__version__)"`.
- 실행 중인 ComfyUI의 프로세스와 포트.
- 결과를 보고한 뒤 경로를 정한다. 드라이버가 580 이상이면 안 A, 미만이면 안 C.

**게이트 1 [승인: 환경과 디스크]**
- 새 venv를 만든다.
  - torch ≥2.11(PyPI) 또는 +cu130 빌드.
  - ComfyUI ≥0.37.0(0.37.1 존재, 스니펫).
  - comfyui-workflow-templates ≥0.11.66(최신 0.11.69).
  - comfy-kitchen, 필요한 커스텀 노드 재설치.
- 기존 venv는 건드리지 않는다(롤백용).
- venv 디스크 사용량은 아직 산정하지 않았다. 단계 0 결과와 함께 제시한다.

**게이트 2 [승인: 다운로드]**
- 받을 파일, 크기, 저장 경로:

| 저장 경로 | 파일 | 바이트 |
|---|---|---|
| `models/diffusion_models/` | `qwen_image_2.1_bf16.safetensors` (Comfy-Org/Qwen-Image-2.1) | 14,230,280,616 |
| `models/text_encoders/` | `qwen3vl_8b_bf16_heretic.safetensors` (pottokao/Qwen-Image-2.1-Text-Encoder-Heretic, 리비전 `047e54342fc4bfcd2addd54049db9c90bb74731e`) | 17,534,334,584 |
| `models/vae/` | `qwen_image_2.1_vae_bf16.safetensors` (Comfy-Org/Qwen-Image-2.1) | 675,509,688 |
| **합계 (안 H)** | | **32,440,124,888** |
| (비교용, 선택) `models/text_encoders/` | `qwen3vl_8b_fp8_scaled.safetensors` (Comfy-Org/Qwen3-VL) | 10,588,637,512 |

- heretic TE sha256: `b1f17ffe6e043c0e1da49ba75fd537d3ea3074fee83b4c9de377bb54689774b1`. 리비전을 고정한 URL로 받는다: `https://huggingface.co/pottokao/Qwen-Image-2.1-Text-Encoder-Heretic/resolve/047e54342fc4bfcd2addd54049db9c90bb74731e/qwen3vl_8b_bf16_heretic.safetensors`.

- 받은 뒤 sha256을 HF API 값과 비교한다(4.6). DiT는 2026-09-19T10:04Z, VAE는 09-18T14:26Z에 교체됐으므로 그 이전에 받은 사본은 쓰지 않는다(구 DiT 14,230,284,584 B, 구 VAE 675,508,656 B).

- 공개 repo라 토큰이 필요 없다. 토큰을 쓰더라도 환경변수로만 전달한다.
- TLS 검증과 프록시 설정은 유지한다.

**게이트 3 [승인: 서비스 재시작]**
- ComfyUI를 새 venv로 재시작하거나, 별도 포트로 인스턴스를 띄운다.
- **포드는 정지하지 않는다.**

**단계 4: 시험**
- 템플릿을 T2I, Image Edit, Background Removal 순서로 돌린다.
- steps를 25에서 **40**으로 올린다(밴딩 방지). CFG 1, euler/simple.
- 1024²에서 시작해 2048급으로 넓힌다. 2K에서는 #16447(mu 0.69 고정) 때문에 흐려질 수 있다.

**단계 5 (선택): H3 전환 시험**
- 모델 캐시를 비우거나 재시작한 뒤 RAM을 확인한다.

### 7.3 수용 기준
- (안 A를 시험할 때만) 시작 로그에 "You need pytorch with cu130 or higher" 경고가 없다(ConvRot CUDA 백엔드 활성). 안 S는 ConvRot를 쓰지 않는다.
- 템플릿 3종이 누락 노드 없이 로드된다.
- 1024², 40 steps T2I가 NaN이나 검은 이미지 없이 생성된다.
  - 피크 VRAM이 24 GB 미만이다(`nvidia-smi` 기록).
  - 소요 시간을 기록해 추정치 25–40 s와 비교한다.
- RGBA 출력 PNG에 알파 채널이 있다.
- heretic TE로 같은 시드·프롬프트를 공식 TE(fp8_scaled)와 비교 생성해, 프롬프트 반영과 품질이 크게 떨어지지 않는지 확인한다(본체는 원본 TE로 학습됐다).
- 참조 2장 이상의 편집이 성공하고, 정체성 유지를 육안으로 확인한다.
- 품질 점검 항목: 황색 톤, VAE 격자, 손, 글자 렌더링, Illustrious와 비교한 애니 품질.
- 기존 venv, Anima, Forge가 정상 동작해 롤백이 가능하다.
- H3와 번갈아 쓸 때 RAM이 62 GB를 넘지 않는다.

---

## 8. 리스크와 미해결 질문

- **라이선스**
  - 비상업 전용이다. 생성물의 상업 이용은 X 게시물과 LICENSE 본문이 엇갈려 모호하다.
  - 상업 문의 메일이 반송된다는 주장이 있다(미검증).
  - 파생 모델에는 "Built with Qwen" 표기 의무가 있고, 위반하면 7.b에 따라 삭제해야 한다.
- **드라이버**: `project/HANDOFF.md` 기록은 580.65.06으로 r580+ 조건을 충족한다. 다만 2026-09-21 기록이므로 단계 0에서 재확인한다.
- **커널 호환성**
  - sm_86에서 ConvRot int8·w4a8·w4a4 커널이 동작하는지 미검증이다. sm_80 바이너리 호환을 추론했을 뿐이다.
  - quant_ops.py의 cu130 조건은 커뮤니티 인용으로만 확인했다.
- **3090 성능**: 1차 벤치마크가 없다. 3090 수치는 모두 추정이거나 스니펫이다.
- **ComfyUI**
  - 0.37.0 출시일(09-20 대 09-21)과 PR #16400은 미검증이다.
  - 버그 #16447, #16470, #16496은 스니펫으로만 확인했다.
- **모델 구성 관련 미확인 사항**
  - TE가 stock Qwen3-VL-8B-Instruct와 같은지 공식 확인이 없다.
  - PE 파라미터가 약 243M 적은 이유를 모른다.
  - VAE가 Qwen-Image-VAE-2.0 계열인지 모른다.
  - 데모(pro 변형)가 오픈 가중치와 다를 수 있다.
- **벤치마크**: 자체 측정이며 GPT Image 2가 빠져 있다. Arena 수치는 스니펫뿐이다. 편집·RGBA 지표가 없다.
- **커뮤니티 가중치**: 검열 해제판과 AIO의 출처·안전성이 불명하고 라이선스 표기도 틀렸다.
- **H3 공존**: RAM 여유가 작다. H3 키트 구성은 가정이고 현재 디스크 여유는 확인하지 않았다.
- **diffusers 경로**: git main이 필요하다. torch 2.5.1에서의 동작은 시험하지 않았다. 필요하면 별도 venv를 쓴다.
- **확인하지 못한 출처**
  - 차단됨: qwen.ai, ModelScope, comfy.org·blog·docs, comfyui-wiki, 다수 언론, x.com.
  - Reddit은 확인하지 못했다.
  - GitHub는 조회 범위 밖이었다.

---

## 9. 출처
URL 옆은 출처에 표시된 날짜이며, 명시가 없으면 2026-09-23 조회 시점 기준이다.

**Hugging Face (직접 조회)**
- https://huggingface.co/Qwen/Qwen-Image-2.1: README, config(sha 790c926), 수정 2026-09-21
- https://huggingface.co/Qwen/Qwen-Image-2.1/blob/main/LICENSE: "Release Date: September 20, 2026"
- https://huggingface.co/api/models/Qwen/Qwen-Image-2.1/commits/main: 2026-09-14~09-21
- https://huggingface.co/Qwen/Qwen-Image-2.1-PE-T2I, https://huggingface.co/Qwen/Qwen-Image-2.1-PE-I2I: 2026-09-20
- https://huggingface.co/spaces/Qwen/Qwen-Image-2.1 (app.py): 생성 2026-09-20. `Qwen/Qwen-Image-2.1-workflow`: 2026-09-20
- https://huggingface.co/Comfy-Org/Qwen-Image-2.1: 생성 2026-09-15, 수정 2026-09-23. discussions #2 (09-20), #4 (09-21), #6, #8 (09-21), #9, #10, #11 (09-22)
- https://huggingface.co/Qwen/Qwen-Image-2.1/discussions: #5 (09-21), #6, #7 (09-20/09-22), #12, #14 (09-22), #28, #29, #31, #32 (09-22), #35 (09-22), #40 (09-23)
- https://huggingface.co/Comfy-Org/Qwen3-VL: 수정 2026-09-20
- https://huggingface.co/Comfy-Org/MiniMax-H3: 생성 2026-07-30, 수정 2026-09-23
- https://huggingface.co/Merserk/MiniMax-H3-INT4-ConvRot: 수정 2026-08-03
- https://huggingface.co/Qwen/Qwen-Image/blob/main/vae/config.json: repo 2025-08-02
- https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct: 2025-10-11
- https://huggingface.co/Qwen/Qwen3-VL-32B-Instruct
- https://huggingface.co/Qwen/Qwen3.5-9B
- 커뮤니티 repo(생성일은 4.3 표 참조)
  - unsloth/Qwen-Image-2.1-GGUF, unsloth/Qwen-Image-2.1-FP8, unsloth/Qwen-Image-2.1
  - leejet/Qwen-Image-2.1-GGUF, Abiray/Qwen-Image-2.1-GGUF, realrebelai/Qwen-Image-2.1_GGUFs
  - toxicdog/Qwen-Image-2.1-INT4ConvRot-ComfyUI, NidAll/Qwen-Image-2.1-Mixed-Balanced, ModelsLab/Qwen-Image-2.1-W4A4-int4
  - SamuelTallet/Qwen-Image-2.1-SDNQ-4bit-dynamic-hadamard256, Rin247/Qwen-Image-2.1-INT8, BennyDaBall/Qwen-Image-2.1-NVFP4
  - Viggle/Qwen-Image-2.1-viggle-turbo (2026-09-22), Winnougan/Qwen-2.1-ComfyUI-AIO
  - pottokao/Qwen-Image-2.1-Text-Encoder-Heretic(-GGUF) (수정 2026-09-23), abenzerps/Qwen-Image-2.1-Uncensored-GGUF
  - tsolful/Qwen2.1_INT4W4A8, Felldude/QWEN_2.1_HDR_VAE, KoalaNation/Qwen2.1-prompt-rewrite-clip
  - cong-gu/qwen2.1 (2024-07-04), bunnycore/Qwen-2.1-7b-Persona-lora_model (2024-11-12)
- https://huggingface.co/obsxrver/ComfyUI-Native-INT8_ConvRot: 날짜 미표기
- HF Papers
  - https://huggingface.co/papers/2605.28091 (Qwen-Image-Bench, 2026-05-27)
  - 2605.10730 (Qwen-Image-2.0, 2026-05-11)
  - 2605.13565 (Qwen-Image-VAE-2.0, 2026-05-13)
  - 2508.02324 (Qwen-Image)

**PyPI (메타데이터·휠 확인)**
- comfy-kitchen 0.2.35 (2026-09-17)
- diffusers 0.40.0 (2026-08-20)
- transformers 5.17.0 (2026-09-09)
- torch 2.11.0 (2026-03-23), 2.14.0 (2026-09-02)
- vllm-omni 0.30.0rc1 (2026-09-23)
- sglang 0.5.20 (2026-09-18)
- comfyui-workflow-templates 0.11.64 (2026-09-20T01:11Z), 0.11.65 (09-20T05:13Z), 0.11.66 (09-20T12:59Z), 0.11.69 (09-23T17:08Z)
- comfyui-workflow-templates-json 0.1.88 (2026-09-20), 0.1.94 (2026-09-22), 0.1.95 (2026-09-23)

**언론·블로그** (대부분 스니펫만)
- https://finance.sina.com.cn/tech/digi/2026-09-20/doc-inisnssu9285198.shtml (2026-09-20)
- https://news.qq.com/rain/a/20260920A0CLE900 (날짜 미검증)
- https://cyberq.tw/2026/09/20/qwen-image-21-open-weighted-download-7b/ (2026-09-20)
- https://www.marktechpost.com/2026/09/21/alibaba-qwen-releases-qwen-image-2-1/ (2026-09-21)
- https://technode.com/2026/09/21/alibabas-qwen-open-sources-qwen-image-2-1-for-unified-image-generation-and-editing/ (2026-09-21)
- 한국어
  - https://www.aitimes.com/news/articleView.html?idxno=215554
  - https://aimatters.co.kr/news-report/52619/
  - https://www.tokenpost.kr/news/ai/411125
  - https://wikidocs.net/blog/@jaehong/31467/
- 영어 기타
  - https://datanorth.ai/news/qwen-releases-qwen-image-2-1
  - https://tech-insider.org/what-alibaba-actually-shipped-on-september-20/
  - https://blog.buildfastwithai.com/qwen-image-2-1-review
  - https://eu.36kr.com/en/p/3991785951198217
  - https://www.heise.de/en/news/Qwen-Image-2-1-Alibaba-s-new-AI-image-model-with-transparency-feature-11461466.html
  - https://mixed-news.com/en/qwen-image-2-1-transparent-rgba-7b-open-weights-research-licence/
  - https://www.eesel.ai/blog/qwen-image-2-1
  - https://ai.rs/ai-for-business/qwen-image-2-1-open-weights-licence-vram
  - https://www.mindstudio.ai/blog/qwen-image-2-1-local-install
  - https://note.com/sepiablue/n/n02026f718c3f (~2026-09-22)
- 공식(차단됨)
  - https://qwen.ai/blog?id=qwen-image-2.1
  - https://modelscope.cn/models/Qwen/Qwen-Image-2.1
- ComfyUI 관련
  - https://blog.comfy.org/p/qwen-image-21-in-comfyui-open-weight
  - https://comfyui-wiki.com/en/news/2026-09-20-comfyui-v0-37-0 (2026-09-20)
  - https://comfyui-wiki.com/en/news/2026-09-21-qwen-image-2-1 (2026-09-21)
  - https://docs.comfy.org/installation/system_requirements
  - docs.comfy.org changelog: v0.37.0 2026-09-21, v0.37.1 2026-09-22
- https://diffsynth-studio-doc.readthedocs.io/en/latest/Model_Details/Qwen-Image-2.1.html

**X** (x.com 차단, 스니펫과 게시물 ID 해석)
- https://x.com/QwenDevs/status/2101504596623630787 (2026-09-20T02:51Z)
- https://x.com/QwenDevs/status/2101917379785838660 (2026-09-21T06:12Z)
- https://x.com/Alibaba_Qwen/status/2101659321549660610 (2026-09-20T13:06Z)
- https://x.com/arena/status/2102416020678008986
- https://x.com/superalesha/status/2101940249735634998
- https://x.com/Oluwaphilemon1/status/2102026943398846739

**GitHub** (조회하지 않음, 스니펫만)
- ComfyUI 이슈 #16447, #16470, #16496, #16443, #15084
- alesha-pro/tools/qwen-image-2.1
- noonghunna/club-3090 discussion #481
- Haoming02/sd-webui-forge-classic issue #1481 (~2026-09-20)
- vllm-omni PR #7759, #7792

**대안 후보**
- https://technode.com/2026/09/18/alibabas-qwen-releases-qwen3-8-omni-flash-with-1m-token-context/ (2026-09-18)
- https://www.marktechpost.com/2026/09/18/alibaba-qwen-releases-qwen3-8-omni-flash/ (2026-09-18)
- https://startupfortune.com/alibabas-qwen38-omni-flash-slashes-audio-pricing-98-and-drops-open-weights/
- https://www.mindstudio.ai/blog/qwen3-8-livetranslate-access-api
- https://www.orcarouter.ai/blog/qwen-3-8-live-translate-launch
- https://pandaily.com/alibaba-qwen-livetranslate-audio-3-1-asr-tts-realtime
- https://pandaily.com/alibaba-qwen4-training-roadmap-5-10t-apsara-2026
- https://www.manilatimes.net/2026/09/22/tmt-newswire/media-outreach-newswire/alibaba-unveils-roadmap-on-full-stack-ai-strategy-from-chips-cloud-infrastructure-models-to-agents/2429925 (2026-09-22)
- https://www.technology.org/2026/09/22/alibaba-zhenwu-v900-ai-chip-qwen-10-trillion/ (2026-09-22)
- https://winbuzzer.com/2026/08/25/alibaba-launches-wan3-0-for-30-second-ai-video-from-documents-xcxwbn/ (2026-08-25)
- https://dataconomy.com/2026/08/24/alibaba-launches-wan30-a-30-second-ai-video-generation-model/ (2026-08-24)
- https://comfyui-wiki.com/en/news/2025-02-25-alibaba-wanx-2-1-video-model-open-source (2025-02-25)
- https://www.alibabacloud.com/blog/alibaba-unveils-its-latest-open-source-video-generation-model_602167
- https://gigazine.net/gsc_news/en/20260212-qwen-image-2/
- https://qwenimages.com/blog/qwen-image-2-release (비공식)
- https://news.aibase.com/news/25422
- https://www.unite.ai/alibaba-launches-qwen-image-3-0-without-benchmarks-or-weights/
- https://qwenlm.github.io/blog/qwen2.5/
