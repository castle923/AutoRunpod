# 관측 원본 (2026-09-18)

출처: `blackjack-arrangement-then-wear.trycloudflare.com/chibi/` 개발자도구.
사이트 직접 접근은 프록시 정책(trycloudflare.com 403)으로 불가하여
사용자가 제공한 번들 / CSS / DevTools 스크린샷에 근거한다.

## 백엔드

콘솔에 `backend: comfyui` 기록. 아래 두 목록이 ComfyUI 임을 확정한다
(둘 다 하드코딩이 아니라 `/object_info` 실시간 조회 결과).

- Scheduler: simple, sgm_uniform, karras, exponential, ddim_uniform, beta,
  normal, linear_quadratic, kl_optimal
- Sampler: euler … er_sde, er_sde_cps, sa_solver, sa_solver_pece,
  seeds_2, seeds_3, res_multistep_*, gradient_estimation_*

`sa_solver` / `er_sde_cps` 는 최근 추가분이므로 ComfyUI 최신 리비전.

## 세팅

| 항목 | 값 |
|---|---|
| Checkpoint | animality_baseFlat_trubo.safetensors (드롭다운에 이것 하나뿐) |
| LoRA | 달타셀일러_ANIM... (UI 에서 잘림) / model 1.0 / clip 1.0 |
| Steps | 16 (UI 잠김) |
| CFG | 1 (UI 잠김) |
| Sampler | er_sde |
| Scheduler | simple |
| 해상도 | 1536x1536 (1:1), 프리셋 상한 |
| Seed | -1 (랜덤) |

해상도 프리셋: 1536x1536 / 1536x640 / 1344x768 / 1216x832 / 1152x896 /
1024x1024 / 832x1216 / 768x1344. 세로 4:3(896x1152)만 누락.

## 세팅상 유의점

**정정.** 최초 분석에서 UI 의 해상도 프리셋이 전부 "SDXL" 로 라벨돼 있는 것을 보고
SDXL 아키텍처로 가정해 "1536x1536 은 학습 픽셀 예산의 2.25배" 라고 적었다. **틀렸다.**
체크포인트는 Anima 계열이고, Anima 는 SDXL 이 아니라 NVIDIA Cosmos-Predict2-2B
기반의 2B 파라미터 모델이다. 공식 README 기준 **512^2 ~ 1536^2 를 지원**하므로
1536x1536 은 정상 범위의 상한이다. 해상도는 문제가 아니다.
프리셋의 "SDXL" 라벨은 프론트엔드가 들고 있는 하드코딩 문자열일 뿐이다.

유효하게 남는 지적은 하나다.

- **CFG 1 에서는 네거티브 프롬프트가 작동하지 않는다.** unconditional 경로
  가중치가 0 이므로 네거티브 토큰이 결과에 반영되지 않는다. 이건 아키텍처와
  무관한 CFG 의 정의다. 화면의 방대한 네거티브는 전부 무효다.
  다만 Anima-Turbo 는 공식적으로 CFG 1 전용이므로 설정 자체는 올바르다.
  네거티브를 살리려면 Turbo 가 아닌 Base/Aesthetic + CFG 4~5 로 가야 한다.

공식 권장치와의 차이:

| 항목 | 관측값 | Anima 공식 권장 | 판정 |
|---|---|---|---|
| CFG | 1 | Turbo 는 1 | 일치 |
| Steps | 16 | Turbo 는 8~12 | 초과. 다만 아래 참조 |
| Sampler | er_sde | 저자 기본값이 er_sde | 일치 |
| Scheduler | simple | 공식 예제가 simple | 일치 |
| 해상도 | 1536x1536 | 512^2~1536^2 | 상한이지만 정상 |

### steps 를 줄여야 하는가

처음에 16 -> 12 를 권했는데 근거가 약했다. 저자가 적은 권장 이유는
"스텝 수에 비례해 과금하는 온라인 플랫폼에서 훨씬 저렴하다" 였고,
RunPod 처럼 GPU 를 시간 단위로 통째로 빌리는 환경에는 그대로 적용되지 않는다.

RunPod 에서도 처리량은 곧 렌탈 시간이므로 무관하지는 않다. 800장 기준
샘플링 스텝 25% 감소는 배치 전체로 15~20% 단축에 해당한다. 판단 기준은
처리량에 쫓기느냐다.

- 뽑을 물량이 밀려 있다 -> 줄이면 같은 시간에 더 나온다
- 포드를 켜둘 시간이 정해져 있다 -> 줄일 이유가 없다. 남는 시간을
  품질에 쓰는 편이 낫다

