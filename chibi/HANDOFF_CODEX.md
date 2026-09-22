# 인수인계: Chibi/Anima 환경 재현 — 실현 가능성 점검 요청

작성: 2026-09-19, Claude Opus 세션에서 작성.
수신: Codex (또는 점검을 수행할 에이전트)

---

## 1. 목표

RunPod GPU 포드 위에 아래 환경을 **새로 구축**할 수 있는지 점검해 달라.

> **ComfyUI + Anima(Cosmos-Predict2-2B 계열) 체크포인트 + 캐릭터 LoRA + Chibi
> Vue SPA 프론트엔드**로 구성된 이미지 생성 서버.
> 원본은 Cloudflare Quick Tunnel로 노출되어 있었고, 프록시 정책으로 직접 접근은
> 불가하여 개발자도구 데이터로 역산했다.

"재현"의 범위: 캐릭터 LoRA는 사용자가 자기 것으로 교체. Chibi 프론트엔드 정적
파일이 없어도 API 직접 호출로 동일한 생성 결과를 낼 수 있으면 된다.

---

## 2. 현재 인프라 개요

- **RunPod Community Cloud** (Secure Cloud 사용 금지 — 예산 원칙)
- 기존 포드: RTX 4090, 300GB 볼륨, 템플릿 `runpod/forge:3.3.0`
- 기존 부트스트랩: `scripts/bootstrap_pod.sh` — **Forge(A1111 계열) 전용**
- ComfyUI는 과거에 한번 구성했으나 현재 포드에는 복원되어 있지 않음
  (`SETUP_HISTORY.md` 2~4번 항목 참조)

---

## 3. Anima 모델 정보

### 아키텍처

- **SDXL이 아니다.** NVIDIA Cosmos-Predict2-2B 기반, 2B 파라미터
- 텍스트 인코더: Qwen3-0.6B / VAE: Qwen-Image VAE
- 해상도 지원 범위: 512² ~ 1536²
- **ComfyUI 네이티브 지원** — A1111/Forge에서는 로드 불가 (비표준 아키텍처)
- 공동 개발자가 Comfy Org

### 관측된 체크포인트

`animality_baseFlat_trubo.safetensors` — Civitai 모델 2532722 (Animality).
Anima-preview-3 기반 커뮤니티 파생본.

### 입수 경로 (2가지)

| 경로 | 설명 | 동일 재현 |
|---|---|---|
| A. Civitai 직접 다운로드 | 모델 2532722에서 해당 버전 다운로드 | **완전 동일** |
| B. HF 분리 파일 | `circlestone-labs/Anima` + turbo LoRA 조합 | **근사치만** (Animality 자체의 파인튜닝/머지가 빠짐) |

상세: `chibi/MODEL.md`

### 라이선스

CircleStone Labs Non-Commercial License. 생성 이미지의 상업적 사용은 허용되나
모델을 유료 API로 호스팅하는 것은 별도 라이선스 필요. 개인 사용은 문제없음.

---

## 4. 관측된 생성 세팅

| 항목 | 값 | 비고 |
|---|---|---|
| Checkpoint | animality_baseFlat_trubo.safetensors | 드롭다운에 이것 하나만 있었음 |
| LoRA | 달타셀일러_ANIM... (UI에서 잘림) | 캐릭터 LoRA, 교체 대상 |
| LoRA strength | model 1.0 / clip 1.0 | |
| Steps | 16 | UI에서 잠김. 공식 권장 Turbo 8-12 |
| CFG | 1 | UI에서 잠김. Turbo 전용값 |
| Sampler | er_sde | 공식 기본값과 일치 |
| Scheduler | simple | 공식 예제와 일치 |
| 해상도 | 1536x1536 (1:1) | 지원 범위 상한이지만 정상 |
| Seed | -1 (랜덤) | |

**CFG 1에서는 네거티브 프롬프트가 수학적으로 무효**하다 (unconditional 경로
가중치 = 0). Anima-Turbo는 CFG 1 전용 설계이므로 설정 자체는 올바름.

상세: `chibi/OBSERVED.md`

---

