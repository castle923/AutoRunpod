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

- **CFG 1 에서는 네거티브 프롬프트가 작동하지 않는다.** unconditional 경로
  가중치가 0 이므로 네거티브 토큰이 결과에 반영되지 않는다. 화면의 방대한
  네거티브(bad hands, missing fingers, distorted anatomy 등)는 전부 무효다.
  Turbo distilled 모델을 쓰는 이상 감수해야 하는 트레이드오프.
- **1536x1536 은 SDXL 학습 픽셀 예산(약 1024^2)의 2.25배**다. 이 영역대에서는
  인물 중복 / 사지 증식 / 구도 분열이 전형적으로 나온다. 베이스가 고해상도
  파인튜닝을 거쳤다면 무해할 수도 있어 단정하지 않는다. 같은 시드로
  1024x1024 대조군을 뽑으면 즉시 판별된다.

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