품질 측면은 단정할 근거가 없다. 증류 모델은 "스텝이 많을수록 좋다" 가
성립하지 않고, 증류 타겟을 넘기면 대개 수렴 후 정체하며 일부 turbo 계열은
오히려 열화한다. Anima-Turbo 가 어느 쪽인지는 공식 문서에 없다.
같은 시드로 steps 12 / 16 을 각각 8장 뽑아 비교하면 바로 판별된다
(comfy_client.py --seed-base 고정 + --steps).

메모리와는 무관하다. 메모리 증가는 경과 시간이 아니라 처리한 이미지 수에
따라 붙으므로, 스텝을 줄여도 OOM 위험은 줄지 않는다.

## Anima 프롬프트 규칙 (공식 README)

현재 프롬프트가 SDXL/Pony 관습대로 쓰여 있는데, Anima 는 규칙이 다르다.

- **프롬프트 가중치는 SDXL 보다 높게 줘야 한다.** 예: `(chibi:2)`
- **아티스트 태그는 반드시 `@` 를 앞에 붙인다.** 안 붙이면 효과가 거의 없다
- 태그는 소문자, 언더스코어 대신 공백. score_ 태그만 예외
- 태그 순서: [품질/메타/연도/안전] [1girl 등] [캐릭터] [시리즈] [아티스트] [일반]
- Danbooru 와 Gelbooru 가 다른 태그는 Gelbooru 쪽을 쓴다
- 안전 태그(safe / sensitive / nsfw / explicit)를 명시하면 의도치 않은 출력이 준다
- 권장 네거티브: worst quality, low quality, score_1, score_2, score_3,
  artist name, blurry, jpeg artifacts, chromatic aberration
  (단 Turbo + CFG 1 에서는 위 사유로 무효)

## 프론트엔드 결함 (심각도순)

1. WebSocket 재연결 시 이전 prompt_id 를 재구독하지 않음 -> 생성 중 끊기면
   완성 이미지 유실. 실측 로그:
   `22:27:13 closed 1006 / 22:27:14 open / 22:27:54 closed 1006 / 22:27:56 open`
   (약 40초 주기 = Cloudflare Quick Tunnel 유휴 WebSocket 타임아웃 패턴)
   `/history/<prompt_id>` 조회로 보정 가능. comfy_client.py 에는 반영돼 있다.
2. 프리뷰 Blob 에 revokeObjectURL() 누락 -> 장시간 배치 시 탭 메모리 누수.
   실측: `Blob {size: 68772, type: image/jpeg}` 등이 스텝마다 누적
3. 터널에 UI 와 ComfyUI API 가 인증 없이 동시 노출
4. 설정을 콤마 join 으로 직렬화 -> 프롬프트/모델명에 콤마 포함 시 파손
5. WebSocket 재연결 백오프 없음 (1~2초 간격 무한 재시도)
6. 번들 파일명에 해시 없음 (assets/index.js 고정) -> 배포 갱신해도 구버전 캐시
7. `#app { -webkit-user-select: none }` -> 시드/모델명 드래그 복사 불가
8. LoRA 이름 truncate + title 속성 없음 -> 긴 이름 식별 불가
9. chibi/icon_192.png 403 -> PWA 아이콘 누락 (기능 무관)

`setImageFormat` 의 서버 전역 설정 변조와 IndexedDB base64 적재는 WebUI
경로 전용 코드라 현재 구성에서는 해당 없음.

## 프론트엔드 구성

Vue 3.5.29 SPA (Vite), axios 1.13.5, vue3-lazyload, textarea-caret-position.
`<div id="app" data-v-app>` + ./assets/index.js + ./assets/index.css.

- 저장소: localStorage `chibi.settings` / `chibi.generationInfo` /
  `chibi.history(<url>)`, IndexedDB `history` / `historyStore` / `urlIndex`
- 테마 9종을 `<html>` 클래스로 전환: radio-black(현재), radio-white, novellus,
  nord, catppuccin, tokyo-night, dracula, gruvbox, amoled
- JS 주입 CSS 변수: `--e6bcdc4a` = 히스토리 패널 너비(px),
  `--v597bc4e4` = 진행률(%). 후자가 토스터 배경 그라디언트를 구동하며,
  별도 프로그레스바 없이 **토스터 자체가 진행바**다
- 반응형 분기: 1280px(히스토리 오버레이), 900px(설정 패널 접힘)
- `--color-tag-1~5` = 자동완성 태그 색상, Danbooru 분류 5종과 대응
- `.shirink` 는 shrink 오타지만 전 파일 일관 사용이라 동작 무관