## 5. 이미 만들어진 도구와 파일

### 저장소: `castle923/AutoRunpod`, 브랜치 `claude/backup-repo-review-setup-g9plm3`

`main` 대비 +2,951줄, 24개 파일 변경. 아직 머지되지 않음.

| 파일 | 역할 | 검증 상태 |
|---|---|---|
| `chibi/workflow_anima.json` | ComfyUI API 워크플로 (단일 체크포인트 경로) | 구문 검증 완료. **실제 ComfyUI 제출 미검증** |
| `chibi/workflow_anima_split.json` | HF 분리 파일용 워크플로 (UNETLoader+CLIPLoader+VAELoader) | 동일 |
| `chibi/comfy_client.py` (193줄) | ComfyUI `/prompt` API 클라이언트. probe(모델 목록)/run(생성) 명령. WS 재연결+history fallback 포함 | py_compile 통과, 로직 검토 완료. **실서버 테스트 미완** |
| `chibi/read_png_workflow.py` (147줄) | PNG tEXt 청크에서 ComfyUI/A1111 생성 파라미터 추출 | 합성 PNG + HF 공식 example.png으로 검증 완료 |
| `chibi/README.md` | 재현 가이드, 부품 목록, nginx 예시, 대조군 실험 명령 | 문서 |
| `chibi/OBSERVED.md` | 관측 원본 기록, 세팅 비교표, 프론트엔드 결함 9건, Anima 프롬프트 규칙 | 문서 |
| `chibi/MODEL.md` | 체크포인트 계보 조사 결과, 입수 경로 2가지, 라이선스 | 문서 |
| `scripts/bootstrap_pod.sh` | 포드 부트스트랩 (현재 Forge 전용, ComfyUI 미포함) | 실동작 검증 완료 (Forge 부분) |

---

## 6. 점검 요청 사항

### 6-1. ComfyUI 부트스트랩 자동화 (핵심 갭)

`bootstrap_pod.sh`는 Forge 전용이다. ComfyUI를 추가 구성하는 자동화가 없다.

과거에 수동으로 했던 절차 (`SETUP_HISTORY.md`):
1. `/workspace/ComfyUI`에 git clone
2. 전용 venv (`/workspace/venvs/comfyui`) 구성
3. torch 버전 호환성 (cu126 인덱스 사용, cu13x는 드라이버 충돌)
4. Forge의 models/ 디렉토리와 심볼릭 링크로 모델 공유
5. 8188 포트로 백그라운드 실행

**점검 포인트:**
- 이 절차를 `bootstrap_pod.sh`에 통합 또는 별도 스크립트로 자동화할 수 있는가?
- Anima의 비표준 아키텍처가 최신 ComfyUI에서 추가 커스텀 노드 없이 작동하는가?
  (관측된 샘플러 `sa_solver`, `er_sde_cps`는 최근 ComfyUI 코어에 포함됨)
- `runpod/forge:3.3.0` 도커 이미지의 CUDA/드라이버 버전과 ComfyUI torch 요구사항 간 충돌 가능성

### 6-2. comfy_client.py 실동작 검증

실제 ComfyUI 인스턴스 상대로 테스트된 적이 없다.

**점검 포인트:**
- workflow JSON 구조가 현재 ComfyUI API 스펙과 호환되는가?
- WebSocket `/ws?clientId=` 프로토콜이 현재 ComfyUI 버전과 맞는가?
- `/history/{prompt_id}` fallback 경로가 실제로 완성 이미지 경로를 반환하는가?
- `resolve_lora()` 의 `/object_info` 응답 구조 가정이 맞는가?

### 6-3. 모델 파일 배치

Animality 체크포인트를 ComfyUI에서 인식하려면:

- `models/checkpoints/animality_baseFlat_trubo.safetensors`에 놓으면 `CheckpointLoaderSimple`이 잡는가?
- Anima 아키텍처를 ComfyUI가 자동 감지하는가, 아니면 별도 모델 config가 필요한가?
- HF 분리 파일 경로(B)의 경우 `models/diffusion_models/`, `models/text_encoders/`, `models/vae/` 디렉토리 구조가 ComfyUI 기본 구조와 맞는가?

