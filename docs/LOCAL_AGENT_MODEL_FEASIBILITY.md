# RunPod에서 8GB 노트북용 AI 에이전트 모델 제작 — 현실성 조사

- 기준일: 2026-09-24. 특별한 표기가 없으면 출처는 모두 이날 조회했습니다.
- 표기
  - **[S]**: 검색 결과 요약(snippet)으로만 확인했고 원문 페이지는 열지 못했습니다.
  - **미검증**: 1차 출처로 확인하지 못했거나 계산·판단으로 낸 추정치입니다.
- 가격은 RunPod Community Cloud의 시간당 달러($/hr) 목록가입니다. 목록가가 있어도 실제로 빌릴 수 있는지는 별개입니다(4.4절).
- 벤치마크 뒤 괄호에는 누가 측정했는지 적었습니다. "자체"는 모델 제작사가 직접 측정한 값입니다.

---

## 0. 결론 요약

- **조건부로 현실성이 있습니다.** 여기서 "제작"은 기존 오픈웨이트 소형 모델(4B~9B)을 RunPod에서 LoRA로 도구호출(function calling)에 특화하고, GGUF로 양자화해 노트북의 llama.cpp, LM Studio, Ollama에서 돌리는 것을 뜻합니다.
  - 도구가 10개 이하인 좁은 과제라면 개인 규모의 성공 사례가 여럿 있습니다.
  - Gitara 3B: 0.12 → 0.92
  - Songgot-X 0.8B, 한국어 FunctionChat SingleCall: 45.2 → 82.2
  - Home-LLM: RTX 3090 한 장으로 LoRA 학습, 97.11%
- **권장 경로는 A → B → C 순서입니다.**
  - A안: 학습 없이 Qwen3.5-9B 또는 4B에 도구 설계를 더하고 평가셋을 만듭니다.
  - B안: A가 부족할 때만 Qwen3.5-4B를 bf16 LoRA로 학습합니다. 보호 포드가 아닌 별도의 임시 Community 포드를 씁니다.
  - C안: 필요하면 GRPO까지 진행합니다.
- **대략적인 비용과 기간**
  - A안: $0, 3~7일
  - B안: 총 $30~150. GPU 비용은 4B $10~60, 9B $20~100이고 데이터 생성 비용은 별도입니다. 파트타임으로 2~4주.
  - C안: $100~400, 1~3개월
- **8GB 노트북의 한계**
  - 현실적인 범위는 dense 모델 4B~9B의 Q4~Q8 양자화입니다.
  - Qwen3.5-9B Q4_K_M을 32k 컨텍스트로 쓰면 실사용 약 7.2GiB 이상으로 빠듯합니다. 16k로 줄이거나 KV 캐시를 q8_0으로 쓰세요.
  - 14B dense 모델은 들어가지 않습니다.
  - 35B급 MoE는 시스템 RAM 32GB와 전문가 가중치 CPU 오프로드가 있어야 합니다.
- **현실성이 없는 것**
  - **처음부터 사전학습**: 3090 한 장으로 3B 모델을 60B 토큰 학습하는 데 약 440일이 걸리고, 옵티마이저 메모리(약 54GB)부터 24GB에 들어가지 않습니다. 결과물도 Qwen3.5-4B에 한참 못 미칩니다.
  - **범용 개인비서를 로컬 소형 모델로 대체**: Claude Opus 4.6을 Qwen3.5-9B로 바꾸면 정확도가 25~39%p 떨어집니다(OpenJarvis).
- **하지 말 것**
  - 보호 포드 `sydh2pm05u5rg2`에서 학습하지 마세요. Forge/ComfyUI와 VRAM·RAM을 나눠 쓰고, 워치독이 Forge를 재시작하며, Google Drive 자동 백업이 돌고 있습니다.
  - Secure 전용 GPU(A40, L4)와 network volume은 쓰지 마세요.
  - Qwen3.5에 QLoRA를 쓰지 마세요.
  - GPT, Claude, Gemini의 출력으로 학습 데이터를 만들지 마세요. 약관상 금지됩니다.
- **가장 큰 불확실성**
  - Qwen3.5의 한국어 단독 점수가 공개되어 있지 않습니다.
  - 노트북의 정확한 GPU와 RAM을 모릅니다.
  - GGUF로 변환한 뒤 도구호출 템플릿과 파서가 맞지 않을 위험이 있습니다.

---

## 1. 질문 해석과 전제

### 1.1 "에이전트 모델 제작"의 의미

| 해석 | 내용 | 현실성 |
|---|---|---|
| (a) 기존 모델 + 에이전트 구성 | 공개 모델을 그대로 쓰고 도구(MCP), 프롬프트, 실행 루프를 설계합니다 | 높음. 가장 먼저 할 일 |
| (b) 기존 모델 미세조정 | LoRA/QLoRA/SFT로 도구호출 형식과 한국어 명령을 학습시키고, 필요하면 DPO나 GRPO를 더합니다 | 좁은 과제에서는 높음 |
| (c) 처음부터 사전학습 | 모델 가중치를 새로 만듭니다 | 사실상 없음(8절) |