### 6-4. 기존 Forge와의 공존

현재 포드는 Forge가 주력이다. ComfyUI를 추가할 때:

- 포트 충돌 없는가? (Forge 3000/7860, ComfyUI 8188)
- 모델 디렉토리 심볼릭 링크로 공유할 때, Anima 체크포인트가 Forge에 노출되면 Forge가 로드 시도하다 에러를 내는가?
- 메모리: RTX 4090 24GB에서 Forge와 ComfyUI를 동시에 올릴 수 있는가, 아니면 한쪽을 내려야 하는가?

### 6-5. rclone 인증 만료

Google Drive 백업/복원에 쓰는 rclone OAuth 토큰이 `invalid_grant`로 만료됨.
재인증은 사용자 브라우저 OAuth가 필요하므로 에이전트가 직접 할 수 없다.
이건 점검이라기보다 **알려두는 사항**.

### 6-6. 브랜치 상태

`claude/backup-repo-review-setup-g9plm3` 브랜치에 17개 커밋이 `main` 대비 미머지.
chibi 관련 5개 커밋 외에 listener, finish_project, auto_finish_watcher 등 운영
도구 12개 커밋이 함께 있다. PR은 아직 생성되지 않았다.

---

## 7. 결론 (현재 판단)

| 항목 | 판단 | 근거 |
|---|---|---|
| ComfyUI 설치 자체 | **가능** | 과거 성공 이력 있음, 절차 문서화됨 |
| Anima 체크포인트 로드 | **가능 (조건부)** | ComfyUI 네이티브 지원 공식 명시. 단 Animality 파생본은 Civitai에서 직접 다운로드 필요 |
| 워크플로 실행 | **높은 확률로 가능, 미검증** | 관측 데이터로 역산한 워크플로이므로 실서버 테스트 전까지 확정 불가 |
| Chibi 프론트엔드 | **블로커** (없어도 API로 우회 가능) | minify된 번들 3개 파일이 원본 포드에만 존재 |
| Forge 공존 | **가능** | 포트 분리 + 심볼릭 링크. 과거 구성 경험 있음 |
| 부트스트랩 자동화 | **미완성** | ComfyUI 부분 스크립트 미작성 |

**한 줄 요약: 포드를 열고 ComfyUI + Anima 환경을 수동으로 구축하는 것은 가능하다.
자동화 스크립트는 아직 없고, comfy_client.py는 실서버 검증이 필요하다.**

---

## 8. 파일 참조 경로 (저장소 내 상대 경로)

```
chibi/
├── README.md                  # 재현 가이드
├── OBSERVED.md                # 관측 데이터 원본
├── MODEL.md                   # 체크포인트 계보
├── HANDOFF_CODEX.md           # 이 문서
├── workflow_anima.json        # 단일 체크포인트 워크플로
├── workflow_anima_split.json  # HF 분리 파일 워크플로
├── comfy_client.py            # API 클라이언트
└── read_png_workflow.py       # PNG 메타데이터 추출

scripts/bootstrap_pod.sh       # 포드 부트스트랩 (Forge 전용)
SETUP_HISTORY.md               # 과거 ComfyUI 구축 이력
```

---

## 9. 보안 주의사항 (반드시 준수)

- `GITHUB_TOKEN`이 노출되면 `castle923/Runpod-Backup`을 통해 Google Drive 전체 접근 가능한 refresh_token이 유출됨. 환경변수로만 전달, 로그/커밋/공개 채널에 절대 남기지 말 것
- `secrets/rclone.conf`는 비공개 저장소 `castle923/Runpod-Backup`에만 존재. 공개 저장소 `castle923/AutoRunpod`에 절대 포함시키지 말 것
- 터널로 ComfyUI API를 노출할 때 인증 없이 `/prompt`와 `/view`가 열리므로, Cloudflare Access 또는 basic auth를 반드시 앞에 둘 것
- **포드를 정지시키지 말 것** — RTX 4080 SUPER는 RunPod 매물이 없어 복구 불가 (포드 1은 이미 종료됨)