- 에이전트는 모델(두뇌)과 하네스(도구, 메모리, 루프)를 합친 것입니다. 성능의 상당 부분이 하네스에서 나옵니다.
- OpenJarvis(https://huggingface.co/papers/2605.17172, 2026-05)의 결과:
  - 프롬프트, 도구 설명, 런타임 설정을 모두 다시 조정하면 로컬 모델 교체로 생긴 성능 하락의 56~77%를 회복했습니다.
  - 프롬프트 최적화만으로는 약 5%p만 회복했습니다.
  - 단, 최적화 과정에서 클라우드 프런티어 모델을 제안자로 썼습니다.

### 1.2 노트북 전제

- GPU: 8GB GDDR7 NVIDIA 노트북 GPU. RTX 5050, 5060, 5070 Laptop 중 하나로 추정되며 Blackwell(sm_120)입니다.
- 모델명, TGP, 시스템 RAM, OS는 확인하지 못했습니다(미검증). RAM은 16~32GB로 가정했습니다.
- OS는 Windows일 가능성을 염두에 두고 주의점을 함께 적었습니다.

### 1.3 RunPod 운영 규칙(CLAUDE.md)

- Community Cloud만 씁니다. Secure Cloud는 금지입니다.
- 포드 `sydh2pm05u5rg2`는 **절대 정지하지 않습니다**.
  - 사양: RTX 3090 24GB, 컨테이너 RAM 62GB, 볼륨 300GB 중 약 159GB 사용 중.
  - Forge와 ComfyUI가 돌고 있습니다.
  - 공개 프록시가 404를 반환해 현재 상태는 미검증입니다.
- 토큰은 환경변수로만 전달합니다.
- 4팀 공유 드라이브에는 어떤 경로로도 접근하거나 업로드하지 않습니다.
- 이번 조사에서 호출한 RunPod API는 읽기 전용 GraphQL `gpuTypes` 가격·재고 조회뿐입니다. 상태를 바꾸는 호출은 하지 않았습니다.

---

## 2. 노트북(8GB)에서 돌릴 수 있는 한계

### 2.1 GPU 기준

| GPU (노트북) | VRAM / 버스 / 대역폭 | TGP | 출처 |
|---|---|---|---|
| RTX 5050 Laptop | 8GB GDDR7, 128-bit, 약 384 GB/s | 35/50~100W | [S] videocardz, notebookcheck |
| RTX 5060 Laptop | 8GB GDDR7, 128-bit, 384 GB/s | 45~100W | [S] videocardz |
| RTX 5070 Laptop | 8GB 또는 12GB GDDR7, **둘 다 128-bit, 384 GB/s** | 50~100W | [S] videocardz, thefpsreview(2026-04-29) |
| (참고) RTX 5070 Ti Laptop | 12GB, 192-bit, 약 672 GB/s | – | [S] |

- 배치 1 디코딩은 메모리 대역폭이 결정합니다. 따라서 5050, 5060, 5070 Laptop의 **토큰 생성 속도는 거의 같다**고 봐야 합니다.
- 프롬프트 처리(prefill)는 연산량이 결정하므로 코어 수와 TGP를 따라갑니다(스펙에서 추론, 미검증).
- 노트북에서도 compute capability는 12.0(sm_120)입니다. 드라이버 R570 이상, CUDA 12.8 이상이 필요합니다([S] NVIDIA 포럼 Blackwell 마이그레이션 가이드).

### 2.2 VRAM 계산 (가중치 + KV 캐시)

**계산식**
- 토큰당 KV 바이트 = 2(K와 V) × KV를 따로 가진 어텐션 레이어 수 × KV 헤드 수 × head_dim × 2B(fp16)
- 예: Qwen3.5는 풀어텐션 레이어가 8개이므로 2 × 8 × 4 × 256 × 2B = 32 KiB/토큰입니다. 여기에 DeltaNet 고정 상태 48 MiB가 더해집니다.

**가용 예산**
- 8 GiB에서 CUDA 컨텍스트와 계산 버퍼 0.3~1.0 GiB(미검증), Windows 디스플레이 예약(미검증)을 빼면 가중치와 KV에 쓸 수 있는 것은 약 7.0~7.5 GiB입니다.
- Qwen3.5 계열은 어휘가 248,320개라서 logits 버퍼만 약 0.51GB입니다(248,320 × n_ubatch 512 × 4B). 그래서 오버헤드는 범위의 상단으로 잡아야 합니다.
- 아래 표의 수치는 오버헤드를 **포함하지 않은** 값입니다.

| 모델 / 양자화 | GGUF 파일 (HF 실측 바이트) | KV/토큰 (f16) | 8k 합계 GiB | 32k 합계 GiB | 판단 |
|---|---|---|---|---|---|
| Qwen3.5-4B Q4_K_M | 2.74 GB (2.55 GiB) | 32 KiB + 48 MiB | 2.85 | 3.60 | 여유 |
| Qwen3.5-4B Q8_0 | 4.48 GB (4.17 GiB) | 32 KiB + 48 MiB | 4.47 | 5.22 | 여유. **안전한 기본값** (Q5/Q6도 권장) |
| Qwen3.5-9B Q4_K_M | 5.68 GB (5.29 GiB) | 32 KiB + 48 MiB | 5.59 | 6.34 | 32k는 오버헤드를 넣으면 **약 7.2 GiB 이상이라 빠듯**. 16k, q8_0 KV, `-ub 256` 중 하나를 쓰세요 |
| Qwen3.5-9B Q5_K_M | 6.58 GB (6.13 GiB) | 동일 | 6.42 | 7.17 | 비권장 |
| Qwen3.5-9B + 비전 mmproj | +0.92 GB | – | – | Q4 32k가 오버헤드 전에 이미 약 7.2 | 불가 |
| Gemma-4-E4B Q4_K_M / Q5_K_M | 4.98 / 5.48 GB | 약 16 KiB + 20 MiB | 4.78 / 5.25 | 5.15 / 5.62 | 여유. 가장 편한 Gemma 선택지 |
| Gemma-4-12B IQ4_XS | 6.38 GB (5.94 GiB) | 8 KiB + 320 MiB (슬라이딩 윈도) | 6.31 | 6.50 | 16k 이하에서만 현실적. llama.cpp의 KV 저장 방식이 미검증이므로 0.1~0.2 GiB를 더 잡으세요 |
| Gemma-4-12B QAT Q4_0 / Q4_K_M | 6.98 / 7.12 GB | 동일 | 6.87 / 7.01 | 7.06 / 7.20 | 일부 레이어를 CPU로 오프로드해야 합니다 |
| Kanana-2-3B Q8_0 | 3.73 GB (3.48 GiB) | **128 KiB** | 4.48 | 7.48 (q8_0 KV면 약 5.6) | 32k에서는 q8_0 KV가 필수입니다 |
| Qwen3-8B Q4_K_M (전 레이어 풀어텐션) | 5.03 GB | 144 KiB | 약 5.8 | 약 9.2 (q8 KV면 약 7.1) | 16k까지 |
| Granite-4.2-8B Q4_K_M | 5.35 GB | 160 KiB | 6.23 | 9.98 | 8~16k만 |
| LFM2.5-8B-A1B Q5_K_M | 6.03 GB | 12 KiB | 5.71 | 5.99 | 여유 (라이선스 조건은 3절) |
| Ministral-3-14B / Qwen3-14B Q4_K_M | 8.24 / 9.00 GB | 160 KiB | 8.92 / – | 12.67 / – | **불가** |

- 파일 크기 출처: https://huggingface.co/unsloth/Qwen3.5-9B-GGUF, https://huggingface.co/unsloth/Qwen3.5-4B-GGUF, https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF, https://huggingface.co/unsloth/gemma-4-12b-it-GGUF, https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf, https://huggingface.co/mradermacher/kanana-2-3b-instruct-GGUF, https://huggingface.co/Qwen/Qwen3-8B-GGUF 등.
- 구조 수치의 출처는 각 모델의 config.json입니다.
- Qwen3.5 모델카드는 thinking 능력을 유지하려면 컨텍스트를 128K 이상으로 두라고 권합니다. 8GB에서는 불가능하므로 **도구 루프는 non-thinking 모드**로 설계하세요.

### 2.3 MoE 모델: 전문가 가중치를 시스템 RAM에 두는 경우

| 모델 | GGUF | 시스템 RAM 요구 | 비고 |
|---|---|---|---|
| Qwen3.6-35B-A3B | UD-Q4_K_M 22.13 GB (UD-IQ2_M 11.52 GB) | 전문가 약 4~5GB를 GPU에 두면 RAM 16~17GB, 전부 CPU로 보내면 약 20GB. **RAM 32GB 필요** | 전문가 32.2B 파라미터, 토큰당 약 1.0B만 사용. RAM이 16GB면 IQ2_M만 가능하고 품질이 떨어집니다 |
| Gemma-4-26B-A4B | UD-Q4_K_M 16.95 GB | 약 10GB | [S] RTX 4060 Laptop 8GB와 RAM 16GB에서 `-cmoe`로 64K 컨텍스트 약 25 tok/s라는 1인 보고가 있습니다(미검증) |
| gpt-oss-20b | MXFP4 12.11 GB | 약 5~6GB가 RAM으로 넘어감. RAM 16GB로 가능 | 토큰당 전문가 약 2.39B 사용 |

### 2.4 런타임 소프트웨어 (sm_120, 8GB)

| 런타임 | 최신 버전 (날짜) | 8GB 적합성 | 주의 |
|---|---|---|---|
| **llama.cpp** (llama-server) | 롤링 빌드 | **최적** | sm_120 지원. NVFP4 네이티브는 b8967(2026-04-29)부터[S]. 도구호출에는 `--jinja`가 필요합니다. MTP 추측 디코딩[S]과 웹 UI의 MCP 호스트 기능[S]이 있습니다 |
| **LM Studio** | 0.4.25 (2026-09) [S] | 적합 | RTX 50은 0.3.15부터, MCP 호스트는 0.3.17부터[S]. OpenAI/Anthropic 호환 API, 헤드리스 `llmster` 데몬 제공 |
| **Ollama** | v0.34.3 (2026-09-19, Go 모듈 프록시) | 적합 | VRAM이 24GiB 미만이면 **기본 컨텍스트가 4k**라 `num_ctx`를 32k 이상으로 올려야 합니다[S]. v0.34.1부터 GGUF 변환, 양자화, LoRA 어댑터 GGUF 생성 기능이 빠졌습니다[S]. 네이티브 MCP 클라이언트는 없습니다[S]. Windows에서 드라이버 616.92와 v0.34.x 조합으로 CPU 폴백이 생기는 이슈(#18581)가 있습니다[S] |
| ExLlamaV3 | 1.5.1 (2026-09-22) | 가능하지만 틈새 | Windows에서는 빌드 도구가 필요합니다 |
| vLLM / SGLang / TensorRT-LLM / NIM | 0.30.0 / 0.5.20 / 1.2.1 / – | **비현실적** | 리눅스·데이터센터용이고 메모리를 미리 크게 잡습니다. TensorRT-LLM은 Windows 지원 중단[S] |

### 2.5 예상 속도 (384 GB/s 기준, 미검증 추정)

**실측 기준점**(모두 [S] localscore.ai, Llama-3.1-8B Q4_K_M)
- RTX 4060 Laptop(256 GB/s): 토큰 생성(tg) 36.0 tok/s, 프롬프트 처리(pp) 1,365 tok/s
- RTX 5070 Ti Laptop(672 GB/s): tg 65.6 tok/s

**추정치**

| 크기 (Q4_K_M) | 디코드 tok/s | 프롬프트 처리 tok/s | 체감 |
|---|---|---|---|
| 약 4B (2.7GB) | 약 60~95 | 약 3,000~6,000 | 에이전트 루프에 충분 |
| 8~9B (5.0~5.7GB) | **약 33~53** (이론 상한: 9B Q4 약 67) | 약 1,300~2,500 | 적정선 |
| 14B (부분 오프로드) | 약 4~15 | 급락 | 다단계 에이전트로는 비실용적 |
| 26~35B MoE + 전문가 오프로드 | 약 20~30 (1인 보고) | 약 200~300 | RAM 32GB 필요 |

- 하이브리드 어텐션 모델(Qwen3.5, Gemma 4 E4B)은 32k에서 속도가 10~20%만 떨어집니다(계산).
- Qwen3-8B 같은 풀어텐션 모델은 32k에서 약 0.65배로 느려집니다.
- 첫 턴에 1~2만 토큰짜리 하네스 프롬프트를 넣으면 첫 토큰까지 약 5~13초가 걸립니다. 이후 턴은 프리픽스 캐시를 재사용합니다.

### 2.6 Blackwell과 Windows 주의점

- **NVFP4**
  - 파일 크기는 Q4_K_M보다 0~10% 작은 수준입니다.
  - 배치 1 디코드 속도는 거의 그대로이고 프롬프트 처리만 빨라집니다([S] RTX 5090 기준 +43~68%).
  - **Q4_K_M(또는 imatrix Q4/Q5)이 안전한 기본값**입니다.
  - RunPod의 3090(sm_86)으로는 FP4 경로를 검증할 수 없으므로, 노트북에서 직접 측정해야 합니다.
- **Windows 공유 메모리 폴백**
  - VRAM이 넘치면 공유 메모리로 조용히 흘러가 5~10배 느려집니다.
  - NVIDIA 제어판에서 `CUDA – Sysmem Fallback Policy`를 **Prefer No Sysmem Fallback**으로 바꾸세요([S] runaihome.com).
- **TGP 편차**
  - 같은 GPU 이름이라도 노트북마다 성능이 50~60% 다를 수 있습니다[S].
  - 전원을 연결하고 성능 모드로 둔 상태에서 `llama-bench -d 0,16384,32768`로 측정하세요.

---

## 3. 추천 베이스 모델

**선정 기준**
- 8GB에 16~32k 컨텍스트로 들어가는가
- 공개된 에이전트·도구 점수
- 한국어 근거
- 라이선스
- RunPod에서 학습할 수 있는가
- 런타임 지원

주의: 아래 점수는 대부분 **제작사 자체 측정**입니다. 독립 리더보드(BFCL 사이트)는 이 환경에서 접근이 차단되어 확인하지 못했습니다.

| 순위 | 모델 (HF repo) | 파라미터 / 컨텍스트 | 라이선스 | 도구호출 | 에이전트 점수 (측정 주체) | 한국어 근거 | GGUF (HF) | 8GB 적합 | RunPod 학습 |
|---|---|---|---|---|---|---|---|---|---|
| **1 (학습 기본값)** | Qwen/Qwen3.5-4B (2026-02-27) | 4.66B (비전 포함), 262K. 하이브리드: DeltaNet 3개당 어텐션 1개 | Apache-2.0 | XML 형식 `<tool_call><function=…><parameter=…>`, 파서는 `qwen3_coder`. 기본값이 thinking 모드 | BFCL-V4 50.3, TAU2 79.9 (자체). BFCLv4 50.56 또는 54.01, Tau² Telecom 87.72 / Retail 71.93 (Liquid 측정) | MMMLU 76.1, MMLU-ProX 71.5 (자체). **한국어 단독 점수 미공개** | Q4_K_M 2.74 / Q5 3.14 / Q8 4.48 GB | 여유 (Q8, 32k에서 5.22 GiB) | bf16 LoRA 약 10GB(미검증)라 3090/4090으로 가능. 가장 싸고 안전한 학습 대상 |
| **2 (학습 없이 쓸 때 최고 성능)** | Qwen/Qwen3.5-9B (2026-02-27) | 9.65B, 262K | Apache-2.0 | 4B와 동일 | BFCL-V4 66.1, TAU2 79.1 (자체). BFCLv4 60.13 (Liquid) | MMMLU 81.2, MMLU-ProX 76.3 (자체). 한국어 단독 점수 미공개 | Q4_K_M 5.68 / IQ4_XS 5.17 / Q5 6.58 GB | Q4에 16k 권장. 32k는 빠듯 | bf16 LoRA 약 22GB. 24GB 카드에서는 짧은 시퀀스만 되므로 32~48GB 카드를 권장. **QLoRA 비권장** |
| 3 | google/gemma-4-E4B-it (대안: gemma-4-12B-it IQ4_XS) | E4B는 총 8.0B(effective 4.5B), 128K. 12B는 11.96B, 256K | Apache-2.0 | 네이티브 function-call 토큰(`<\|tool_call>`)과 thinking 토글 | E4B Tau2 42.2. 12B Tau2 평균 69.0 (thinking 모드). 모두 Google 자체 | MMMLU E4B 76.6, 12B 83.4 (한국어를 포함한 14개 언어 합산, 한국어 단독 없음) | E4B Q4 4.98 / Q5 5.48. 12B IQ4_XS 6.38 GB | E4B 여유. 12B는 16k 이하에서 빠듯 | E4B LoRA 17GB / QLoRA 10GB(모두 미검증). 12B는 QLoRA만 가능. 미세조정하면 QAT 이점이 사라집니다 |
| 4 (한국어 근거 최다) | kakaocorp/kanana-2-3b-instruct (2026-07-27 공개) | 3.51B, qwen3 아키텍처, 32K | Kanana Open License. 조건은 아래 참고 | `qwen3_coder` 파서 | BFCL-v3 Live 71.94, Multi-turn 17.12 (Kakao 자체) | KoMT 6.92, KMMLU-CoT 43.32, HAERAE-CoT 43.75, KoSimpleQA 22.29 (Kakao 자체) | Q8_0 3.73 GB. 커뮤니티 GGUF만 있음 | 32k는 q8 KV로 약 5.6 GiB | 가중치가 약 7.0GB(bf16)라 24GB에서 LoRA가 여유로움(추정) |
| 5 (RAM 32GB일 때만) | Qwen/Qwen3.6-35B-A3B (2026-04-15) | 35.95B, 활성 약 3B, 262K | Apache-2.0 | `qwen3_coder` | TAU3 67.2, MCP-Atlas 62.8, Terminal-Bench 2.0 51.5 (자체) | 다국어 수치 없음 | UD-Q4_K_M 22.13 GB | 전문가 오프로드와 RAM 32GB 필요 | 3090 한 장으로는 학습 불가(bf16 LoRA가 필요하고 4bit는 비권장). **데이터를 만드는 teacher로 활용** |

**Kanana Open License 조건**
- 개인 용도와 자체 서비스에서는 쓸 수 있습니다.
- 배포하면 "Powered by Kanana"를 표시해야 하고, Kanana 출력으로 학습한 모델을 배포할 때는 이름 앞에 "Kanana"를 붙여야 합니다.
- 제3자에게 API, 온프렘, 온디바이스로 제공하려면 Kakao의 상용 라이선스가 필요합니다. 절대 금지는 아닙니다.

**점수 해석 시 주의**
- Qwen3.5의 TAU2 점수는 airline 도메인에 수정한 하네스를 적용해 측정했습니다. 그래서 4B(79.9)가 9B(79.1)보다 높게 나옵니다.
- 같은 Qwen3.5-4B 파생 모델인 Trida2.0-4B는 Trillion 자체 하네스에서 tau2 retail/airline/telecom을 0.40/0.50/0.80으로 보고했습니다(https://huggingface.co/trillionlabs/Trida2.0-4B, 2026-09-18). **실제로 써 보면 79 수준을 기대하기 어렵습니다.**
- non-thinking 모드에서는 점수가 더 낮을 수 있습니다(미검증).
- 한국어 언어 혼용 위험: https://huggingface.co/papers/2604.16235 에서 **이전 세대 Qwen3-4B**가 시험한 모델(Qwen3, Gemma-3, Llama-3, Aya) 가운데 한국어 단어 수준 안정성이 가장 낮았습니다(0.8882). Qwen3.5를 측정한 결과는 아닙니다.

**차순위**
- **LiquidAI/LFM2.5-8B-A1B**
  - 전부 VRAM에 들어갑니다(Q5 32k에서 5.99 GiB).
  - BFCLv4 49.73, Tau² Telecom 88.07. 같은 카드의 다른 표에는 48.50으로 적혀 있어 ±1 정도는 제작사 측정 노이즈로 보세요.
  - 라이선스는 LFM Open v1.0으로, 연매출 $10M 이상인 기업은 상용 사용이 허락되지 않습니다.
- **ibm-granite/granite-4.2-8b**
  - Apache-2.0.
  - τ³-bench(AVG) 58.06, BFCL v4 52.39. 3B는 45.78과 52.41입니다.
  - KV 캐시가 커서 16k까지만 현실적입니다.
- **openai/gpt-oss-20b**
  - Apache-2.0.
  - MMMLU 한국어 77.6 (high 추론).
  - Tau-Bench Retail 54.8, Airline 38.0 (high 추론). Airline은 medium 추론이 42.6으로 오히려 더 높습니다.
  - 일부를 CPU로 오프로드해야 합니다.
- **google/gemma-4-26B-A4B-it**
  - Tau2 68.2 (Google 자체), TAU3 59.0 (Qwen 측정).
  - 시스템 RAM 약 10GB가 필요합니다.
- **kakaocorp/kanana-2-1.3b-instruct**
  - 슬라이딩 윈도 하이브리드 구조로 32K에서 KV가 최대 72.7% 줄어듭니다.
  - KoMT 6.54, BFCL-v3 Live 69.64.
  - `custom_code`(kanana2_tiny)를 쓰기 때문에 Unsloth 학습과 GGUF 변환이 막힐 위험이 있습니다.

**제외**

| 모델 | 제외 이유 |
|---|---|
| EXAONE-4.0-1.2B | 비상업 라이선스 |
| HyperCLOVAX-SEED-Think-14B | Q4_K_M이 8.92GB라 들어가지 않음. 커스텀 도구 형식 |
| HyperCLOVAX-SEED-Omni-8B (2025-12-23) | 약 10.7B, GGUF 없음, llama.cpp 지원 미검증 |
| Ministral-3-14B / 8B | 14B는 들어가지 않고, 8B는 도구 점수가 공개되지 않음 |
| Nemotron-3-Nano-4B | 영어 전용 |
| Qwen3.8, EXAONE 4.5 (33B), K-EXAONE 2.0, A.X-K2, Solar-Open2 | 노트북 크기 모델이 없음 |
| Trida2.0-4B | 블록 디퓨전 연구용 체크포인트. 전용 SGLang 포크가 필요 |
| Qwen-Drive-1.0-4B, Qwen-AgentWorld-35B-A3B | 특정 도메인 전용 |
| Ternary Bonsai 2 27B (5.95GB) | PrismML 포크가 필요하고 LoRA 학습 대상이 아님 |
| Meta Llama | Llama 3.2 이후 소형 모델이 없음 |

---

## 4. RunPod에서의 학습 방법

### 4.1 방법과 RTX 3090 24GB 적합성 (추정치, 실측 아님)

| 방법 | 4B | 8~9B | 14B | 용도와 주의 |
|---|---|---|---|---|
| Full fine-tune | 불가 (약 34GB 이상) | 불가 | 불가 | 24GB에서는 약 2B 이하만 가능 |
| **bf16 LoRA** | 2k/4k/8k 모두 가능 (8k에서 약 13~17GB) | 약 22GB라 짧은 시퀀스만 가능하고 경계선. 32~48GB 카드 권장 | 불가 (약 30~33GB) | **Qwen3.5의 기본 방법** |
| QLoRA 4bit | 가능 | 가능 | Unsloth로 가능 | **Qwen3.5에는 비권장.** Unsloth가 "양자화 차이가 평소보다 크다"는 이유로 비권장합니다. 처리량은 약 0.7배입니다 |
| DPO/KTO/ORPO | SFT의 1.2~1.5배 VRAM | 같은 비율 | – | 연산량은 SFT의 2~3배 |
| GRPO | 24GB에서 Unsloth Standby 모드로 가능(추정) | 24GB에서는 불가 | – | 실행해서 확인할 수 있는 보상이 있을 때만 |

- Unsloth 수치는 unsloth.ai가 차단되어 검색 요약으로만 봤습니다. 교차 확인된 것은 "9B bf16 LoRA 22GB"와 "Qwen3.5는 QLoRA 비권장" 두 가지뿐이고, 4B 10GB와 Gemma 4 수치는 미검증입니다. **학습 전에 목표 max_length로 1스텝만 돌려(dry run) 실제 메모리를 확인하세요.**
- **숨은 메모리 비용**: 어휘 248,320개에 8k 토큰이면 fp32 logits만 약 8.14GB이고 그래디언트도 같은 크기입니다. chunked cross-entropy(TRL 기본값 `chunked_nll`)나 Unsloth의 fused CE가 필수입니다.
- Qwen3.5 학습에는 `flash-linear-attention`과 `causal_conv1d` 패키지가 필요합니다. 없으면 **경고 없이 느리고 메모리를 많이 쓰는 경로로** 돌아갑니다(https://huggingface.co/docs/transformers/model_doc/qwen3_5).
- 하이브리드 구조에서 시퀀스 패킹이 되는지는 미검증입니다(transformers 이슈 #46093이 열려 있음).

### 4.2 프레임워크 (PyPI 기준, 2026-09-24)

| 도구 | 버전 (날짜) | 장점 | 의존성 주의 |
|---|---|---|---|
| Unsloth | 2026.9.11 (2026-09-23) | 단일 GPU SFT, GRPO(vLLM Standby), GGUF 내보내기 내장 | 기본 설치 요구사항이 `torch<2.13`, `transformers<=5.5.0`, `trl<=0.24.0`입니다. 그래서 TRL 1.x의 도구 환경 기능을 쓸 수 없고, vLLM 0.30(torch==2.13)과 같은 venv에 둘 수 없습니다. unsloth-zoo 2026.9.7은 trl≤1.13을 허용해 둘의 핀이 서로 충돌합니다 |
| TRL | 1.13.0 (2026-09-10) | `tools` 컬럼 SFT, `assistant_only_loss`, `GRPOTrainer(tools=…)`, `environment_factory` | vllm extra가 `>=0.19.1,<=0.28.0`이라 vLLM 0.30은 지원 범위 밖입니다 |
| Axolotl | 0.19.0 (2026-09-10) | YAML 설정, 멀티 GPU, QAT, RunPod 템플릿 | `trl==1.9.0`, `transformers==5.16.1`, torch 2.11~2.13, Python 3.11 이상 |
| LLaMA-Factory | 0.9.5 (2026-05-30) | 코드 없이 쓰는 GUI(LlamaBoard) | 지원 목록에 Gemma 4가 없습니다(미검증) |
| torchtune | 0.6.1 (2025-04-07) | – | 2025-07에 개발 중단. **사용하지 마세요** |

**권장: venv를 분리하세요.**
- (a) Unsloth venv: SFT와 GGUF 내보내기용. Unsloth가 고정한 구버전 TRL과 transformers를 그대로 씁니다.
- (b) TRL 1.13 + vLLM ≤0.28 venv: 도구 환경 GRPO용. torch 2.13과 CUDA 13이 필요하고 드라이버 580.65.06 이상이어야 합니다[S].
- Unsloth를 `--no-deps`로 TRL 1.13과 함께 쓸 수 있는지는 미검증입니다.
- TRL의 `max_length` 기본값은 1024로 알려져 있지만 확인하지 못했습니다. 항상 명시적으로 지정하세요.

### 4.3 CUDA와 드라이버

- PyPI의 torch 2.14 휠은 CUDA 13 빌드입니다. CUDA 13에는 드라이버 580.65.06 이상이 필요합니다[S].
- 새 포드를 만들 때 `allowedCudaVersions: ["13.0"]`으로 필터하거나, 570 계열 호스트라면 cu128 휠을 쓰세요. 다만 torch 2.13/2.14에 cu128 휠이 있는지는 미검증입니다.
- 이전 포드는 드라이버 570.195.03 / CUDA 12.8이었고, cu13 torch가 "driver too old"로 실패한 기록이 있습니다(`SETUP_HISTORY.md`).

### 4.4 Community GPU 가격과 재고

- 가격 출처: https://www.runpod.io/pricing 의 JSON-LD(dateModified 2026-09-13)
- 재고 출처: 읽기 전용 GraphQL `gpuTypes` 조회(2026-09-24 04:05~04:17 UTC)
- **재고는 분 단위로 바뀝니다.** 포드를 만들기 직전에 다시 확인하세요.

| GPU | VRAM | Community $/hr | Community 재고 | 용도 |
|---|---|---|---|---|
| RTX A5000 | 24GB | 0.16 | 미확인 | – |
| **RTX 3090** | 24GB | **0.22** | Low | 4B LoRA, 데이터 생성 |
| **RTX 4090** | 24GB | **0.34** | Low | 4B LoRA (더 빠름) |
| RTX 5000 Ada | 32GB | 0.49 | Low | 9B bf16 LoRA (짧은 컨텍스트) |
| RTX 5090 | 32GB | 0.69 | Low | 9B bf16 LoRA |
| **L40** | 48GB | **0.69** | Low | 9B bf16 LoRA 4~8k, 9B GRPO, teacher 추론 |
| RTX 6000 Ada | 48GB | 0.74 | Low | L40과 같음 |
| L40S | 48GB | 0.79 | Low | L40과 같음 |
| RTX PRO 5000 | 48GB | 0.82 | Low | L40과 같음 |
| RTX A6000 | 48GB | 0.33 (목록가) | **재고 없음** | – |
| A40 / L4 | 48 / 24GB | 목록가 0.35 / 0.44 | **Community에서 제공하지 않음**(API의 `communityCloud=false`, Secure 전용) | **사용 금지** |
| A100 PCIe | 80GB | 1.19 | Low | GRPO |
| A100 SXM | 80GB | 1.39 | 04:05에는 Low, 04:09에는 없음 | – |
| H100 NVL | 94GB | 2.59 | Low | 빠른 실행 |
| H100 PCIe / SXM | 80GB | 1.99 / 2.69 | 없음 | – |
| H200 / RTX Pro 6000 | 141 / 96GB | 3.59 / 1.69 | 없음 (04:17) | – |

**스토리지**
- 컨테이너 디스크는 $0.10/GB/월이고, 포드를 정지하면 내용이 사라집니다.
- 볼륨(`/workspace`)은 실행 중 $0.10/GB/월, 정지 중 $0.20/GB/월입니다. terminate할 때까지 보존됩니다.
- network volume은 **Secure 전용**입니다(https://docs.runpod.io/storage/network-volumes).
- Global volume(베타, $0.09/GB/월 + 요청 요금)이 Community 포드에서도 되는지는 미검증입니다. 파일 잠금이 없는 객체 스토리지 기반이라 문서도 체크포인트 저장용으로는 맞지 않다고 적고 있습니다(https://docs.runpod.io/storage/globalvolume).
- 체크포인트는 **private HF repo**나 `runpodctl send/receive`로 옮기세요.

### 4.5 학습 시간과 비용 (추정, 실측 아님)

**계산 방법**
- 처리량(tok/s) = 유효 TFLOPS ÷ (6 × 파라미터 수 N)
- 유효 TFLOPS 가정: 3090 21, 4090 40, L40S 55, A100 100, H100 SXM 280
- 이 가정값은 기억에 의존한 스펙 피크에서 나온 것이라 미검증입니다. 조사 노트끼리도 차이가 납니다(3090 21 대 28, 4090 40 대 66, H100 280 대 400).
- L40, RTX 6000 Ada, RTX 5000 Ada, 5090은 처리량 가정이 없어 표에서 뺐습니다.

**데이터 예산**
- A: 1만 샘플 × 1.5k 토큰 × 2 에폭 = 3천만 토큰
- B: 5만 샘플 × 1.5k 토큰 × 2 에폭 = 1억 5천만 토큰
- 패킹을 못 하거나(Qwen3.5에서 가능성 있음) 중간 평가를 넣으면 **실제 시간은 약 2배**입니다.

**4B (N = 4.2B), bf16 LoRA**

| GPU ($/hr) | tok/s | 예산 A | 예산 B |
|---|---|---|---|
| 3090 (0.22) | 833 | 10h / $2.2 | 50h / $11 |
| 4090 (0.34) | 1,587 | 5.2h / $1.8 | 26h / $8.9 |
| L40S (0.79) | 2,183 | 3.8h / $3.0 | 19h / $15 |
| A100 PCIe (1.19) | 3,968 | 2.1h / $2.5 | 10.5h / $12.5 |
| H100 SXM (2.69, 재고 없음) | 11,111 | 0.75h / $2.0 | 3.75h / $10.1 |

**9B (N = 9.2B)**

| GPU ($/hr) | tok/s | 예산 A | 예산 B | 비고 |
|---|---|---|---|---|
| 3090 (0.22) | 380 | 22h / $4.8 | 110h / $24 | bf16 LoRA 약 22GB라 짧은 시퀀스만. Qwen3.5가 아닌 모델을 QLoRA(×0.7)로 돌리면 31h / $6.9, 157h / $34 |
| 4090 (0.34) | 725 | 11.5h / $3.9 | 58h / $19.6 | 24GB라 3090과 같은 제약 |
| L40S (0.79, 48GB) | 996 | 8.4h / $6.6 | 42h / $33 | 4~8k 시퀀스를 여유 있게 |
| A100 PCIe (1.19) | 1,812 | 4.6h / $5.5 | 23h / $27 | – |
| H100 SXM (2.69, 재고 없음) | 5,072 | 1.6h / $4.4 | 8.2h / $22 | H100 NVL($2.59)로 하면 비슷한 수준 |

- 토큰당 비용은 GPU끼리 2배 이내로 비슷합니다. 따라서 **모델이 메모리에 들어가는지와 기다릴 수 있는 시간으로 GPU를 고르세요.**
- 3~5회 반복하고 평가까지 포함한 프로젝트 전체 GPU 비용: **4B $10~60, 9B bf16 LoRA $20~100.**
- 이전 조사 노트의 A6000/A40 기반 수치는 해당 GPU를 Community에서 빌릴 수 없어 폐기했습니다. 그 수치는 실제보다 1.5~2.1배 낮게 잡혀 있었습니다.
- 교차 확인: 논문 https://huggingface.co/papers/2509.12229 는 RTX 4060에서 Qwen2.5-1.5B LoRA가 360~628 tok/s(MFU 약 20%)라고 보고했습니다. 위 가정과 모순되지 않습니다.

### 4.6 SFT 이후 강화학습 (선택, 추정)

| 방법 | 규모 | 비용 |
|---|---|---|
| DPO | 5천 쌍 × 1.5k 토큰 | 4B는 3090에서 $0.5~2. 9B는 48GB Community 카드에서 약 $4~13 |
| GRPO 4B | 500스텝 × 64 completion × 약 800 토큰 | 3090과 Unsloth로 **최소 25~30h, 약 $6~7**. TRL 1.13 도구 환경을 쓰려면 32~48GB 카드 필요 |
| GRPO 9B | 같음 | 24GB에서는 불가. 48GB Community 카드에서 약 $20~32. H100에서는 약 5h, $14 (재고 없음) |

- 오차 범위는 0.5배에서 3배까지 잡으세요.
- 보상은 실행해서 판정할 수 있어야 합니다: JSON 스키마 유효성, 함수명과 인자 일치, 샌드박스 작업 성공.
- 도구는 가능하면 목(mock)으로 대체하세요. 실제 도구를 부르면 대기 시간이 늘어납니다.

### 4.7 기존 3090 포드와 별도 임시 포드 비교

| 항목 | 보호 포드 `sydh2pm05u5rg2` | 별도 임시 Community 포드 |
|---|---|---|
| VRAM | Forge(SDXL 약 6.9GB)와 ComfyUI가 7~12GB를 쓰는 것으로 추정되어 12~16GB만 남습니다 | 24~48GB 전부 사용 |
| 프로세스 | Forge를 내려도 워치독(listener)이 다시 띄워 VRAM을 되가져가므로, 학습 도중 OOM이 날 수 있습니다 | 간섭 없음 |
| RAM | cgroup 한도 62GB. `listener/server.py`는 메모리 90% 이상이고 Forge가 유휴일 때 Forge를 재시작합니다. 9B를 fp32로 CPU 병합하면 약 38.6GB가 필요합니다 | 제약 없음 |
| 디스크 | 약 141GB 여유. 9B 파이프라인은 최대 90~110GB, 4B는 약 45GB를 씁니다 | 필요한 만큼 볼륨 할당 |
| 소프트웨어 | ComfyUI venv가 torch 2.5.1+cu121이고 드라이버는 미검증 | CUDA 버전을 필터로 선택 가능 |
| Drive 자동 백업 | `scripts/auto_backup_workspace.sh`가 30분마다 `/workspace` 최상위의 *.py/*.json/*.md/*.txt/*.ipynb/*.sh 파일과 `/workspace/scripts/`, `/workspace/logs/`를 `gdrive:런포드 백업/workspace_snapshot`으로 복사합니다. 학습 로그가 Drive로 올라갈 수 있습니다 | 해당 없음. rclone 설정을 이 포드로 복사하지 마세요 |
| 정지 규칙 | **절대 정지 금지** | 산출물을 올린 뒤 terminate 가능. 보호 대상이 아닙니다 |
| 결론 | **사용하지 마세요.** 굳이 쓴다면 사용자 승인을 받은 4B 소규모 PoC만, `/workspace/llm/` 아래에서 하세요 | **권장** |

**임시 포드 설정 요령**
- `cloudType=COMMUNITY`로 지정합니다.
- HF 토큰은 환경변수로만 넘깁니다.
- `push_to_hub`를 `hub_private_repo=True`, `hub_strategy="every_save"`로 설정해 저장할 때마다 체크포인트를 올립니다. Community 호스트는 사라질 수 있습니다.
- 작업 파일은 `/workspace`에 두세요. 컨테이너 디스크는 정지하면 사라집니다.
- 에이전트 스크립트에는 포드 ID 허용목록(allowlist)을 하드코딩하세요.

---

## 5. 데이터

### 5.1 공개 도구호출·에이전트 데이터 (영어 중심)

| 데이터셋 | 규모 | 라이선스 | 생성 모델 | 비고 |
|---|---|---|---|---|
| Salesforce/xlam-function-calling-60k | 60,000 | CC-BY-4.0 (동의 후 접근) | 앞의 33,659개는 DeepSeek-V2-Chat, 나머지는 Mixtral-8x22B | 600개 샘플 사람 검수에서 95% 이상 정확 |
| Team-ACE/ToolACE | 11.3K | Apache-2.0 | "frontier LLM" (구체 모델 미검증) | 영어·중국어 |
| NousResearch/hermes-function-calling-v1 | 11.6K | Apache-2.0 | 미검증 | Hermes 형식이라 Qwen3.5 XML 형식으로 다시 렌더링해야 합니다 |
| nvidia/When2Call | SFT 15K, 선호쌍 9K, 테스트 3,652 + 300 | CC-BY-4.0 | BFCL v2 Live와 APIGen 기반 합성 | 호출할지, 되물을지, 거절할지 판단을 학습. **BFCL과 겹치므로 평가 전에 중복 제거** |
| nvidia/Nemotron-Agentic-v1 | 335,122 | CC-BY-4.0 | Qwen3-235B, Qwen3-32B, GPT-OSS-120B | 상용 가능 |
| nvidia/Nemotron-SFT-Agentic-v2 | 991,900 (약 20GB) | CC-BY-4.0 + Apache/MIT | DeepSeek-V3.2, GLM-4.6 | 2026-08-10 갱신 |
| Agent-Ark/Toucan-1.5M | 약 1.53M (정제된 SFT 119,287) | Apache-2.0 | Qwen3-32B, Kimi-K2, GPT-OSS-120B | 실제 MCP 서버 495개에서 실행해 만든 데이터 |
| nvidia/Nemotron-RL-Agentic-*-Pivot-v1 | 각 1K~100K | CC-BY-4.0 | 전문가 궤적 | GRPO용 환경 |

**제외하거나 주의할 데이터**
- APIGen-MT-5k: 비상업(CC-BY-NC)이고 GPT-4o로 생성했습니다.
- glaive v2: 2023년 데이터이고 노이즈가 많습니다.
- SWE-smith, SWE-Gym: Claude나 GPT로 생성했습니다.
- hermes_reasoning_tool_use: Llama 3.1 계보이고 BFCL v3 카테고리에 맞춰져 있습니다.
- smoltalk2: 라이선스 태그가 없습니다(미검증).

### 5.2 한국어 도구호출 데이터

| 데이터셋 | 규모 | 라이선스 | 계보와 주의 |
|---|---|---|---|
| palette-lab/songgot-tools-ko (2026-09-11) | (요청, 호출) 336,602쌍, 스키마 183,737개, 60개 도메인 | Apache-2.0 | **공개된 한국어 데이터 중 최대 규모**지만 단일 호출만 있습니다. teacher는 Palette-K-Midm(MIT 라이선스 Midm-2.0에 QLoRA를 얹은 모델)인데, 이 QLoRA가 공개되지 않은 모델이 만든 397개 예제로 학습됐습니다. 그래서 계보는 대체로 깨끗하지만 기록해 둬야 합니다. teacher가 같은 호출을 다시 만들어 낸 행만 남겼는데, 전 필드가 일치한 비율은 57%입니다 |
| jungsanghyun/ko-agentic-toolcall (2026-08-10) | 11,931행 (89.2%가 멀티턴) | **라이선스 표기 없음**, 수동 승인 후 접근 | 라이선스가 명확해질 때까지 쓰지 마세요 |
| gyung/toolllama-korean-function-calling | 1,524 | Apache-2.0 표기 | ToolBench(gpt-3.5-turbo 생성)를 번역한 것이라 OpenAI 약관 계보입니다 |
| irene93/…, iamjoon/… | 3,260 / 388 | 태그 없음 | 출처 미상, 비권장 |

- **멀티턴 한국어 에이전트 데이터는 여전히 부족하고, 있는 것도 라이선스가 불명확합니다.** 직접 합성하는 방법(5.4절)을 전제로 계획하세요.

### 5.3 한국어 능력 유지용 일반 SFT 데이터

| 데이터셋 | 라이선스 | 주의 |
|---|---|---|
| CohereLabs/aya_dataset | Apache-2.0 | 사람이 직접 작성해 가장 깨끗합니다. 한국어 행 수는 미검증 |
| lemon-mint/smol-koreantalk | Apache-2.0 | 번역에 쓴 모델 미검증 |
| CarrotAI/ko-instruction-dataset | Apache-2.0 | WizardLM-2(Apache) 생성 |
| PoSTMEDIA/rosetta-ko-instruction-following-synth-* | Apache-2.0 (동의 후 접근) | 규칙으로 검증 가능한 지시 따르기 데이터 |
| nvidia/Nemotron-Personas-Korea | CC-BY-4.0 | 한국 사용자 시뮬레이터의 시드로 적합 |
| nlpai-lab/kullm-v2, kuotient/orca-math-ko | Apache 표기 / CC-BY-SA | ChatGPT·GPT-4 계보라 주의 |

### 5.4 합성 데이터와 teacher 선택

**참고할 파이프라인**
- APIGen: 형식 검사, 실제 실행, 의미 검사 순으로 거릅니다.
- APIGen-MT: 멀티턴 대화를 만들고 사용자를 시뮬레이션합니다.
- ToolACE, Toucan(실제 MCP 서버 사용), Nemotron(페르소나 기반).
- EDGE: 한국 공공 API를 실제로 호출해 성공한 연결만 남깁니다.
- ToolRL: 샘플 4천 개로 GRPO를 돌렸습니다.

**한국어 데이터 전략**
1. 기존 영어 데이터를 한국어로 바꿉니다. 사용자 발화와 최종 답만 한국어로 옮기고, 함수명과 JSON 인자는 그대로 둡니다.
2. 라이선스가 허용하는 teacher로 한국어 요청을 새로 생성합니다. Nemotron-Personas-Korea와 **사용자의 실제 도구 스키마**를 시드로 씁니다.
3. 생성된 호출을 실제 로컬 도구에서 실행해 보고, 실패한 것은 버립니다.

**출력을 학습에 써도 되는 teacher**

| 모델 | 라이선스 | 비고 |
|---|---|---|
| Qwen3.6-35B-A3B, Qwen3-235B-A22B-2507 | Apache-2.0 | 35B-A3B는 24GB 카드에 4bit로 올릴 수 있습니다 |
| gpt-oss-20b / 120b | Apache-2.0 | 3090(Ampere)에서 vLLM MXFP4가 동작하는지는 미검증 |
| DeepSeek-V3.2 / R1 | MIT | R1 카드는 "distillation for training other LLMs"를 명시적으로 허용합니다 |
| GLM-4.6 | MIT | – |
| K-intelligence Midm-2.0 | MIT | 한국어 |
| Kimi-K2 | 수정된 MIT | 월간 활성 사용자 1억 명 또는 월 매출 $20M을 넘을 때만 "Kimi K2" 표시 의무 |
| skt/A.X-K2, K-EXAONE-2.0-750B | Apache-2.0 | 약 692B와 749B라 직접 호스팅은 비현실적. 호스팅 API가 있는지는 미검증 |

- 생성 비용(추정): 궤적 1만 개 × 약 3k 토큰이면 3천만 토큰입니다. 24GB 카드에서 1~2K tok/s로 돌리면 4~8 GPU시간, 3090 가격 기준 약 $1~2입니다. 반드시 별도 포드에서 돌리세요.

### 5.5 약관과 라이선스 (학습에 다른 모델의 출력을 쓰는 경우)

| 출처 | 요지 | 확인 상태 |
|---|---|---|
| Anthropic Commercial Terms D.4 | "to build a competing product or service, including to train competing AI models"를 금지합니다. 출력물 권리는 고객에게 있지만 학습 금지는 그대로입니다 | 시행 2025-06-17, 원문 확인 |
| Anthropic Consumer Terms | 경쟁 AI 모델의 개발·학습을 금지합니다 | 시행 2025-10-08, 원문 확인 |
| OpenAI Terms of Use / Services Agreement | 출력으로 경쟁 모델을 개발하는 것을 금지합니다. 예외는 외부에 배포하지 않는 분류기·임베딩 모델뿐입니다 | [S], 시행일 미검증 |
| Gemini API Additional Terms | 경쟁 모델 개발을 금지합니다 | [S], 시행일 미검증 |
| DeepSeek Open Platform ToS | 증류 등 다른 모델 학습을 허용합니다 | [S]. R1 모델카드의 허용 문구는 원문 확인 |
| Llama 3 (2024-04-18) | 출력으로 Llama가 아닌 LLM을 개선하는 것을 금지합니다 | 원문 확인 |
| Llama 3.1 (2024-07-23) | 출력으로 학습한 모델을 배포하면 이름 앞에 "Llama"를 붙이고 "Built with Llama"를 표시해야 합니다 | 원문 확인 |
| Gemma ToU (2024-04-01, Gemma 1~3) | Gemma 합성 출력으로 학습한 모델도 Model Derivative로 봅니다. **Gemma 4는 Apache-2.0**입니다 | 이후 개정 여부 미검증 |
| Qwen Research License (예: Qwen2.5-3B) | 비상업 전용, "Built with Qwen" 표시 | 원문 확인 |
| EXAONE 1.2-NC | 모델과 출력 모두 상업 사용 금지, 경쟁 모델 개발 금지 | 원문 확인 |
| Kanana / HyperCLOVA X SEED | 출력으로 학습한 모델도 파생물로 봅니다. 배포하면 이름 접두어와 표시 의무가 생기고, 일정 규모 이상은 별도 라이선스가 필요합니다 | 원문 확인 |

**실무 규칙**
- 계보가 Apache-2.0, MIT, CC-BY 같은 허용형 라이선스인 teacher와 데이터만 씁니다.
- 데이터셋마다 출처 기록(provenance log)을 남깁니다.
- 개인 용도라도 GPT, Claude, Gemini, Llama-3.0, EXAONE, Qwen 연구용 라이선스 모델의 출력은 쓰지 않습니다. 약관은 API를 호출한 사람을 구속합니다.
- 학습 데이터를 거르는 보상 판정자로 GPT도 쓰지 않습니다.
- 이 내용은 법률 자문이 아닙니다.

**데이터 구성 팁**
- 도구 궤적 가운데 최소 10~30%는 사용자 발화와 최종 답변이 한국어여야 합니다.
- 일반 한국어 SFT 데이터를 20~50% 섞으세요. 이 비율은 경험칙이라 미검증입니다.
- 영어 SFT 세트에 다국어 예제를 40개만 넣어도 다국어 지시 따르기가 크게 좋아진다는 결과가 있습니다(https://huggingface.co/papers/2401.01854).
- 호출이 필요 없는 예제와 파라미터를 되물어야 하는 예제를 넣으세요(When2Call, Hammer의 7,500개).
- 함수명과 파라미터명을 마스킹하거나 바꿔서 이름에 과적합하지 않게 하세요.

---

## 6. 노트북 배포

### 6.1 파이프라인

1. **병합은 16bit로 합니다.**
   - Unsloth: `model.save_pretrained_merged("merged", tok, save_method="merged_16bit")`
   - PEFT: bf16 베이스를 불러와 `merge_and_unload()`
   - GPU에서 bf16으로 병합하세요. 9B를 fp32로 CPU 병합하면 RAM이 약 38.6GB 필요합니다.
2. **변환:** `python llama.cpp/convert_hf_to_gguf.py merged --outtype bf16 --outfile m-bf16.gguf`
3. **보정과 양자화:**
   - `llama-imatrix`를 한국어 텍스트와 도구호출 대화로 보정합니다.
   - `llama-quantize --imatrix imatrix.dat m-bf16.gguf m-Q4_K_M.gguf Q4_K_M`로 양자화합니다. Q5_K_M도 가능합니다.
   - 대안으로 Unsloth `save_pretrained_gguf`를 쓸 수 있습니다. 이 경우 포드에 cmake와 컴파일러가 필요합니다.
4. **어댑터만 배포하는 방법:**
   - 기본 GGUF는 그대로 두고 `convert_lora_to_gguf.py --base <base_hf> --outtype q8_0 <adapter_dir>`로 LoRA GGUF를 만듭니다.
   - `llama-server --lora`로 불러옵니다.
   - 업데이트할 때 수십 MB만 교체하면 됩니다(https://huggingface.co/blog/ngxson/gguf-my-lora).
   - Ollama 0.34.1 이상에서 `ADAPTER`로 불러오는 것이 되는지는 미검증입니다.
5. **Ollama를 쓸 경우:** GGUF는 llama.cpp 도구로 만든 뒤 `ollama create`로 가져오세요. Ollama 0.34.1 이상은 변환과 양자화를 하지 않습니다[S].

### 6.2 템플릿과 도구호출 함정 (가장 흔한 실패 지점)

- **(a) 학습과 추론에 같은 템플릿과 모드를 쓰세요.**
  - TRL의 Qwen3.5 학습용 템플릿은 항상 `<think>`를 출력합니다. 반면 공식 템플릿은 이전 턴의 `<think>`를 지웁니다.
  - 한 가지 모드를 정하세요(예: non-thinking, `enable_thinking=False`). 그리고 정확히 그 형식으로 학습하세요.
- **(b) Qwen3.5의 도구호출은 XML 형식입니다.**
  - 형식: `<tool_call><function=NAME><parameter=ARG>value</parameter></function></tool_call>`
  - Qwen3 방식인 Hermes형 JSON-in-`<tool_call>`로 학습하면 `qwen3_coder` 파서와 맞지 않습니다.
  - 데이터는 반드시 모델 자체 템플릿으로 렌더링하고, `arguments`는 JSON 문자열이 아닌 dict로 넣으세요.
- **(c) 병합한 폴더의 템플릿을 확인하세요.**
  - `chat_template.jinja`와 `tokenizer_config.json`이 베이스 모델과 같은지 봐야 합니다.
  - 학습용 `{% generation %}` 태그를 llama.cpp가 처리하는지는 미검증입니다. 변환 전에 베이스 템플릿으로 교체하세요.
- **(d) EOS 토큰은 `<|im_end|>`여야 합니다.** 틀리면 출력이 끝나지 않거나 깨집니다.
- **(e) llama.cpp는 `--jinja`로 실행하세요.** 서버 로그에 "Chat format: Generic"이 보이면 도구 형식을 인식하지 못한 것입니다. `--chat-template-file`로 지정하세요.
- **(f) Ollama는 Jinja 템플릿을 직접 쓰지 않습니다.** 내장 Go 템플릿 가운데 하나를 고르므로(https://huggingface.co/docs/hub/ollama), 커스텀 Qwen3.5 미세조정 모델의 도구호출이 되는지는 미검증입니다. **llama-server나 LM Studio가 더 안전한 대상입니다.**
- **(g) Gemma 4의 QAT 이점은 일반 미세조정을 하면 사라집니다.** Q5/Q6를 쓰거나 QAT 미세조정을 하세요.
- **(h) LoRA는 Qwen3.5의 MTP 헤드를 학습하지 않습니다.** 그래서 추측 디코딩 이득이 줄 수 있습니다(미검증).
- **(i) 사례:** Qwen3-Coder GGUF는 런타임마다 도구 템플릿이 다르게 깨졌습니다(https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/discussions/10). Songgot-X는 변환기가 존재하지 않는 25번째 MTP 블록을 만들어 2026-09-13 파일을 불러올 수 없었습니다.

**권장 설정**
- 실행: `llama-server -m m-Q4_K_M.gguf --jinja -c 16384 -ngl 99`
- KV 캐시는 q8_0. Songgot-X에서 f16 80.2 대 q8_0 81.0으로 손실이 없었습니다.
- non-thinking 샘플링: T=0.7, top_p=0.8, top_k=20, presence_penalty=1.5
- Ollama를 쓰면 `num_ctx`를 32k 이상으로 설정하세요.

**GGUF 점검**
- `gguf-dump`로 아키텍처, `tokenizer.chat_template`, EOS/BOS id를 확인합니다.
- `llama-perplexity --kl-divergence-base`로 bf16 대비 양자화 손상을 봅니다.
- **같은 도구 평가를 bf16(vLLM `--tool-call-parser qwen3_coder`)과 GGUF 양쪽에서 돌려 비교합니다.**

### 6.3 에이전트 클라이언트, 프레임워크, MCP

| 도구 | 버전 (날짜) | 4~9B 로컬 모델 적합도 |
|---|---|---|
| Pi (`@earendil-works/pi-coding-agent`) | 0.87.1 (2026-09-22) | 시스템 프롬프트가 약 2~3k 토큰이라 소형 모델에 가장 적합[S] |
| Qwen-Agent | 0.0.34 (2026-02-16) | Qwen3.5 모델카드가 MCP 예시와 함께 권장 |
| Hermes Agent (Nous) | 0.19.0 (2026-07-20) | llama.cpp나 Ollama에 연결하는 개인 에이전트 |
| OpenClaw | 2026.9.6 (2026-09-23) | 개인 에이전트 게이트웨이. OpenJarvis에서 9B로 교체 시 큰 폭의 하락이 측정됨 |
| Cline / OpenCode / Kilo Code | CLI 3.0.64 / 1.18.32 / 7.7.9 | Cline 문서: VRAM 16GB 미만에서는 8B를 "단일 파일 도우미"로 보고, Compact Prompt를 켜고 16~32k 컨텍스트를 쓰라고 권합니다. Q3/Q2 양자화는 도구호출을 깹니다[S] |
| LangGraph / Pydantic-AI / smolagents | 1.2.12 / 2.49.0 / 1.26.0 | **코드가 흐름을 쥐고 모델은 빈칸만 채우는 구조**가 자유로운 ReAct 루프보다 안정적입니다 |
| Claude Code / Codex CLI / OpenHands | 2.1.281 / 0.156.1 / 1.11.0 | 하네스가 무거워 8GB 소형 모델에는 부적합합니다. OpenHands는 Qwen3.6-35B-A3B를 권장합니다[S] |
| Continue | 최종 v2.0.0 (2026-06-19) | 2026-06에 Cursor가 인수해 저장소가 읽기 전용입니다[S]. 새로 쓰지 마세요 |

**MCP 호스트**
- LM Studio: 0.3.17부터 지원
- llama.cpp 웹 UI: `--webui-mcp-proxy` 옵션[S]
- Ollama: 브리지가 필요합니다(`mcp-client-for-ollama` 0.35.0)

**형식 보장**
- 도구호출 형식을 지키려면 제약 디코딩을 쓰세요: llama.cpp GBNF/JSON-schema, Ollama `format`, LM Studio structured output.

### 6.4 로컬 소형 모델이 현실적으로 할 수 있는 일 (판단, 실측 아님)

| 수준 | 작업 |
|---|---|
| **4~9B Q4로 안정적. 미세조정 효과가 가장 큼** | 도구 10개 이하, 스키마가 고정된 단일 또는 짧은(3~5단계 이하) 호출. 의도 라우팅, JSON 추출·분류, 로컬 파일 RAG, 한국어 요약·번역, 사람 승인을 거치는 단일 MCP 동작 |
| 경계선. 엔지니어링이 필요 | 5~15단계 ReAct 루프, 여러 파일 코드 수정, 웹 리서치, 32k 이상 장기 세션 |
| API 모델이나 27~35B급 로컬 모델이 필요 | 저장소 단위 자율 코딩, GAIA 수준의 개방형 리서치, 장기 계획. Qwen3.5-9B의 DeepPlanning 점수는 18.0에 불과합니다 |

- 현실적인 절충은 **하이브리드**입니다. 로컬 모델이 라우팅, 추출, 개인 데이터 처리를 맡고 계획은 API 모델에 맡깁니다.

---

## 7. 평가 방법

### 7.1 평가 층위

| 층 | 도구 | 실행 위치 | 측정 대상 | 주의 |
|---|---|---|---|---|
| 1. BFCL | `bfcl-eval` 2026.3.23. `bfcl generate --backend vllm --enable-lora …` 후 `bfcl evaluate` | RunPod | 표준 AST 채점이라 재현성이 가장 좋음 | 커스텀 모델은 핸들러를 등록해야 합니다. GGUF 엔드포인트로 되는지는 미검증. V4 웹검색 항목에는 SerpAPI 키가 필요합니다. 카테고리 가중치는 [S] |
| 2. When2Call | log-prob 객관식 3,652 + LLM 판정 300 | RunPod | 과잉 호출과 환각 | BFCL과 겹침 |
| 3. τ-bench / τ² / τ³ | LLM 사용자 시뮬레이터 필요 | RunPod | 다단계 작업 | 시뮬레이터 비용이 들고, 로컬 시뮬레이터로 바꾸면 점수를 비교할 수 없습니다. 소형 모델은 결과가 들쭉날쭉하므로 **5회 이상 돌려 pass^k로 보고**하세요 |
| 4. 한국어 도구 | FunctionChat-Bench 700문항(SingleCall 500, Dialog 200). KOPA-Bench(145과제, 데이터 공개 여부 미검증) | RunPod | 한국어 도구 대화 | FunctionChat 판정 모델은 GPT-4라는 [S] 정보만 있어 OpenAI 키가 필요할 수 있습니다. **판정 출력은 평가에만 쓰고 학습 데이터로 쓰지 마세요** |
| 5. 한국어 일반 | `lm-eval` 0.4.13: KMMLU(CC-BY-ND), HAE-RAE 1.1(CC-BY-NC-ND), KoBEST. KoMT-Bench | RunPod | 한국어 능력이 유지되는지 | – |
| 6. 언어 충실도 | 한국어 질문에 한국어로 답한 비율(Language Confusion Benchmark 방식) | 양쪽 | 코드스위칭 | – |
| 7. **커스텀 스위트** | 200~500개 과제, 결정론적 채점 | RunPod(bf16)과 **노트북(최종 GGUF)** | 실제 목적 달성 | 가장 중요합니다 |
| 8. 노트북 성능 | `llama-bench -d 0,16384,32768`, nvidia-smi | 노트북 | 속도와 VRAM | – |

### 7.2 커스텀 스위트 설계

- **과제 원천:** 사용자가 실제로 쓰는 도구(파일, 일정, 셸, RunPod/ComfyUI 조회 등).
- **과제 유형:**
  - 단일 호출
  - 병렬 호출
  - 다단계 연쇄
  - 파라미터가 부족해 되물어야 하는 경우
  - 관련 없는 요청이라 거절해야 하는 경우
  - 한국어와 영어 각각
- **채점:** 호출과 인자를 AST로 정확히 비교하거나, τ-bench처럼 샌드박스 상태 차이로 판정합니다.
- **보고 지표:** pass@1, pass^k(k=3~5), 잘못된 도구를 부른 비율.
- **보류 도구:** 학습에 쓰지 않은 도구를 따로 남겨 두고 일반화를 측정합니다.
- **실행 대상 세 가지:**
  - (a) 베이스 모델
  - (b) RunPod의 bf16 LoRA
  - (c) 노트북의 Q4/Q5 GGUF. 실제 운영과 같은 템플릿과 파서로 돌립니다.
- **합격 기준(제안):** GGUF의 점수 하락이 bf16 대비 2~3점 이내. Songgot-X는 양자화로 약 2점이 떨어졌습니다.
- **오염 제거:** When2Call은 BFCL v2 Live, hermes_reasoning은 BFCL v3, APIGen-MT는 τ-bench 도메인과 겹칩니다. 도구명과 질의가 겹치는 항목을 제거하세요.
- **첫 할 일:** Qwen3.5-4B와 9B, Gemma 4 E4B, Kanana-2-3B의 한국어 점수는 공개된 것이 없습니다. RunPod에서 먼저 기준점부터 측정하세요.

### 7.3 미세조정의 알려진 부작용 (평가로 반드시 확인할 것)

| 연구 | 관찰 |
|---|---|
| ToolRL (https://huggingface.co/papers/2504.13958) | SFT를 400개로 하면 7B의 irrelevance 탐지가 62.66에서 8.11로 붕괴. 7B를 SFT 4k개로 학습하면 36.53으로 원본(41.97)보다 낮아짐. GRPO는 3B를 33.04에서 52.98로 올림 |
| Toucan (https://huggingface.co/papers/2510.01179) | 7B BFCL은 55.10에서 58.26으로 올랐지만 non-live AST는 84.19에서 78.52로, relevance는 72.22에서 66.67로 떨어짐. 14B relevance도 83.33에서 72.22로 하락. τ² telecom은 16.70에서 10.50으로 하락 |
| When2Call (https://huggingface.co/papers/2504.18851) | When2Call을 SFT에 추가하니 4B의 BFCL Live AST가 6.2% 떨어짐 |
| Hammer (https://huggingface.co/papers/2410.04587) | 호출 정확도와 irrelevance 탐지가 서로 상충. 음성 예제 7,500개와 함수명 마스킹으로 완화 |
| DiaTool-DPO (https://huggingface.co/papers/2504.02882) | SFT만 한 모델보다 slot filling이 **상대적으로** 44%, 거절이 9.6% 개선되어 GPT-4o 대비 94.8%와 91.3% 수준에 도달. 베이스 모델에 따라 relevance가 10% 떨어진 경우도 있음 |
| OpenAgent (https://huggingface.co/papers/2607.01084) | 질의, 도구, 도메인이 바뀌면 SFT 모델과 RL 모델 모두 성능이 떨어짐 |

---

## 8. 처음부터 사전학습하는 경우

**계산 전제**
- 필요 연산량(FLOPs) ≈ 6 × N(파라미터 수) × D(토큰 수)
- 유효 처리량 가정(MFU 약 40%): H100 400, 4090 66, 3090 28 TFLOPS
- 3090의 28은 BF16 텐서 피크 71 TFLOPS([S] GA102 백서)의 40%입니다. 소비자 GPU에는 낙관적인 가정입니다.
- 가격은 Community 목록가입니다. H100 SXM은 현재 재고가 없고 H100 NVL($2.59)로 해도 비슷합니다.

| 모델 / 토큰 | FLOPs | H100 GPU시간 ($) | 4090 GPU시간 ($) | 3090 GPU시간 ($) |
|---|---|---|---|---|
| 0.5B / 10B (Chinchilla 20배) | 3.0e19 | 21 ($56) | 126 ($43) | 298 ($65) |
| 1B / 20B | 1.2e20 | 83 ($224) | 505 ($172), 약 21일 | 1,190 ($262), 약 50일 |
| 3B / 60B | 1.1e21 | 750 ($2.0K) | 4,545 ($1.5K) | 10,714 ($2.4K), **약 440일**. AdamW 혼합정밀도에 파라미터당 약 18B가 필요해 약 54GB이므로 24GB에 들어가지 않음 |
| 1B / 4T (현대식) | 2.4e22 | 16,667 ($45K) | 101,010 ($34K) | – |
| 3B / 11.2T (SmolLM3 수준) | 2.0e23 | 140K ($377K) | – | – |
| 2.69B / 34T (LFM2.5-2.6B 수준) | 5.5e23 | – | – | **약 610 GPU년** |

**실제 기준점**
- nanochat d20: 561M 파라미터, 11.2B 토큰, 8×H100 약 3~4시간, **약 $100**. MMLU 약 24~31%, GSM8K 약 4.5% (https://huggingface.co/sdobson/nanochat)
- nanochat d32: 1.9B, 약 $800. CORE 0.31로 GPT-2(0.26)보다 조금 높음 (Karpathy, 2025-10)
- **Songgot(한국어, 처음부터 학습):** 50M~303M 파라미터를 12B 토큰으로 학습했더니 FunctionChat SingleCall 29~33%. 미세조정한 Qwen3.5-0.8B(82.2)의 절반에도 못 미쳤습니다(https://huggingface.co/palette-lab/songgot-l). 프로젝트 자체의 관대한 exact-match 채점 기준입니다.
- Puro-2B (https://huggingface.co/api/papers/2608.27370, 2026-08-27)
  - $6.9K 미만으로 Qwen2.5-1.5B에 근접했고, 약 $4.4K면 Qwen2-1.5B 수준이라고 합니다.
  - 22,514 GPU시간, 17.6일이라는 수치는 초록에 없어 미검증입니다. RunPod 5090 가격으로 환산하면 약 $15.5K입니다.
- TinyLlama 1.1B: 3T 토큰, A100-40G 16장으로 90일(계획치) = 34,560 A100시간. Community A100 SXM 40GB $1.00 기준 약 $34.6K
- SmolLM3-3B: 11.2T 토큰, H100 384장으로 24일 ≈ 221K H100시간, 약 $440K~595K (https://huggingface.co/blog/smollm3, 2025-07-08). 한국어를 지원하지 않습니다.
- Qwen3: 36T 토큰. 소형 모델은 대형 모델에서 증류했습니다(https://huggingface.co/papers/2505.09388). 4B 기준 약 8.6e23 FLOPs, 약 600K H100시간, 약 $1.6M입니다.
- 한국어 데이터: FineWeb-2 kor_Hang은 48.6B **단어**, 60.9M 문서, 213GB입니다. 토큰으로 환산한 값은 미검증이며 수백억 토큰 규모로 봅니다.

**결론: 처음부터 사전학습하는 것은 현실적이지 않습니다.**
- 연산 격차가 수천~수백만 배입니다. Qwen3-0.6B만 해도 약 1.3e23 FLOPs를 썼습니다.
- 데이터 정제와 증류 파이프라인이 없습니다.
- Qwen3.5는 "수백만 개 에이전트 환경"으로 강화학습을 했습니다.
- 처음부터 학습하더라도 결국 도구호출 미세조정을 똑같이 다시 해야 합니다.
- **처음부터 만든 모델이 Qwen3.5-2B/4B를 이길 확률은 사실상 0**입니다. 의미가 있는 것은 약 $100짜리 nanochat 같은 학습 경험용 교육 과제뿐입니다.

---

## 9. 현실적인 프로젝트 안

### 9.1 근거 사례 (8B 이하 또는 로컬 실행)

| 사례 | 방법과 데이터 | 결과 | 주의 |
|---|---|---|---|
| Gitara (distil labs, 2025-12 카드) | Llama-3.2-3B/1B에 LoRA SFT. teacher는 GPT-OSS-120B, seed 약 100개를 1만 개로 확장, git 명령 13개 | 3B: 0.12 → 0.92 (teacher와 동일), 1B: 0.00 → 0.90 (테스트 50개) | 단일 턴만. Llama 3.2 라이선스 |
| Home-LLM (개인, acon96) | RTX 3090 한 장으로 LoRA r=64. 합성 데이터 1만~10만 행 | 자체 테스트셋에서 JSON 함수호출 97.11% | StableLM 기반은 비상업 라이선스 |
| **Songgot-X 0.8B (한국어, 2026-09-16)** | Qwen3.5-0.8B에 SFT 3회 후 가중치 평균. 한국어 도구호출 263K행 사용 | FunctionChat SingleCall 45.2 → 82.2. Kanana-2-1.3B는 73.2, EXAONE-4.0-1.2B는 63.0. Q4_K_M 양자화로 약 2점 손실 | 자체 채점. MASSIVE 결과는 MASSIVE train을 학습했으므로 공정한 비교가 아닙니다. Kanana 점수는 같은 분포일 수 있습니다 |
| Jan-nano (2025-06) | Qwen3-4B에 RLVR | SimpleQA(MCP 사용) 83.2% | 베이스 59.2%와 DeepSeek-V3 78.2%는 미검증. 평가 프로토콜을 검증할 수 없다는 비판이 있습니다 |
| KOPA/EDGE (한국어, 2026-09) | Qwen3.5-9B에 GRPO. 실행으로 검증한 과제 1,781개 | [S] 9B pass@1 0.3275 → 0.4310. 미학습 27B는 0.4482로 차이 1.7점 | 논문 원문 미열람. BFCL +4.0/+5.9와 50.2%는 미확인 |
| DualTune (2025-09) | Qwen2.5-7B에 도구 선택용과 인자 생성용 LoRA를 분리 | MCP-Bench 정확도 **상대** 46% 향상 | – |
| ART·E (OpenPipe, 2025-04) | Qwen2.5-14B에 GRPO | [2차 출처] o3보다 정확. H100 한 장, 약 $80 | 데이터 생성과 판정에 GPT-4.1을 썼다는 2차 출처가 있어 **라이선스상 깨끗한 레시피가 아닙니다** |
| TinyAgent (2024-09) | 1.1B/7B에 LoRA. 8만 개 데이터, 데이터 비용 약 $500 | 1.1B: 12.71% → 78.89% | GPT-4-Turbo로 만든 데이터라 약관 문제가 있습니다 |

**공통 패턴**
- 성공한 사례는 모두 도구 5~15개 수준의 **좁은 과제**입니다.
- 데이터는 1천~1만 개 이상이고, 실행이나 규칙으로 검증했습니다.
- 베이스 모델의 zero-shot 성능이 낮을수록 개선 폭이 컸습니다.

**반대 근거**
- OpenJarvis: 범용 스택에서 로컬 9B는 −25~39%p였습니다.
- 학습 없이 도구 이름과 스키마를 모델에게 익숙한 형태로 바꾸기만 해도 최대 +17%, 스키마 불일치 오류 −80%였습니다(PA-Tool, ACL 2026, [S]).

**방법 비교 연구** (https://arxiv.org/abs/2609.17848, [S] 미검증)
- 같은 분포 과제에서는 SFT-LoRA가 18개 설정 중 15개에서 가장 좋았습니다.
- 다른 분포로 옮겼을 때는 GRPO가 54개 중 29개에서 이겼지만 차이는 1점 미만이었습니다.

### 9.2 세 가지 안 (+ 비권장 D)

| 안 | 내용 | 예산 | 기간 | 성공 확률 (추정) | 권장 |
|---|---|---|---|---|---|
| **A. 학습 없음** | 노트북에서 Qwen3.5-9B Q4_K_M(16k)이나 4B Q8_0을 non-thinking 모드로 돌립니다. Qwen-Agent나 MCP, 제약 디코딩을 쓰고 도구는 10개 이하로 둡니다. 도구 이름을 친숙하게 바꾸고 한국어 few-shot을 넣습니다. **실사용 명령으로 평가셋 100~200개**를 만듭니다 | GPU $0. 한국어 기준점 측정용 임시 포드는 선택이며 수 달러 | 3~7일 | 좁은 도구와 사람 확인 조건이면 80~90%. 자율 다단계는 약 50%. 범용 비서는 낮음 | **1순위** |
| **B. LoRA 특화** | A의 평가셋에서 모자란 부분을 대상으로 합니다. seed 50~150개를 한국어로 직접 쓰고, **허용형 오픈 teacher**로 2천~1만 개로 늘립니다. 호출 불필요 예제, 방해 도구, 실행 검증을 넣습니다. Qwen3.5-4B를 bf16 LoRA로 학습(4090 $0.34, 회당 1~3시간)합니다. 9B는 5090/L40급에서 회당 2~6시간입니다. 이후 GGUF로 만들고 재검증합니다 | 총 $30~150 (GPU 4B $10~60, 9B $20~100, teacher 추론 $10~50) | 파트타임 2~4주 | 보류한 실사용 셋에서 A 대비 +10%p 이상일 확률 65~80%. A가 이미 90% 이상이면 이득이 작습니다 | A가 부족할 때 |
| **C. 증류 + GRPO** | B의 체크포인트에서 시작해 샌드박스 보상으로 GRPO를 돌립니다. RunPod API는 목으로, ComfyUI는 녹화한 응답으로 대체합니다. 실제로 실행에 성공한 궤적만 남깁니다. 도구는 TRL 1.13, Unsloth, ART, verl | $100~400 (4B는 A100 PCIe $1.19 등에서 회당 10~30시간, 3~6회) | 1~3개월 | B보다 의미 있게 좋아질 확률 30~50% | 선택 |
| D. 처음부터 사전학습 | – | 장난감 모델 $50~800. 쓸 만한 수준은 $4K~15K 이상인데도 2024년 1.5B 수준 | 수주~수개월 | 약 0% | **비권장** |

**B안 teacher 규칙**
- 프런티어 API(GPT, Claude, Gemini)는 쓰지 않습니다.
- Qwen3.6-35B-A3B, Qwen3-235B-A22B-2507, gpt-oss-120b, DeepSeek-V3.2, Midm-2.0 같은 Apache/MIT 모델을 씁니다.
- teacher는 48GB Community 카드(L40 $0.69, RTX 6000 Ada $0.74, L40S $0.79)나 24GB 카드에 4bit MoE로 올려 돌립니다.

**C안 위험**
- 보상 해킹. OpenPipe 모델이 약 1,200스텝에서 모든 기사에 같은 제목을 생성한 사례가 있습니다.
- 환경을 만드는 부담이 큽니다.
- 분포가 바뀌면 성능이 떨어집니다.

### 9.3 운영 안전장치 (모든 안에 필수)

1. 학습은 **별도의 임시 Community 포드**에서만 하고 끝나면 그 포드만 terminate합니다. 스크립트에는 포드 ID 허용목록을 하드코딩합니다. `sydh2pm05u5rg2`는 대상에서 빼고, 정지, 재시작, 프로세스 종료, 대용량 작업을 모두 금지합니다.
2. 에이전트 도구 계층에서 다음을 차단하거나 사람 확인을 필수로 합니다.
   - RunPod의 stop/terminate 계열 API
   - `scripts/restart_forge_clean.sh` (`pkill -9` 사용)
   - `scripts/jupyter_exec.py` (원격 코드 실행)
   - `scripts/submit_job.py` 같은 쓰기 도구
   - 에이전트 도구는 `scripts/runpod_pod_status.py`, `scripts/verify_lora_integrity.py`, `chibi/comfy_client.py`의 큐 조회 같은 **읽기 전용 도구부터** 시작합니다.
3. Google Drive에 쓰는 도구(`scripts/finish_project.py` 등)는 **4팀 공유 드라이브를 대상에서 하드 차단**합니다. 학습 산출물은 Drive에 올리지 않습니다.
4. 토큰(HF, RunPod)은 환경변수로만 넘기고 로그와 커밋에 남기지 않습니다.
5. 모델 출력은 항상 스키마로 검증하고, 위험한 동작에는 사람 승인을 받습니다. 모델은 환각을 일으키므로 안전장치를 모델에 맡기지 않습니다.

### 9.4 권장

- **A안부터 시작하세요.** 평가셋이 있어야 B안이 필요한지, 효과가 있었는지 판단할 수 있습니다.
- B안이 필요하면 **Qwen3.5-4B + bf16 LoRA + RTX 4090 임시 포드**가 비용, 위험, 노트북 여유 사이의 균형이 가장 좋습니다.
- 9B는 A안의 추론용으로 쓰거나, 4B 결과가 모자랄 때 32~48GB 카드로 학습하세요.

---

## 10. 사용자 결정 사항 / 다음 단계

### 10.1 결정이 필요한 것

1. **노트북 정확한 사양**
   - 확인할 것: GPU 모델명(5050/5060/5070), TGP, 시스템 RAM(16GB인지 32GB인지), OS
   - 확인 방법: `nvidia-smi`, 작업 관리자
   - 이것으로 9B를 쓸지 4B를 쓸지, MoE 오프로드가 가능한지가 정해집니다.
2. **에이전트 용도와 도구 목록.** 예: RunPod/ComfyUI 자동화, 로컬 파일, 일정. A안과 B안의 범위가 여기서 정해집니다.
3. **개인 용도인지 배포·상용인지.** Kanana, LFM, Llama 계열의 라이선스 의무가 달라집니다.
4. **예산 상한과 기간.** 예: B안 $150, 한 달.
5. **데이터 정책.** 허용형 오픈 teacher만 쓰고 GPT/Claude/Gemini 출력은 쓰지 않는다는 데 동의하는지.
6. **운용 방식.** 한국어와 영어 비중, thinking을 쓸지 여부.

### 10.2 승인 게이트

| 게이트 | 내용 | 비용과 영향 | 필요한 승인 |
|---|---|---|---|
| G1 | 노트북에 런타임(LM Studio나 llama.cpp)을 설치하고 GGUF를 다운로드. 예: Qwen3.5-4B Q8_0 4.48GB, 9B Q4_K_M 5.68GB | 무료, 디스크 사용 | 사용자 |
| G2 | **임시 Community 포드 생성.** GPU 종류, 최대 시간, 비용 상한, terminate 시점을 명시 | 예: 4090 $0.34 × 10h ≈ $3.4. 볼륨 요금 별도 | **사용자 명시 승인** |
| G3 | 포드에 베이스 가중치와 데이터셋 다운로드. 4B bf16 약 9.3GB, 9B 약 19.3GB | 디스크, 시간 | 사용자 |
| G4 | HF private repo를 만들고 토큰을 사용. 토큰은 환경변수로만 | – | 사용자 |
| G5 | teacher로 합성 데이터 생성. 라이선스와 출처 기록 확인 | $10~50 | 사용자 |
| G6 | 보호 포드 `sydh2pm05u5rg2`: **사용하지 않고 변경하지 않음** | – | 변경 없음 |
| G7 | Google Drive: 학습 산출물을 업로드하지 않음. 4팀 공유 드라이브는 어떤 경우에도 대상이 아니며, 필요하면 CLAUDE.md의 별도 승인 절차를 따름 | – | – |

### 10.3 첫 주 할 일 (A안)

1. 노트북 사양을 확인합니다.
2. LM Studio나 llama-server를 설치하고 두 모델을 올립니다.
   - 모델: Qwen3.5-4B Q8_0과 9B Q4_K_M
   - 설정: `--jinja`, 16k 컨텍스트, q8_0 KV, non-thinking
   - Windows라면 Sysmem Fallback을 끕니다.
3. 도구 5~10개를 MCP나 Qwen-Agent로 감쌉니다. 읽기 전용 도구부터 시작합니다.
4. 실사용 명령 100~200개로 평가셋을 만듭니다. 한국어 발화, 호출이 필요 없는 경우, 파라미터가 빠진 경우를 넣습니다.
5. 평가셋으로 측정한 뒤, 실패 유형을 보고 B안으로 갈지 정합니다.

---

## 11. 리스크와 미검증 항목

### 11.1 리스크

| 리스크 | 영향 | 완화 |
|---|---|---|
| GGUF 변환 후 템플릿과 파서가 맞지 않음 | 도구호출이 조용히 실패 | 모델 자체 템플릿으로 렌더링, gguf-dump로 확인, `--jinja` 로그 확인, GGUF에서 같은 평가를 다시 실행 |
| 한국어 품질 저하와 코드스위칭 | 사용성 하락 | 한국어 비율 10~30% 이상, 일반 한국어 SFT 혼합, 언어 충실도 측정 |
| 과잉 호출과 irrelevance 탐지 붕괴 | 불필요한 도구 실행 | When2Call과 Hammer식 음성 예제, DPO |
| 형식과 함수명 과적합 | 새 도구에서 실패 | 함수명 마스킹, 보류 도구로 평가 |
| 양자화 손실 | 약 2점 (Songgot-X) | 한국어와 도구 대화로 imatrix 보정, Q5, KL-divergence 확인 |
| VRAM 초과 | Windows 공유 메모리로 5~10배 느려짐 | Sysmem Fallback 끄기, 16k 컨텍스트, q8 KV |
| 학습 프레임워크 의존성 충돌 | 환경 구축 실패 | venv 분리(4.2절) |
| Community 재고 변동과 호스트 소멸 | 작업 중단 | 생성 직전 재고 확인, HF에 체크포인트 저장 |
| 약관과 라이선스 위반 | 법적 위험 | 허용형 계보만 사용, provenance log |
| 보호 포드나 Drive 사고 | 복구 불가 (RTX 3090 매물 없음) | 별도 포드, allowlist, 학습 파일은 `/workspace/llm/`, Drive 쓰기 차단 |
| RL 보상 해킹 | 엉뚱한 행동 학습 | 롤아웃을 직접 확인, 보상을 다중화 |
| 제작사 벤치마크 과대평가 | 기대치가 틀림 | 직접 측정. TAU2 79는 수정된 하네스 기준 |
| 노트북 발열과 TGP 편차 | 성능 편차 50~60% [S] | 전원 연결, 성능 모드에서 실측 |

### 11.2 미검증 항목

- **하드웨어와 인프라**
  - 노트북 GPU 모델, TGP, RAM, OS, 실측 tok/s
  - 런타임 오버헤드 0.3~1.0 GiB
  - 보호 포드의 현재 상태, 드라이버, 여유 VRAM (프록시가 404 반환)
  - 현 드라이버에서 torch 2.13/2.14용 cu128 휠이 있는지
  - Global volume을 Community 포드에서 쓸 수 있는지
  - Community 재고 (분 단위로 변동)
- **모델 성능과 호환성**
  - Qwen3.5-4B/9B, Gemma 4 E4B/12B의 한국어 점수 (KMMLU, KoMT, FunctionChat, Ko-AgentBench)
  - Qwen3.5의 non-thinking 모드 도구 점수
  - llama.cpp가 Qwen3.5 XML, Gemma 4 네이티브 토큰, LFM 형식의 도구호출을 제대로 파싱하는지
  - llama.cpp가 Gemma 4의 KV 공유를 어떻게 구현하는지
  - Ollama 라이브러리의 `qwen3.5:9b`와 `gemma4:e4b` 도구 지원 (ollama.com 접근 차단)
  - Ollama에서 커스텀 Qwen3.5 미세조정 모델의 도구호출이 되는지, 0.34.1 이상에서 `ADAPTER`로 불러오는지
  - Ollama 관련 이슈(#18581, #18232)와 llama.cpp 이슈 #26674의 현재 상태
  - gpt-oss-20b MXFP4가 3090 vLLM에서 도는지
  - NVFP4의 실제 크기 절감 폭
  - Gemma 4 E4B와 12B의 공개 출시일 (각각 2026-04-02와 2026-06-03이라는 [S] 정보만 있음)
- **학습**
  - Unsloth VRAM 수치: 9B 22GB와 Qwen3.5 QLoRA 비권장만 교차 확인됐고, 4B 10GB, Gemma 4 수치, requirements 표는 미검증
  - 학습 처리량 가정(스펙 피크를 기억으로 적었고 노트끼리 불일치). L40, 6000 Ada, 5000 Ada, 5090의 처리량
  - Qwen3.5 시퀀스 패킹
  - llama.cpp의 `{% generation %}` 태그 처리
  - LoRA 이후 MTP 추측 디코딩에 미치는 영향
  - LLaMA-Factory의 Gemma 4 지원
  - Unsloth와 TRL 1.13을 `--no-deps`로 함께 쓸 수 있는지
  - TRL `max_length` 기본값
- **데이터, 평가, 약관**
  - FunctionChat-Bench의 판정 모델
  - KOPA-Bench 데이터 공개 여부와 세부 수치
  - arXiv 2609.17848 수치
  - BFCL V4 카테고리 가중치
  - ToolACE, glaive, Hermes의 생성 모델
  - smoltalk2 라이선스, Aya 데이터의 한국어 행 수
  - OpenAI, Gemini, DeepSeek 약관의 시행일
  - Gemma ToU가 이후 개정됐는지
- **사례와 사전학습 수치**
  - ART·E 수치 (2차 출처만)
  - Jan-nano 베이스 점수
  - Puro-2B의 GPU시간
  - 한국어 단어를 토큰으로 바꾼 환산값
  - 3090 BF16 71 TFLOPS (백서 [S])

---

## 12. 출처

- 조회일은 모두 2026-09-24입니다. 게시일이나 시행일을 알면 함께 적었습니다.
- 차단되어 열지 못한 사이트: ollama.com, lmstudio.ai, unsloth.ai, arxiv.org, openai.com, ai.google.dev, nvidia.com, reddit, gorilla.cs.berkeley.edu 등. 이 사이트에 근거한 내용은 [S]로 표시했습니다.

**RunPod**
- https://www.runpod.io/pricing (JSON-LD dateModified 2026-09-13, HTTP last-modified 2026-09-23)
- https://api.runpod.io/graphql (`gpuTypes`, 읽기 전용, 2026-09-24 04:05~04:17 UTC)
- https://docs.runpod.io/storage/network-volumes
- https://docs.runpod.io/storage/globalvolume (2026-09-18 수정)
- https://docs.runpod.io/pods/storage/types
- https://docs.runpod.io/api-reference/pods/POST/pods

**모델카드, config, 라이선스 (HF)**
- https://huggingface.co/Qwen/Qwen3.5-9B (2026-02-27)
- https://huggingface.co/Qwen/Qwen3.5-4B (2026-02-27)
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B (2026-04-15)
- https://huggingface.co/google/gemma-4-E4B-it (HF 2026-03-02)
- https://huggingface.co/google/gemma-4-12B-it (HF 2026-05-23)
- https://huggingface.co/google/gemma-4-26B-A4B-it
- https://huggingface.co/kakaocorp/kanana-2-3b-instruct (2026-07-27 공개, LICENSE 포함)
- https://huggingface.co/kakaocorp/kanana-2-1.3b-instruct
- https://huggingface.co/kakaocorp/kanana-2-30b-a3b-instruct-2601
- https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-1.2B
- https://huggingface.co/naver-hyperclovax/HyperCLOVAX-SEED-Think-14B
- https://huggingface.co/naver-hyperclovax/HyperCLOVAX-SEED-Omni-8B
- https://huggingface.co/ibm-granite/granite-4.2-8b (2026-08-25)
- https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512
- https://huggingface.co/LiquidAI/LFM2.5-8B-A1B
- https://huggingface.co/LiquidAI/LFM2.5-2.6B
- https://huggingface.co/openai/gpt-oss-20b
- https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16
- https://huggingface.co/trillionlabs/Trida2.0-4B (2026-09-18)
- https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf
- https://huggingface.co/deepseek-ai/DeepSeek-R1

**GGUF**
- https://huggingface.co/unsloth/Qwen3.5-9B-GGUF
- https://huggingface.co/unsloth/Qwen3.5-4B-GGUF
- https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF
- https://huggingface.co/unsloth/gemma-4-12b-it-GGUF
- https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf
- https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF
- https://huggingface.co/mradermacher/kanana-2-3b-instruct-GGUF
- https://huggingface.co/ggml-org/gpt-oss-20b-GGUF
- https://huggingface.co/Qwen/Qwen3-8B-GGUF
- https://huggingface.co/Qwen/Qwen3-14B-GGUF

**논문 (HF 미러)**
- Gemma 4 기술보고서 https://huggingface.co/papers/2607.02770
- gpt-oss https://huggingface.co/papers/2508.10925
- 한국어 언어 혼용 https://huggingface.co/papers/2604.16235
- OpenJarvis https://huggingface.co/papers/2605.17172 (2026-05)
- When Agents Fail to Act https://huggingface.co/papers/2601.16280
- TinyLLM https://huggingface.co/papers/2511.22138
- ToolRL https://huggingface.co/papers/2504.13958
- Toucan https://huggingface.co/papers/2510.01179
- When2Call https://huggingface.co/papers/2504.18851
- DiaTool-DPO https://huggingface.co/papers/2504.02882
- Hammer https://huggingface.co/papers/2410.04587
- TinyAgent https://huggingface.co/papers/2409.00608
- ToolACE https://huggingface.co/papers/2409.00920
- APIGen-MT https://huggingface.co/papers/2504.03601
- FunctionChat-Bench https://huggingface.co/papers/2411.14054 (2024-11-21)
- 다국어 SFT https://huggingface.co/papers/2401.01854
- LoRA 망각 https://huggingface.co/papers/2405.09673
- Language Confusion https://huggingface.co/papers/2406.20052
- DualTune https://huggingface.co/papers/2510.00229
- OPT-350M ToolBench https://huggingface.co/papers/2512.15943
- OpenAgent https://huggingface.co/papers/2607.01084
- Jan-nano https://huggingface.co/papers/2506.22760
- Qwen3 https://huggingface.co/papers/2505.09388
- 4060 LoRA 처리량 https://huggingface.co/papers/2509.12229
- Puro-2B https://huggingface.co/api/papers/2608.27370 (2026-08-27)

**[S]로만 확인한 논문**
- KOPA-Bench https://arxiv.org/abs/2609.05395
- SFT와 GRPO 비교 https://arxiv.org/abs/2609.17848
- PA-Tool https://arxiv.org/abs/2510.07248

**프레임워크와 문서**
- PyPI JSON: unsloth 2026.9.11 (2026-09-23, wheel METADATA), trl 1.13.0 (2026-09-10), axolotl 0.19.0, llamafactory 0.9.5, torchtune 0.6.1, vllm 0.30.0, torch 2.14.0, bfcl-eval 2026.3.23, lm-eval 0.4.13, llama-cpp-python 0.3.35, exllamav3 1.5.1
- https://huggingface.co/docs/trl/sft_trainer, https://huggingface.co/docs/trl/grpo_trainer, https://huggingface.co/docs/trl/chat_templates (v1.13.0)
- https://huggingface.co/docs/transformers/model_doc/qwen3_5
- https://huggingface.co/docs/hub/ollama
- https://huggingface.co/docs/hub/agents-local
- https://huggingface.co/blog/ngxson/gguf-my-lora
- https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/chat_template.jinja
- Ollama 버전: proxy.golang.org/github.com/ollama/ollama/@latest
- npm registry (Pi, OpenClaw, OpenCode, Cline, Codex CLI, Claude Code, `@lmstudio/sdk`)
- [S]: https://unsloth.ai/docs/models/qwen3.5/fine-tune, docs.ollama.com (gpu, context-length, anthropic-compatibility), lmstudio.ai/changelog, docs.cline.bot/running-models-locally/overview, docs.openhands.dev, docs.nvidia.com CUDA 13 릴리스 노트, NVIDIA GA102 백서

**데이터셋 (HF)**
- https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k
- https://huggingface.co/datasets/Salesforce/APIGen-MT-5k
- https://huggingface.co/datasets/Team-ACE/ToolACE
- https://huggingface.co/datasets/NousResearch/hermes-function-calling-v1
- https://huggingface.co/datasets/nvidia/When2Call
- https://huggingface.co/datasets/nvidia/Nemotron-Agentic-v1
- https://huggingface.co/datasets/nvidia/Nemotron-SFT-Agentic-v2
- https://huggingface.co/datasets/Agent-Ark/Toucan-1.5M
- https://huggingface.co/datasets/palette-lab/songgot-tools-ko (2026-09-11)
- https://huggingface.co/datasets/jungsanghyun/ko-agentic-toolcall
- https://huggingface.co/datasets/gyung/toolllama-korean-function-calling
- https://huggingface.co/datasets/CohereLabs/aya_dataset
- https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea
- https://huggingface.co/datasets/HAERAE-HUB/KMMLU
- https://huggingface.co/datasets/LGAI-EXAONE/KoMT-Bench
- https://huggingface.co/datasets/HuggingFaceFW/fineweb-2
- https://huggingface.co/spaces/huggingface-KREW/Ko-AgentBench

**약관**
- https://www.anthropic.com/legal/commercial-terms (시행 2025-06-17)
- https://www.anthropic.com/legal/consumer-terms (시행 2025-10-08)
- [S]: https://openai.com/policies/row-terms-of-use/, https://openai.com/policies/services-agreement/, https://ai.google.dev/gemini-api/terms, DeepSeek Open Platform ToS
- Llama 3 / 3.1 라이선스: HF 게이트 원문 (2024-04-18 / 2024-07-23)
- Gemma ToU 사본: https://huggingface.co/tokyotech-llm/Llama-3.1-Swallow-8B-Instruct-v0.5/blob/main/GEMMA_TERMS_OF_USE.md (2024-04-01)

**사례**
- https://huggingface.co/distil-labs/Distil-gitara-v2-Llama-3.2-3B-Instruct
- https://huggingface.co/acon96/Home-3B-v3-GGUF
- https://huggingface.co/palette-lab/songgot-x-0.8b (2026-09-16)
- https://huggingface.co/palette-lab/songgot-l
- https://huggingface.co/sdobson/nanochat
- https://huggingface.co/blog/smollm3 (2025-07-08)
- https://huggingface.co/TinyLlama/TinyLlama-1.1B-intermediate-step-1431k-3T
- https://huggingface.co/blog/hf-skills-training (2025-12-04)
- https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/discussions/10
- [2차 출처/S]: marktechpost.com ART·E (2025-04-29), zenml.io, kenashe.ai (2026-09-07), x.com/karpathy/status/1978615547945521655

**노트북 하드웨어와 속도 ([S])**
- videocardz.com (RTX 5050/5060/5070 Laptop)
- thefpsreview.com (2026-04-29)
- localscore.ai (accelerator/529, model/1, model/2)
- runaihome.com (NVFP4, Sysmem Fallback)
- insiderllm.com (llama.cpp NVFP4)

**리포지토리 파일 (로컬 확인)**
- `/home/user/AutoRunpod/CLAUDE.md`
- `/home/user/AutoRunpod/scripts/auto_backup_workspace.sh`
- `/home/user/AutoRunpod/listener/server.py`
- `/home/user/AutoRunpod/SETUP_HISTORY.md`
- `/home/user/AutoRunpod/scripts/` (`runpod_pod_status.py`, `verify_lora_integrity.py`, `submit_job.py`, `restart_forge_clean.sh`, `jupyter_exec.py`, `finish_project.py`)
- `/home/user/AutoRunpod/chibi/comfy_client.py`
