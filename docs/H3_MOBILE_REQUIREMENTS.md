# MiniMax H3 모바일 킷 도입 — 요청 사항 정리

- 작성일: 2026-09-23
- 대상: D2 결정 전(현 포드 `sydh2pm05u5rg2`(RTX 3090 24GB, Community Cloud) 또는 신규 Community 포드)
- 근거: 리서치 노트 4건
  - 킷 서버·UI 분석
  - 킷 스크립트·보안 분석
  - 현재 포드·저장소 호환성
  - 외부 링크 검증

**표기 규칙**

- 경로 약어
  - `K/` = 사용자가 공유한 `h3_mobile_kit.zip`의 `h3_mobile/` 폴더. 킷 파일 인용에 `K/`가 없으면 모두 이 폴더 기준이다(예: `server.py:28`). 킷 원본은 토큰이 들어 있어 이 저장소에 넣지 않았다(D9).
  - `U` = 사용자가 공유한 단독 모델 목록 `minimax_h3_models.txt`
  - `R/` = 이 저장소(`castle923/AutoRunpod`) 루트
- 근거가 없는 사실은 적지 않았다. 확인하지 못한 항목은 **미검증**으로 표시했다. 외부 지식에 기댄 항목은 "(외부 지식)"으로 표시했다.
- 현재 포드 사실의 우선순위: `R/project/HANDOFF.md`(2026-09-20) → `R/project/STATUS.md`(09-21) → `R/STATUS.md`(09-22) → `R/docs/OPERATIONAL_VERIFICATION.md`(09-22 관찰) 순으로 최신 자료를 따른다. `R/README.md:13`(RTX 4080 SUPER, 500GB), `R/docs/RUNBOOK.md`, `R/docs/OPERATIONS_LOG_2026-09-16.md`, `R/MONITORING_ROUTINES.md`, `R/SETUP_HISTORY.md`는 이전 포드의 기록이며, 인용할 때 "이전 포드"라고 표시한다.
- Civitai 토큰 값은 이 문서 어디에도 적지 않는다. 가리킬 때는 "하드코딩된 Civitai 토큰(값 생략)"이라고 쓴다.
- 조사 중에 하지 않은 일
  - RunPod 변경
  - Google Drive 접근
  - 모델 본문 다운로드. 네트워크 확인은 HEAD 요청과 메타데이터 조회만 했다.

---

## 0. 요약 (TL;DR)

1. **[차단] 라이선스.** MiniMax H3 커뮤니티 라이선스는 대한민국·미국·EU·영국을 "Excluded Territories"로 정한다(MiniMaxAI/MiniMax-H3 `LICENSE` L8/L10, L42(V.4), L65(AUP #1)). 필수 #2(TE)·#3·#4(VAE)는 HF 메타데이터상 직접 이 라이선스이고, DaSiWa DiT도 따를 가능성이 높다(미검증). 모델을 받거나 비용이 생기기 전에 사용자가 판단해야 한다(D1).
2. **[차단] VRAM.**
   - 킷 요구: VRAM 32GB 이상. 검증 환경은 RTX 5000 Ada 32GB였고 피크가 31.9/32.7GB였다(`K/README.md:6-7,24,56-59`).
   - 현재 포드: RTX 3090 24GB. GPU와 RAM 62GB를 Forge와 나눠 쓴다.
   - 결정할 것: 기존 포드에서 Forge와 시간을 나눠 쓸지, 32GB 이상(권장 48GB급) Community 포드를 새로 만들지(D2). 어느 쪽이든 `sydh2pm05u5rg2`는 정지하지 않는다.
3. **[차단·보안] Civitai 토큰.**
   - `download_models.sh:7`은 하드코딩된 Civitai 토큰(값 생략)을 기본값으로 쓴다.
   - zip이 이미 공유되었으므로 소유자가 토큰을 폐기하고 재발급해야 한다. 새 토큰은 `CIVITAI_TOKEN` 환경변수로만 넘기며, 전달 경로는 I3를 따른다(RunPod 콘솔의 Pod 환경변수 편집은 금지).
   - 이 스크립트를 `/workspace` 루트나 `/workspace/scripts/`에 두면 auto_backup이 30분마다 Drive로 올린다(`R/scripts/auto_backup_workspace.sh:17,33-37,44`).
4. **[차단] 경로 불일치와 `restart_comfy.sh`.**
   - 경로: 킷은 `/workspace/runpod-slim/ComfyUI`와 `.venv-cu128`을 가정한다. 포드는 `/workspace/ComfyUI`와 `/workspace/venvs/comfyui`다.
   - `restart_comfy.sh`는 포드의 ComfyUI(`main.py --listen 0.0.0.0 --port 8188`)를 먼저 죽인다. 그다음 `cd`가 실패해서 다시 띄우지 못한다(`restart_comfy.sh:21,38`).
   - `server.py`는 크래시를 감지하면 이 스크립트를 자동으로 호출한다(`server.py:30,347-373`).
   - 최신 기록상 포드 ComfyUI는 설치·가동 상태였다(`R/project/HANDOFF.md:19,39`). 따라서 이 위험은 가정이 아니라 실제 위험이다(현재 가동 여부는 미검증).
   - 이 스크립트를 고치거나 무력화하기 전에는 `server.py`를 기동하지 않는다. 무력화 방법: README:30의 복사 단계를 수행하지 않는다(P2-9와 일치). 그러면 기본 경로(`/workspace/restart_comfy.sh`)가 없어 `server.py:350-351`에서 자동 재시작이 꺼진다. `RESTART_COMFY` 환경변수 방식은 모든 기동 경로에서 export해야 하므로 보조 수단이다.
5. **[차단] 외부 노출.**
   - 19123이 포드 노출 포트에 있는지는 미검증이다. `R/project/HANDOFF.md:15-22`는 서비스 목록일 뿐 포드 포트 설정이 아니다(I5로 확인). 킷 `README.md:49-51`이 말하는 템플릿 기본 포트는 신규 `runpod/comfyui` 포드에만 해당한다.
   - 포트를 추가하는 pod edit는 컨테이너를 다시 만든다. 이때 cron, rclone 설정, nginx 설정이 사라진다. `sydh2pm05u5rg2`에는 금지(범위 밖).
   - 선택지: SSH 터널, 인증을 붙인 cloudflared, 기존 외부 포트 재사용(C, 기존 ComfyUI 재기동 필요), 새 포드를 만들 때 포트를 포함하기(D4, G7).
6. **[차단·보안] 기존 포드 노출 포트(D14).**
   - 저장소 기록상 포드 Jupyter(8888)는 토큰 없이 `_xsrf` 쿠키만으로 커널을 만들어 코드를 실행할 수 있다(`R/docs/RUNBOOK.md:51`(이전 포드), `R/scripts/jupyter_exec.py:4-6`). 현 포드 8888도 공개 프록시로 가동 중이었고(`R/project/HANDOFF.md:21`), 09-22에는 외부에서 Jupyter API로 `/workspace`를 조회했다(`R/docs/OPERATIONAL_VERIFICATION.md:9,32`). 현 포드의 Jupyter 인증 여부는 미검증이다.
   - 무인증이라면 pod ID(공개)를 아는 누구나 코드를 실행할 수 있다. 이 경우 포드에 둔 환경변수(`/proc/<pid>/environ`), `/workspace/rclone.conf`(`R/docs/OPERATIONAL_VERIFICATION.md:54`), H3 UI 인증·127.0.0.1 바인드가 모두 무력하다.
7. **[보안] `server.py`.**
   - 인증이 없고 `0.0.0.0`에 바인드한다.
   - 로컬 재현으로 **확인된** 취약점
     - CSRF(text/plain JSON)
     - 교차 사이트 WebSocket 탈취
     - `/media` 접두사 검사 우회
     - 무제한 업로드
     - 업로드한 HTML 파일을 통한 저장형 XSS
   - 워커를 영구 정지시키는 경쟁 조건도 확인됐다.
   - 외부에 노출하거나 무인으로 돌리기 전에 P0 수정이 필수다(§8).
8. **모델.**
   - 킷 목록이 기준이다. video VAE는 fp16을 쓴다. 업로드된 단독 목록(`U`)은 int8 VAE를 권장하지만, 이는 구버전 정보다(int8은 검은 화면이 나온다 — 킷 작성자가 ComfyUI 0.30.0에서 관측했다. 원인은 미확정이다. §2.2 참조).
   - 모바일 UI가 쓰는 파일은 4개, 약 41.74GB(38.87GiB)다. DiT 크기는 추정치라 미검증이다.
   - 잠재 업스케일러 URL은 파일이 옮겨져 404를 반환한다.
9. **포드 상태 미검증.** 2026-09-23 16:59Z, 17:20Z, 17:36Z, 17:48Z 재확인에서 3000/8188/8888/7777과 미노출 포트 19123이 모두 같은 `HTTP/2 404`(본문 없음, server: cloudflare)를 반환했다. 노출되지 않은 포트와 구분되지 않으므로, 포드가 RUNNING이 아니거나 프록시 전체의 문제일 가능성이 높다. 마지막 정상 관측은 2026-09-22 약 01:40–02:00Z(3000 → 200, 8888 → 302; `R/docs/OPERATIONAL_VERIFICATION.md:12,19-20`)다. 콘솔 확인이 최우선이다(I5).

---

## 1. 목표와 범위

### 1.1 킷의 정체

`h3_mobile`은 휴대폰 브라우저에서 MiniMax H3(DaSiWa hybrid turbo) 영상+오디오 생성 작업을 넣고 결과를 보는 웹 UI다.

**구성 파일**

| 파일 | 역할 |
|---|---|
| `server.py` | aiohttp 서버. 작업 큐, ComfyUI 그래프 생성, 크래시 복구. 기본 포트는 8189지만 스크립트는 19123을 쓴다 |
| `static/index.html` | 단일 페이지 UI. 외부 요청 없음 |
| `start.sh` / `watchdog.sh` | 서버 기동과 감시 |
| `restart_comfy.sh` | ComfyUI 재기동 |
| `install_nodes.sh` / `download_models.sh` | 노드와 모델 설치 |
| `models.txt` / `README.md` | 문서 |

**모드**

- T2VA, I2VA(첫 프레임), FL2VA(첫/끝 2장), L2VA(끝 프레임), REF2VA(참조)(`index.html:274-279,586-590`). 이미지를 올리면 T2VA가 자동으로 I2VA로 바뀐다(`index.html:576,633`). 이미지는 모드와 무관하게 최대 2장이다(`server.py:296`).
- 하이브리드 DiT 하나가 두 슬롯을 모두 채운다(`models.txt:14`). REF2VA면 `ref2va_model` 입력에, 그 밖의 모든 모드면 `fl2va_model` 입력에 연결된다(`server.py:247-253`).

**ComfyUI 그래프**(`server.py:195-264`)

- 코어 노드
  - `UNETLoader`, `CLIPLoader`(`type:"minimax"`), `VAELoader` 2개
  - `SamplerCustomAdvanced` 계열
  - `VAEDecode`, `VAEDecodeAudio`, `CreateVideo`, `SaveVideo`
- DaSiWa 노드: `MiniMaxH3Director`, `MiniMaxH3DirectorGuide`, `MiniMaxH3SigmaShift`, `MiniMaxH3Cache`. 이 노드들이 DaSiWa 팩에 속한다는 것은 추정이며 미검증이다.

**기본값**

- 640×480, 4초, 24fps
- 6 steps, euler / simple
- shift: video 6.0, audio 4.0
- 캐시 off

### 1.2 범위

- **포함**
  - 실행 위치 결정
  - 킷의 보안·호환성 수정
  - 모델·노드 설치
  - 접근 경로와 인증
  - Forge와의 공존
  - 백업·자동 기동 정책
  - 검증
- **조건부 포함:** stock DaSiWa 워크플로(ComfyUI 탭)의 선택 기능(잠재 업스케일, AnimeSharp, RIFE)은 D8에서 선택할 때만 범위에 든다.

### 1.3 "완료"의 정의

자세한 검증 항목은 §11에 있다.

1. 선택한 실행 위치에 필수 모델 4개가 있고, sha256 검증을 통과했다.
2. 모바일 UI에는 인증된 경로로만 접근할 수 있다.
3. 640×384 T2VA 작업이 검은 화면이 아닌 영상과 들리는 오디오를 만든다.
4. 크래시 복구는 H3 전용 ComfyUI만 다시 띄운다. 포드의 기존 ComfyUI, Forge, listener는 영향을 받지 않는다.
5. Civitai 토큰이 저장소, 로그, 프로세스 인자, auto_backup이 올리는 로컬 원본 어디에도 남지 않는다(Drive 쪽은 사용자가 직접 확인한다).
6. `sydh2pm05u5rg2`를 정지하거나 편집하지 않았고, 4팀 공유 드라이브에 접근하지 않았다.

---

## 2. 입력 자료와 버전 차이

| 자료 | 위치 | 내용 | 비고 |
|---|---|---|---|
| 단독 모델 목록 | `U` | "MiniMax H3 (DaSiWa T2VA/REF2VA workflow)" 모델·노드 목록 | 킷의 int8 진단 이전 버전으로 추정한다. 내용으로 판단했으며, mtime은 업로드 시각이라 근거가 되지 않는다 |
| h3_mobile_kit.zip | `K/` (zip 날짜 2026-09-14) | README.md, models.txt, download_models.sh, install_nodes.sh, start.sh, restart_comfy.sh, watchdog.sh, server.py, static/index.html | `download_models.sh`에 하드코딩된 Civitai 토큰(값 생략)이 있다 |

**기준 자료는 킷이다**(`K/models.txt`, `download_models.sh`, `server.py:64`).

- 킷은 "Verified on this pod … pure black" 진단을 추가했다(`K/models.txt:31-35`, `README.md:67-71`).
- `server.py`는 fp16 파일명을 하드코딩한다. 따라서 int8만 설치하면 UI가 동작하지 않는다.

### 2.1 두 자료의 차이점

| # | 항목 | U | K | 판정 / 조치 |
|---|---|---|---|---|
| 1 | Video VAE | int8_convrot "2.95"가 기본이고 fp16은 "Alternative"다(U:26-31) | fp16 "5.21"이고 int8은 "(broken)"으로 표시(`K/models.txt:26-35`, `README.md:67-71`, `download_models.sh:29-31`, `server.py:64`). 킷 작성자가 ComfyUI 0.30.0에서 관측했다. 원인은 미확정이다(§2.2) | **fp16을 쓰고 int8은 받지 않는다.** int8이 디스크에 있으면 UI 드롭다운에 노출된다(`server.py:546`, `index.html:780`) |
| 2 | 총량 헤더 | "~37.6 GB" (U:4) | "~37.6 GB" (`K/models.txt:4`, 갱신 누락). 반면 `README.md:19`와 `download_models.sh:2`는 "~43GB" | 37.6은 int8 세트의 GiB 합계다. fp16 기준 `download_models.sh` 세트는 39.52GiB = 42.44GB |
| 3 | 단위 | GiB를 "GB"로 표기 | 같음. 단 fp16 "5.21"만 10진 GB | 계획은 바이트 기준으로 세운다(§6) |
| 4 | 잠재 업스케일러 URL | 404 | 404 (`K/models.txt:47`, `download_models.sh:36`) | 2026-09-17 커밋 `6749d7b`로 파일이 옮겨졌다. 새 경로로 받아 기존 이름으로 저장하거나 리비전을 고정한다 |
| 5 | 잠재 업스케일러 취급 | 선택 | 선택으로 표시(`models.txt:44`)했지만 무조건 받는다(`download_models.sh:36-37`) | 선택 플래그로 바꾼다 |
| 6 | AnimeSharpV4 / RIFE | 선택 목록에 있음 | 목록에는 있지만 스크립트가 받지 않는다. `frame_interpolation` 폴더도 만들지 않는다(`download_models.sh:9-10`) | D8에서 결정 |
| 7 | 커스텀 노드 | U:64-69 | `K/models.txt:68-73` = `install_nodes.sh:18-22` | 동일 |
| 8 | DiT 파일명 | 같음 | Civitai 제공명은 `DasiwaMinimaxH3_dasiwaHybridTurboV2_3203135.safetensors`다(`models.txt:12`). `server.py:62`가 기대하는 이름으로 바꿔 저장해야 한다 | 스크립트가 처리한다(`download_models.sh:22-24`) |

### 2.2 킷 작성 이후 외부 변화

- Comfy-Org가 **다른** int8 video VAE를 올렸다: `vae/minimax_h3_video_vae_int8_convrot.safetensors`, 2,811,065,184 B. 킷은 이 파일을 테스트하지 않았다.
- Kijai README L7: int8_convrot VAE는 "needs ComfyUI 0.36.0 for maximum speed". 킷에서 나온 검은 화면이 ComfyUI 0.30.0 버전 문제일 수 있다(가설, 미검증).

### 2.3 킷 내부 불일치

- `PORT` 기본값: `server.py:28`은 8189다. `start.sh:8`, `watchdog.sh:8`, `README.md:36,39`는 19123이다.

---

## 3. 사용자 결정 요청 (Decisions needed)

### D1. 라이선스 적용 지역 판단 — 차단, 최우선

**사실**

- 라이선스: `minimax-h3-community-license-agreement`. 원문은 `https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/LICENSE`(HTTP 200, 17,604 B)다.

  | 조항 | 내용 |
  |---|---|
  | L8/L10 | Excluded Territories = EU, 영국, **대한민국**, 미국 |
  | L42(V.4), L65(AUP #1) | 적용 지역 밖에서의 사용은 허가되지 않는다 |
  | L23 | 제외 지역 사용자는 라이선스를 문의할 수 있다(통제·가드레일을 조건으로 부여) |
  | IV.1(L36) | 연 매출 $20M 초과 제품·서비스는 별도 서면 허가가 필요하다 |
  | IV.2(L37) | 상용 UI에는 "MiniMax H3"를 표시해야 한다 |
  | III.3.a(L29) | H3로 만든 제품·서비스에 "Powered by MiniMax H3"를 표시한다 |
  | V.2(L40) | 제3자에게 접근을 줄 때는 이용 제한 약관으로 구속하고 고지한다 |
  | V.3(L41) | 출력물로 다른 모델을 개선하는 것은 금지 |
  | V.5(L43) | 제3자에게 생성 서비스를 제공하면 사전에 보호 장치를 두고 유지한다 |
  | AUP #12 | 공개 환경에 게시하는 출력물은 기계 생성물임을 분명히 표시해야 한다 |
  | III.4 | 재배포할 때 NOTICE 파일을 포함해야 한다 |

- 필수 #2(Abiray TE)와 #3·#4(Comfy-Org VAE)는 HF 메타데이터상 직접 `minimax-h3-community-license-agreement`다(각 README 머리 L2-4). 따라서 D1은 DaSiWa와 무관하게 적용된다.
- #1 DaSiWa는 정의상 Model Derivative로 보여 같은 조건을 따를 가능성이 높다(미검증). Civitai 라이선스 필드는 미검증이다.
- UI를 본인 외(팀원 등)에게 제공하면 III.3.a, V.2, V.5가 추가로 적용된다(D4, D15).
- 포드 데이터센터의 국가는 미검증이다.

**선택지**

- A) MiniMax에 라이선스를 문의하거나 법무 검토를 받은 뒤 진행한다.
- B) 사용자 본인 판단으로 진행한다. 책임은 사용자에게 있다.
- C) 도입을 보류한다.

**권장:** A. 최소한 모델 다운로드나 신규 포드 비용이 생기기 전에 결정한다.

**결과**

- 법적 판단 사안이라 이 문서가 결론을 대신하지 않는다.
- C를 고르면 이하 모든 항목을 보류한다.

### D2. 실행 위치 — 차단

| 선택지 | 내용 | 장점 | 단점 / 위험 |
|---|---|---|---|
| **A. 기존 3090 포드** | `sydh2pm05u5rg2`에 별도 ComfyUI+venv를 설치하고 Forge와 시간을 나눠 쓴다 | 추가 비용 없음($0.22/hr 그대로). 새 포드 불필요 | 아래 목록 참고 |
| **B. 새 Community 포드(32GB 이상)** | `runpod/comfyui:1.4.7-cuda13.0` 템플릿 사용. 태그 `active`, `last_updated=2026-08-27`, 4.31GB | 킷 경로와 그대로 맞는다. Forge, listener, cron과 간섭하지 않는다. 3090 포드를 그대로 유지한다 | 두 포드 요금을 동시에 낸다. 잔액이 소진되면 3090 포드까지 정지될 수 있다(D13). 재고가 변한다. 정지하면 GPU를 다시 못 잡을 수 있다. terminate하면 볼륨이 삭제된다. 호스트 드라이버가 580 이상이어야 한다 |
| **C. 3090 + 저메모리 변형** | 후보: DaSiWa v2 int4(약 11.7GB, 출처: 검색 결과 요약, 미검증), Kijai `minimax_h3_ref2va_pruned_w4a8_mixed`(11,770,657,048 B, ComfyUI 0.31.0 이상), Abiray Pruned GGUF(8.9–21.6GB) | VRAM 여유 | 모두 실행 미검증. `server.py:62` 파일명과 그래프를 고쳐야 한다. 품질 차이 미검증 |

**A의 단점과 위험**

- VRAM이 24GB로 피크 31.9GB보다 작다. lowvram offload로만 가능하며 OOM과 저속 위험이 있다(미검증).
- RAM 62.0GB(=57.7GiB)를 공유한다. H3 가중치 약 35.9GB(33.5GiB, DiT 크기 추정 포함; 킷의 "33.4GB"는 GiB 값)를 RAM으로 오프로드하면, Forge가 유휴여도 약 48.5GB(78%)가 되어 listener의 80% 경고선에 다가간다(유휴 Forge 값은 이전 포드 관측 12.58GB 기준). Forge 배치(컨테이너 45.6–59.3GB)와 겹치면 62.0GB 상한을 넘는다(미검증). OOM killer의 대상이 될 수 있다.
- Ampere(sm_86)에서 int8 row-wise convrot / int4 convrot 커널이 동작하는지 미검증이다.
- listener와 Forge를 수동으로 멈춰야 한다.

**권장:** B.

- GPU는 48GB급(RTX A6000 / A40 / L40 / L40S / RTX 6000 Ada)을 우선한다.
- 32GB(RTX 5000 Ada, RTX 5090)는 헤드룸이 0.8GB뿐이다.
- 재고와 가격은 API 키가 없어 확인하지 못했다(미검증).
- 예산이 없으면 A를 "실험"으로만 한다. 동작한다는 보장은 없다.

**결과**

- 어느 쪽이든 `sydh2pm05u5rg2`는 정지하거나 편집하지 않는다(CLAUDE.md Pod Protection).
- B를 고르면 D13의 운영 정책이 필요하다.

### D3. ComfyUI 설치 방식 (D2=A일 때)

**선택지**

- A) 기존 `/workspace/ComfyUI`를 제자리에서 업그레이드한다.
- B) H3 전용 ComfyUI와 cu128 venv를 별도 경로에 설치한다. 모델 폴더는 `extra_model_paths.yaml`로 공유한다.

**권장:** B.

- 제자리 업그레이드는 기존 ComfyUI 사용을 깨뜨릴 위험이 있다(M7은 예정 작업이다. Anima가 이 포드에서 쓰였는지는 미검증이다).
- cuDNN `LD_LIBRARY_PATH` 우회(`R/project/RUNBOOK.md:24-27`)도 깨질 수 있다.
- 구버전 torch에서 comfy-kitchen import가 실패한 이력이 있다(`R/SETUP_HISTORY.md:38-41`).

**결과**

- 디스크가 더 필요하다(venv와 ComfyUI, 크기 미검증).
- 권장값
  - 경로 `/workspace/h3/comfy`. 경로에 `ComfyUI/main.py`가 들어가지 않게 해서 RUNBOOK의 `pkill -f "ComfyUI/main.py"`(`R/project/RUNBOOK.md:22`)에 걸리지 않게 한다.
  - 내부 포트 8190. 3000/3001/5000/7777/7860/8188/8189/8888/19123/22와 겹치지 않는다(포드 실측은 I7).
  - 기동: `cd /workspace/h3/comfy && setsid nohup env -u MPLBACKEND <venv>/bin/python main.py --listen 127.0.0.1 --port 8190 </dev/null >>/workspace/h3_mobile/logs/comfy.log 2>&1 &`. setsid가 없으면 Jupyter 커널에서 띄운 프로세스가 `auto_clean_kernels.py`의 커널 정리(`R/scripts/auto_clean_kernels.py:31-58`)에 휩쓸릴 수 있다(미검증).
- 설치 전에 `pip freeze` 스냅샷을 떠 둔다.
- 공유 안전 정책(구 D12): D3=B(전용 인스턴스)면 크래시 재시작, `/free unload_models`, interrupt를 모두 허용한다. 기존 ComfyUI와 공유하는 구성은 금지한다.

### D4. UI 노출 방식

UI는 루트 절대경로(`/api/*`, `/media/`, `/inputmedia/`, `/api/ws`)만 쓴다(`index.html:610, 627-765, 740`). 따라서 도메인 루트에서 서빙되어야 한다.

| 선택지 | 포드 변경 | 평가 |
|---|---|---|
| A. SSH 터널(`ssh -L`, 공인 SSH 포트 48031 경유). `server.py`는 127.0.0.1에 바인드 | 없음 | 가장 안전하다(Jupyter가 무인증으로 열려 있는 한 효과가 제한된다, D14). 휴대폰에 SSH 클라이언트가 필요하다 |
| B. cloudflared 터널 + 인증(Access 등) | 프로세스 추가 | 저장소에 외부 터널을 관찰한 기록이 있다(`R/chibi/README.md:3,95-97`, 인증이 필요하다는 경고 포함). 이 포드에 배포된 적은 없다. 인증은 필수다 |
| C. 이미 노출된 포트 재사용: 외부 8188(또는 7777)을 H3 UI에 주고 ComfyUI는 내부 포트로 옮긴다 | 기존 서비스의 포트 변경 | 기존 ComfyUI를 재기동해야 하고 외부 접근이 바뀐다. `COMFY_URL`과 재시작 스크립트를 고쳐야 한다. chibi 재현 구성(`R/chibi/README.md:87` `proxy_pass 127.0.0.1:8188`, 이 포드 배포 여부 미검증)을 쓰면 그 설정도 바꿔야 한다. G7에서 따로 승인받는다 |
| D. nginx :3000 하위 경로 | nginx 설정 | 지금 상태로는 불가능하다. `location /`가 Forge로 넘어가고(`R/config/nginx.conf:63-65`) UI는 루트 절대경로를 쓴다. `index.html`을 상대경로로 바꾸는 등 코드 수정이 있어야만 가능하다 |
| E. pod edit로 19123 포트 추가 | **컨테이너 재생성** | **금지(범위 밖).** `sydh2pm05u5rg2`에는 포트·환경변수·이미지·디스크를 바꾸는 pod edit를 하지 않는다. 필요하면 이 계획이 아니라 별도 위험 검토와 사용자의 명시적 승인 대상이다. (참고: `/var/spool/cron`, `/root/.config/rclone`, `/etc/nginx`가 사라지고 구버전 bootstrap을 다시 돌려야 한다 — `R/docs/RUNBOOK.md:174-182`(이전 포드), `R/config/README.md:24-25`) |
| F. (D2=B) 새 포드를 만들 때 ports에 포함 | 생성 시점 | edit가 필요 없다. 예: `19123/http,22/tcp`. Jupyter가 필요하면 토큰이나 비밀번호가 켜져 있는지 확인한 뒤에만 `8888/http`를 추가한다. **8188은 노출하지 않는다** — ComfyUI API는 인증이 없어 H3 UI 인증을 우회한다(`/prompt`, `/upload/image`, `/view`, `/history`, `/free`, `/interrupt`). 템플릿 `/start.sh`의 ComfyUI 기동 플래그와 기본 포트, Jupyter 인증 여부는 미검증이므로 생성 직후 확인한다(§10 단계 2) |

**권장**

- D2=A면 A를 쓰고, 필요할 때만 B. 단, D14 결론이 먼저다.
- D2=B면 F를 쓰고 인증 미들웨어(P0-8)를 붙인다.
- 팀원 등 제3자에게 공유하면 라이선스 V.2, V.5, III.3.a가 적용된다(D1, D15).

**공통 조건**

- 어떤 방식이든 인증 없이 프록시 URL을 노출하지 않는다.
- pod ID가 공개 저장소에 있다(`R/STATUS.md:9`, `R/project/HANDOFF.md:7`). 그래서 프록시 URL은 누구나 추측할 수 있다.

### D5. Forge 공존과 GPU·RAM 공유 정책 (D2=A일 때)

**사실**

- listener의 메모리 규칙
  - 컨테이너 메모리가 90% 이상이고 Forge가 유휴이면 Forge를 재시작한다. 쿨다운은 900초다.
  - 최근 5분 안에 재시작이 3번 있으면 그동안만 재시작을 거부한다. 5분 창이 지나면 다시 재시작하고 `restart_storm_stopped`도 False로 돌아간다. 따라서 Forge가 없는 환경에서는 재시작이 무기한 반복된다.
  - 근거: `R/listener/server.py:34-36, 207-220, 243-250, 288, 319-323, 331-332`.
  - H3가 쓰는 RAM도 여기에 합산된다. 그래서 메모리를 회수하지 못하는 Forge 재시작이 반복될 수 있다(미검증).
- Forge를 내려도 listener가 다시 띄운다. 5초 간격 2회 확인과 API 무응답이 조건이다(`:298-326`).
  - 먼저 `tmux kill-session -t listener`를 해야 한다(`R/listener/start.sh:4-5`).
  - 이는 "포드를 조작하는 주체는 listener 하나"라는 원칙(`R/docs/RUNBOOK.md:191`)과 충돌한다.
- 포드 crontab은 미검증이다. 포드 기록(커밋 `b9d6240` 메시지, `R/project/HANDOFF.md:43,59-63`, `R/project/STATUS.md:24`)은 clean_kernels·preventive_restart·watchdog·auto_restore·auto_backup 5종이며 listener `@reboot`는 없다. `R/STATUS.md:40-50`은 저장소가 의도한 구성이다. 포드에는 구버전 bootstrap이 남아 있다(`R/docs/OPERATIONAL_VERIFICATION.md:72`). 같은 커밋의 bootstrap 코드 자체는 4종(listener 포함)이라 기록끼리도 모순이다.
  - Forge watchdog 루프(`R/scripts/watchdog.sh:10-19`)가 돌면 Forge를 멈춰도 약 15초 안에 `pkill -9` 후 다시 띄운다. preventive_restart(`R/scripts/preventive_restart.py:26-47`)는 유휴 Forge를 5시간마다 재시작한다.
- ComfyUI를 공유하면 `server.py`가 다른 사용자의 작업에 영향을 준다.
  - OOM 후 `/free`를 `unload_models:true`로 호출한다(`server.py:437-438`).
  - 취소할 때 전역 `/interrupt`를 반복해서 보낸다(`server.py:413-419, 590-594`).

**선택지**

- A) 배타적 시간창: H3 작업 중에는 listener와 Forge를 멈추고, 끝나면 되살린다.
- B) 동시 운용: OOM 위험을 받아들인다.
- C) H3 전용 ComfyUI를 두되, Forge가 유휴일 때만 작업한다.

**권장**

- A. 시간창과 절차는 사용자가 명시적으로 승인한다.
- H3 ComfyUI는 전용 인스턴스로 두고, 큐를 공유하지 않는다.
- listener 메모리 임계치에 H3 예외를 둘지는 따로 결정한다.

**결과**

- Forge 배치 일정과 부딪힌다.
- 시간창마다 서비스를 멈추므로 매번 승인 게이트를 거친다.

### D6. 텍스트 인코더와 VAE 변형

| 후보 | 크기(B) | 평가 |
|---|---|---|
| `qwen3vl_32b_minimax_h3_int4_convrot` (Abiray) | 14,952,506,709 | 킷 기본값(`server.py:63`). 필요한 최소 ComfyUI 버전은 명시되어 있지 않다(미검증) |
| `qwen3vl_32b_minimax_h3_nvfp4_awq` (Comfy-Org) | 15,687,142,551 | Blackwell이 아니어도 동작하지만 속도 이득이 없다(Comfy README L25, `models.txt:22`). D2=B에서 RTX 5090을 고르면 고려할 만하다 |
| Abiray의 같은 이름 nvfp4 파일 | 27,141,342,223 | 크기가 Comfy-Org `qwen3vl_32b_minimax_h3_int8_convrot` 텍스트 인코더(27,141,342,152 B, HF API `size`)와 71 B 차이라 라벨 오류로 보인다(미검증). **사용 금지** |

- **Video VAE는 Comfy-Org fp16(5,207,808,496 B)으로 확정한다.**
  - Abiray의 fp16 사본은 다른 blob이다(5,207,808,557 B). 섞어 쓰지 않는다.
  - int8(Kijai판, Comfy-Org 신규판)은 둘 다 받지 않는다.
- **권장:** int4_convrot + fp16 VAE. 킷 기본값 그대로다.

### D7. 메인 DiT 출처

| 선택지 | 평가 |
|---|---|
| A. Civitai `models/3314686?fileId=3203135` (킷 기본) | 토큰이 필요하다. 조사 환경에서는 civitai.com이 egress 403으로 막혀 이름·크기·sha256·early access(유료·기간 한정 공개) 여부·라이선스를 확인하지 못했다. CivArchive 검색 결과 요약에 따르면(미검증, civarchive.com 차단) 3314675가 "DaSiWa Hybrid v2"(int8 19.5GB)다. 3314686과의 관계는 미확인이다 |
| B. HF `brurpo/DaSiWa-MiniMax-H3-Hybrid` | v1 4-step과 8-step 파일만 있다(각 20,967,642,441 B). 제3자 미러다. 파일명이 달라 `server.py:62`를 고쳐야 한다 |
| C. Comfy-Org 공식 pruned int8_convrot FL2VA/REF2VA | hybrid나 turbo가 아니다. turbo LoRA와 슬롯별 모델이 필요하고 그래프도 고쳐야 한다 |

**권장:** A. 사용자가 Civitai 페이지에서 파일의 sha256을 확인해 알려 주면(§4 I4), 다운로드 후 그 값으로 검증한다.

### D8. 선택 모델

| 모델 | 모바일 UI에서 사용 | 상태 | 권장 |
|---|---|---|---|
| 잠재 업스케일러 bf16 | 사용 안 함 | 기존 URL은 404이고 새 경로는 정상(690,592,992 B). 커스텀 노드 `LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler`가 필요한데 설치 목록에 없다 | 생략 |
| taeh3 (TAE 미리보기) | 사용 안 함 | 9,791,388 B. KJNodes의 `ModelPreviewOverride`가 필요하다 | stock 워크플로를 쓸 때만 |
| 2x-AnimeSharpV4_RCAN | 사용 안 함 | openmodeldb가 차단되어 형식·라이선스·크기 미검증. 포드의 `upscale_models`가 Forge ESRGAN 폴더로 가는 심볼릭 링크인지는 미검증이다(계획 `R/project/AGENT_CLAUDE.md:68-71`, 이전 포드 `R/SETUP_HISTORY.md:29-30`). 링크라면 파일이 Forge 쪽에 들어간다. `ls -l /workspace/ComfyUI/models/`로 확인 | 생략 |
| RIFE / FILM (frame_interpolation) | 사용 안 함 | 파일 6개 가운데 워크플로가 어떤 것을 쓰는지 미검증 | 생략. 필요하면 파일명을 지정한다 |

**권장:** 모바일 UI가 목적이면 모두 생략한다. ComfyUI 탭에서 stock 워크플로를 쓰려면 항목별로 지정한다.

### D9. 공개 저장소 커밋 여부와 위치

**선택지**

- A) 커밋하지 않는다. 스크래치패드나 비공개로 보관한다.
- B) 정화본을 공개 `castle923/AutoRunpod`의 전용 디렉터리에 커밋한다. 디렉터리 이름(예: `h3_mobile/`)은 미정이다.
- C) 비공개 `castle923/Runpod-Backup`에만 둔다.

**권장:** C(비공개 `castle923/Runpod-Backup`).

- 공개 저장소에는 비밀이 없는 한 줄 요약만 둔다. 노출 URL, 포트, 인증 방식은 적지 않는다.
- 킷 원본, 정화 전 스크립트, 취약점 재현 하니스는 공개 저장소에 두지 않는다. 이 요구사항 문서에는 비밀값이 없고, 킷은 아직 사용자 포드에 배포되지 않았다. 따라서 취약점 설명은 수정 요청 목적으로만 둔다. 킷을 배포한 뒤 문서를 갱신할 때는 노출 URL·포트·인증 방식을 적지 않는다(pod ID는 공개 — `R/STATUS.md:9`).
- 킷 zip에 LICENSE 파일이 없다. 저작자와 라이선스를 확인하기 전에는 공개 재배포하지 않는다.

B를 굳이 고른다면 다음 조건을 지킨다.

- 토큰을 지우고, 토큰 변수는 `:?` 형식으로 필수화한다.
- 경로를 환경변수로 바꾼다.
- 커밋 전에 토큰을 grep해서 0건인지 확인한다.
- 원본 zip과 스크래치 원본은 커밋하지 않는다. 한 번 들어가면 히스토리를 다시 써야 한다.
- 저장소 선례: `R/scripts/hfdown.sh:4-5,21`은 HF 토큰을 `<YOUR_HF_TOKEN>` placeholder로 바꿨다.

**결과:** 공개 저장소 커밋은 되돌리기 어렵다. 그래서 승인 게이트를 둔다.

### D10. 백업 정책

**현황**

- auto_backup은 30분마다 돈다. 목적지는 `gdrive:런포드 백업/workspace_snapshot`이다(`R/scripts/auto_backup_workspace.sh:17,33-37,44,51-52`).
  - 올라가는 것: `/workspace` 루트의 *.sh/py/txt/json/md/ipynb, `/workspace/scripts/`, 최근 24시간 로그.
  - 그래서 킷 README가 루트로 복사하라는 `restart_comfy.sh`와 `mobile_start.sh`가 자동으로 올라간다.
  - 킷 기본값대로면 로그 `h3_mobile.log`, `comfyui.log`, `watchdog.log`가 `/workspace/logs`에 쓰여(`start.sh:9`, `restart_comfy.sh:45`, README:44) 첫 기동 후 30분 안에, 즉 G9보다 먼저 올라간다. 로그 내용은 주로 기동 배너와 트레이스백이다(`server.py`에 print/logging 호출 없음, 미검증).
  - 대책: H3 로그와 스크립트는 모두 `/workspace/h3_mobile/` 아래에 둔다(P0-14, P2-9).
- 올라가지 않는 것: 모델 43GB, H3 출력, `/workspace/h3_mobile/`(`jobs.json` 포함 — `server.py:26-27`).
- 포드의 `/workspace/scripts/hfdown.sh`에 든 HF 토큰(`R/project/HANDOFF.md:58`)은 이미 30분마다 Drive 스냅샷으로 올라가고 있을 수 있다(`R/scripts/auto_backup_workspace.sh:44`, 킷과 별개, §12.2).
- auto_restore는 Forge 자산만 복원한다. 포드를 terminate하면 H3 모델을 다시 받아야 하고 토큰도 다시 필요하다.
- 이 경로로 올릴 때 quota 403 오류가 난 전례가 있다(`R/docs/OPERATIONAL_VERIFICATION.md:62-68`).

**선택지**

- 모델: A) 백업하지 않고 필요할 때 다시 받는다. B) Drive에 백업한다.
- 출력: A) 백업하지 않는다. B) 고정 경로(예: `gdrive:런포드 백업/h3_outputs/`)로 `rclone copy`만 쓴다. `sync`는 금지한다.

**권장**

- 모델은 A.
- 출력은 필요할 때만 B로 하며, 사용자 승인을 받는다.
- `jobs.json`(프롬프트 전체 포함)은 킷을 `/workspace/h3_mobile/`에 두는 한 업로드되지 않는다. 킷을 루트나 `/workspace/scripts`로 옮기지 않는다는 조건만 유지한다.
- H3 로그는 `/workspace/h3_mobile/logs/`에 두어 업로드 대상에서 뺀다(P0-14).

**절대 조건**

- 4팀 공유 드라이브(ID `1rId_zhT9twxCTK8Y9QA2q94-mrMH5mm-`)는 기본적으로 제외한다. 꼭 필요하면 CLAUDE.md의 절차(목적 확인, 파일 목록·크기, 경로 제시 후 "승인")를 건별로 거친다. 자동 동기화는 금지한다.
- 새로 만드는 스크립트에는 "4팀" 문자열과 이 ID를 거부하는 검사를 넣는다.
- 문자열 검사로는 rclone remote 루트 자체가 4팀 폴더이거나 그 안을 가리키는 경우(`root_folder_id`, `shared_with_me`, `team_drive`, 바로가기)를 막지 못한다. `런포드 백업`의 Drive 내 위치도 미검증이다. 그래서 Drive 쓰기 전에 I7의 rclone 키 확인(로컬 설정만, Drive 접근 없음)을 거친다. `root_folder_id`가 위 ID이거나 `shared_with_me=true`이면 모든 Drive 쓰기를 중단하고 보고한다.
- 상위 폴더를 대상으로 하는 sync는 금지한다.

### D11. 자동 기동

**선택지**

- A) 수동으로 기동한다.
- B) crontab `@reboot`에 H3 ComfyUI, `mobile_start`, `watchdog`을 등록한다. 선례는 `R/scripts/bootstrap_pod.sh:318-319`다.

**권장:** 안정화를 확인한 뒤 B. 컨테이너가 다시 만들어지면 crontab이 사라진다는 점(`R/docs/RUNBOOK.md:174-182`)은 감수한다.

**결과**

- 포드 crontab 변경은 승인 게이트를 거친다.
- D2=B 포드에서는 `bootstrap_pod.sh`와 `new_pod_generate.sh`(Forge 전용)를 실행하지 않는다. 실행하면 다음이 일어난다(`:283-295`, `:337-343`).
  - nginx 설정을 덮어쓴다.
  - listener가 없는 Forge를 무기한 재시작한다(storm 가드는 5분 창 동안만 거부한다, D5).
  - 149GB LoRA 복원이 시작된다.

### D12. 공유 ComfyUI 안전 정책 → D3에 통합

- 결론(D3 "공유 안전 정책"): 전용 인스턴스에서는 (a) 크래시 재시작, (b) OOM 뒤 `/free unload_models`, (c) interrupt를 모두 허용한다. 기존 ComfyUI와 공유하는 구성은 금지한다.
- 스크립트를 고치기 전에는 자동 재시작을 끈다. 1차 수단: README:30의 복사 단계를 수행하지 않는다(P2-9와 일치). 기본 경로 `/workspace/restart_comfy.sh`가 없으면 `server.py:350-351`이 재시작을 건너뛴다. 보조 수단: `RESTART_COMFY`를 존재하지 않는 경로로 export(모든 기동 경로에서 export해야 한다 — `start.sh:49`, `watchdog.sh:26`은 환경을 상속할 뿐이다).

### D13. 새 포드 운영 정책 (D2=B일 때)

**결정할 것**

- GPU 종류
- 시간당 예산 상한
- 볼륨 크기(100GB 이상)
- 사용 후 처리: stop, terminate, 상시 유지 중 하나
- 데이터센터 지역(D1과 연동)

**권장**

- 48GB급 GPU(D2), 시스템 RAM 62GB 이상(킷 검증값, 30GB는 부족 — `README.md:7,58-59`), 컨테이너 디스크 30GB 이상, 볼륨 100GB, 호스트 드라이버 580 이상, `--cloud-type COMMUNITY`, `--dry-run` 출력 승인 후 생성.
- 사용 후 처리의 기본값은 stop이며, terminate는 G10에서 따로 승인받는다.
- 잔액: 승인 전에 RunPod 잔액을 확인한다. 잔액은 (0.22 + 신규 포드 시급) × 계획 사용시간에 3090 단독 운용 7일분(0.22 × 168 ≈ $37)을 더한 값 이상이어야 한다. 신규 포드는 종료 시각을 미리 정하고, 그 시각에 stop 또는 terminate를 승인받는다. "RunPod 잔여 시간" Routine(`R/MONITORING_ROUTINES.md:52-54`)이 두 포드의 합산 소비율로 계산하는지 확인한다. (RunPod은 잔액이 소진되면 모든 포드를 정지한다 — 외부 지식, 미검증. 그러면 `sydh2pm05u5rg2`도 멈춘다.)

**참고: 재고 이력**

- 정지하면 같은 GPU를 다시 못 잡을 수 있다.
  - 4090 품절로 3090으로 대체했다(`R/project/STATUS.md:28`).
  - 4080S는 매물이 없었다(`R/docs/RUNBOOK.md:186-187`).
  - 재고가 낮으면 resume이 실패한다(`R/README.md:121`).
  - 공인 IP가 잡히지 않는 호스트가 있었다(`R/SETUP_HISTORY.md:44`).
- terminate하면 볼륨이 삭제된다.

**`runpod_create_pod.py`를 그대로 쓰면 안 되는 이유**

| 위치 | 문제 | 조치 |
|---|---|---|
| `:106-111` | `cloudType` 기본값이 ALL | `--cloud-type COMMUNITY`를 반드시 명시 |
| `:75-78` | `--gpu-type` 기본값이 RTX 4080 SUPER | D13에서 고른 GPU를 명시 |
| `:101-105` (`:15-17`) | 데이터센터 미지정(any) | D1 판단에 따라 `--data-center-id`로 지역을 명시하고, 생성 후 지역을 기록 |
| `:113-116` | 포트 기본값이 `8888/http,22/tcp` | D4-F 포트를 지정(8188 제외) |
| `:96` | 볼륨 기본값 50GB | 100GB 이상으로 지정 |
| `:98` | 컨테이너 디스크 기본값 20GB | 30GB 이상 지정 |
| — | 최소 RAM과 CUDA 버전 필터가 없음 | 수동으로 확인 |
| `:117-123` | `--env KEY=VALUE`가 argv와 포드 설정에 값을 남김 | 토큰 전달에 쓰지 않는다(I3) |
| `:50`, `:124-128` | API 키를 URL 쿼리(`?api_key=`)로 보내고 `--api-key` argv도 받음 | `--api-key` 인자는 쓰지 않는다. `?api_key=`는 `Authorization: Bearer` 헤더로 바꾼다(I6b) |

### D14. 기존 포드 노출 포트 보호 — 차단(§0 #6)

**사실:** §0 #6. 현 포드 8888/8188/7777은 공개 프록시로 노출되어 있었다(`R/project/HANDOFF.md:18-22`). ComfyUI API(8188)도 인증이 없다(`R/chibi/HANDOFF_CODEX.md:201`의 경고와 같은 구조).

**선택지**

- A) Jupyter에 토큰이나 비밀번호를 적용한다. `R/scripts/jupyter_exec.py`와 `R/scripts/auto_clean_kernels.py`(`:15-18`)도 함께 고쳐야 한다. Jupyter 재기동은 원격 제어 채널을 끊을 수 있으므로 SSH 48031 접속을 먼저 확인하고 별도 게이트 **[G0]**를 거친다.
- B) 위험을 수용한다. 이 경우 Civitai 토큰은 이 다운로드 전용으로 발급하고 DiT sha256 검증 직후 폐기한다.

**권장:** 먼저 I5/I7로 현 포드 Jupyter 인증 여부를 확인한다. 무인증이면 A. 어느 쪽이든 새 토큰은 사용 직후 폐기한다.

### D15. UI 사용자 범위

- 선택지: A) 본인만, B) 팀 등 제3자 포함.
- **권장:** A. B를 고르면 라이선스 V.2/V.5/III.3.a 의무(D1)와 사용자별 인증, 취소·interrupt 권한 설계가 필요하다.

### D16. H3 ComfyUI 버전

- 킷은 0.30.0에서 검증했다(`README.md:6`). 대안 모델은 0.31.0 이상(Kijai w4a8), int8 VAE 최고 속도는 0.36.0(Kijai README L7)을 요구한다.
- **권장:** 킷이 검증한 0.30.0으로 고정한다(해당 태그 존재 여부는 미검증). 업그레이드는 따로 검증한다.

### D17. 포드 명령 실행 주체와 채널

- `R/scripts/jupyter_exec.py:23`의 기본 pod ID는 이전 포드(`xyru66nh4emucs`)이고 `RUNPOD_POD_ID`를 읽는다. `R/docs/RUNBOOK.md:47`의 `POD_ID=...`는 스크립트가 무시한다.
- **권장:** Claude가 명령 전문을 준비해 제시하고 승인받은 뒤 실행한다. jupyter_exec를 쓸 때는 `RUNPOD_POD_ID=sydh2pm05u5rg2`를 반드시 명시한다. 토큰 입력 단계(I3)는 사용자가 SSH에서 직접 한다.

---

## 4. 사용자 제공 필요 항목

| # | 항목 | 전달 방식 | 용도 | 관련 |
|---|---|---|---|---|
| I1 | D1 라이선스 판단 결과 | 대화 | 진행 여부 결정 | D1 |
| I2 | 유출된 Civitai 토큰의 소유자 확인과 폐기 완료 통보 | 대화. 값은 적지 않는다 | 유출 대응. 소유자가 사용자가 아닐 수 있다(미검증) | §9 |
| I3 | **새로 발급한** Civitai 토큰(이 다운로드 전용, DiT sha256 검증 직후 폐기) | `CIVITAI_TOKEN` 환경변수로만 전달(아래 "I3 전달 경로"). 명령행 인자, 파일 커밋, 채팅 붙여넣기 금지 | DiT 다운로드 | P0-1, D14 |
| I4 | Civitai 모델 파일 정보: 파일명, 크기, sha256, early access(유료·기간 한정 공개) 여부 | Civitai 페이지에서 확인해 전달 | 무결성 검증 | D7 |
| I5 | `sydh2pm05u5rg2`의 콘솔 상태: RUNNING 여부, 노출 포트 목록, 데이터센터 국가, Jupyter 인증 설정 | 대화 | 프록시 404 원인 확인, D1·D4·D14 | §0 |
| I6a | 읽기 전용 권한의 `RUNPOD_API_KEY` | 환경변수로만 전달. `--api-key` 인자 금지 | 조회만(포트, 재고, 잔액). RunPod 키 권한 구분은 외부 지식이며 미검증 | D2, D13 |
| I6b | (D2=B 승인 후에만) 생성 권한 | 권장: 사용자가 콘솔에서 직접 만들고 pod ID만 전달. 스크립트를 쓰면 `--dry-run` 출력을 제시하고 승인받은 뒤 실행 | 허용 mutation은 `podFindAndDeployOnDemand` 1회뿐. `sydh2pm05u5rg2` 대상 `podStop`/`podTerminate`/`podEditJob`/`podResume`/`podReset`은 어떤 경우에도 호출하지 않는다 | D13 |
| I7 | 포드 읽기 전용 명령 출력(아래) | 대화. 출력에 토큰이 보이면 가려서 전달 | 환경 확인 | §5 |
| I8 | D2=B일 때: GPU 선호, 시간당 예산 상한, 사용 후 정책 | 대화 | 포드 생성 | D13 |
| I9 | D2=A일 때: Forge와 listener를 멈춰도 되는 시간창 | 대화 | 공존 | D5 |
| I10 | 접근 방식과 인증 수단: SSH 키 사용 여부, 인증 토큰이나 비밀번호를 누가 만들지 | 인증값은 환경변수로만 전달 | 외부 노출 | D4 |
| I11 | 출력 백업 여부와 허용 경로. 4팀 공유 드라이브는 제외 | 대화와 명시적 승인 | 백업 | D10 |
| I12 | 저장소 커밋 여부와 위치 | 대화 | 공개 저장소 | D9 |

**I3 전달 경로**

- D2=A: 사용자가 SSH(48031)나 터미널에서 같은 셸로 `read -rs CIVITAI_TOKEN && export CIVITAI_TOKEN && bash /workspace/h3_mobile/download_models.sh`를 실행한다. 값이 명령행과 히스토리에 남지 않는다.
- **RunPod 콘솔에서 Pod 환경변수를 편집하는 것은 pod edit(컨테이너 재생성)이므로 `sydh2pm05u5rg2`에서 금지한다**(재생성 여부는 킷 `README.md:49-51`의 포트 edit 기록에서 유추, 외부 지식).
- D2=B: 같은 `read -rs` 방식을 쓰거나 RunPod Secret 참조를 쓴다(미검증). `runpod_create_pod.py --env CIVITAI_TOKEN=…`는 금지한다(`R/scripts/runpod_create_pod.py:117-123`).
- D14가 B(Jupyter 무인증 수용)이면, 다운로드 중에는 환경변수가 코드 실행 권한을 가진 누구에게나 보인다는 점을 감수한다.

**I7 명령(모두 읽기 전용)**

```
df -h /workspace /
ionice -c3 du -sh --max-depth=1 /workspace    # Forge 유휴일 때만
crontab -l
tmux ls
ps -eo pid,args | grep -E 'main.py|launch.py|server.py|watchdog.sh|preventive_restart'
ls -la /workspace/restart_comfy.sh /workspace/mobile_start.sh /workspace/start_comfyui.sh
git -C /workspace/ComfyUI describe --tags --always
curl -s localhost:8188/system_stats
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8888/api/kernels   # 토큰 없이 200이면 무인증(D14)
rclone config show gdrive | grep -E '^(type|root_folder_id|team_drive|shared_with_me) '   # token 줄 제외, Drive 접근 없음
which ffmpeg
nvidia-smi
```

- `ls -la /workspace/restart_comfy.sh`는 `server.py:30`의 `RESTART_COMFY` 기본 경로와 이름이 겹치는 파일이 이미 있는지 확인하기 위해서다.

- `ps` 출력에는 다른 프로세스의 인자가 섞일 수 있다. 토큰이 보이면 가린다. 예를 들어 포드에 있는 `hfdown.sh` 사본에는 HF 토큰이 들어 있다(`R/project/HANDOFF.md:58`).
- 추가로 알려 줄 것
  - `/workspace/start_comfyui.sh`의 내용(저장소에 없다)
  - ComfyUI `/object_info`에서 `CLIPLoader`의 `type` 옵션에 `minimax`가 있는지

---

## 5. 환경 요구사항 vs 현재 포드 비교

| 항목 | 킷 요구 / 검증 환경 | 현재 포드 `sydh2pm05u5rg2` | 판정 | 근거 |
|---|---|---|---|---|
| GPU / VRAM | 32GB 이상. 검증은 RTX 5000 Ada 32GB, 피크 31.9/32.7GB | RTX 3090 24GB, Forge와 공유 | **불충족** | `K/README.md:6-7,24,56-59`; `R/project/HANDOFF.md:9` |
| 아키텍처 | Ada에서 검증. NVFP4 TE는 Blackwell에서만 이득 | Ampere sm_86. int8 row-wise convrot / int4 convrot 커널이 동작하는지 모른다. `fp8_e4m3fn_fast`는 이득이 없다(외부 지식: sm_86에는 FP8 텐서 코어가 없다. 미검증) | 미검증 | `models.txt:22-23` |
| 시스템 RAM | 62GB에서 검증. 30GB로는 부족 | cgroup 62.0GB(=57.7GiB). 현재 포드 관측: 배치 중 컨테이너 45.57GB(73.5%), 피크 95.6%(약 59.3GB). 참고(이전 4080S 포드 `xyru66nh4emucs`): OOM 시 Forge RSS 14.2GB, 재시작 후 컨테이너 12.58GB | **위험** | `README.md:7,58-59`; `R/project/HANDOFF.md:32`; `R/docs/OPERATIONAL_VERIFICATION.md:22-24`; 이전 포드 `R/docs/OPERATIONS_LOG_2026-09-16.md:3,36,62` |
| 볼륨 디스크 | 모델 42.44GB + `.part` + venv + 출력(진행 기준은 §6.2) | 300GB. 알려진 사용량 약 159GB(LoRA 149 + 체크포인트 6.9 + 배치 zip 2.85), 여유는 최대 약 141GB. hfdown 대상 약 78GB(`R/project/STATUS.md:23`)를 받았는지 확인되지 않았다. 받았다면 여유가 약 63GB까지 줄 수 있다. venv, Forge, 출력은 포함하지 않았다 | 미검증(I7의 df/du로 확정) | `R/project/HANDOFF.md:31`; `R/project/STATUS.md:9`; `R/STATUS.md:20-22,57-59` |
| 컨테이너 디스크 | pip 캐시 공간 | 미검증. 이전 포드는 40GB였다 | 미검증. `--no-cache-dir` 사용 | 이전 포드 `R/docs/OPERATIONS_LOG_2026-09-16.md:14` |
| 이미지 / CUDA | `runpod/comfyui:1.4.7-cuda13.0`, `.venv-cu128` | 계획상 `runpod/forge:3.3.0`(실제는 미검증). 컨테이너 CUDA 12.1 | 불일치 | `README.md:6`; `R/project/AGENT_CLAUDE.md:21`; `R/project/HANDOFF.md:27` |
| 드라이버 | cu128/cu130 wheel | 580.65.06. CUDA 13.0 최소 드라이버를 충족한다(외부 지식) | 충족. 새 포드는 호스트 드라이버 580 이상 필요(570에서 실패한 전례) | `R/project/HANDOFF.md:28`; `R/SETUP_HISTORY.md:38` |
| torch | cu128 계열. 버전은 명시되지 않음. Comfy-Org README L27은 int8_convrot DiT에 torch cu130을 권장한다(fp8_scaled는 대안, L29) | ComfyUI venv 2.5.1+cu121, system 2.4.0+cu121 | 업그레이드가 필요할 가능성이 있다(미검증). 드라이버 580.65.06은 CUDA 13.0 최소 요건과 같은 값이라 cu130 wheel을 쓸 수 있을 것으로 본다(미검증) | `R/project/HANDOFF.md:28-30`; `https://huggingface.co/Comfy-Org/MiniMax-H3` README L27, L29 |
| Python | 템플릿 기본값(기재 없음) | 3.10.12 | 호환 여부 미검증 | `R/project/HANDOFF.md:26` |
| ComfyUI 버전 | 0.30.0. 노드 2개가 없다 | 미검증. 설치 시점 약 2026-09-20T17:40Z. 브랜치·커밋 기록 없음 | 미검증(I7 `git describe`). `CLIPLoader` `minimax`, `SaveVideo` / `CreateVideo` / `VAEDecodeAudio`, NestedTensor 지원이 필요하다 | `README.md:6,79,86-88`; `R/project/STATUS.md:26` |
| ComfyUI 경로 | `/workspace/runpod-slim/ComfyUI` | `/workspace/ComfyUI` | **불일치** | `server.py:23`; `R/project/RUNBOOK.md:28-30`; `R/project/HANDOFF.md:39` |
| venv | `$C/.venv-cu128` | `/workspace/venvs/comfyui` (ComfyUI 디렉터리 밖) | **불일치** | `start.sh:6`; `R/project/HANDOFF.md:39` |
| ComfyUI 기동 명령 | `main.py --listen 0.0.0.0 --port 8188 --enable-cors-header` | `LD_LIBRARY_PATH` cuDNN 우회 후 `nohup python3 main.py --listen 0.0.0.0 --port 8188` | 킷의 kill 패턴과 일치해서 **위험** | `restart_comfy.sh:21,43-45`; `R/project/RUNBOOK.md:24-30` |
| ComfyUI 가동 여부 | — | 최신 기록(`R/project/HANDOFF.md:19,39`; `R/project/STATUS.md:26`, 2026-09-20)상으로는 설치·가동. `R/SETUP_HISTORY.md:33-34`("미복원")는 2026-09-03 작성으로 현 포드 생성(09-20) 이전의 기록이다(stale). 현재 가동 여부는 미검증(09-22 관찰 `R/docs/OPERATIONAL_VERIFICATION.md:16-24`에 8188 항목 없음, 09-23 프록시 404) | 미검증 | |
| 포트 | 19123. 템플릿 기본 목록에 있다고 주장하지만 미검증 | 서비스 목록: 3000, 8188, 8888, 7777(외부), 5000(listener, 내부), 22(공인 48031). 포드의 실제 노출 포트 설정은 미검증(I5). Forge 내부 포트: 3001(`R/listener/server.py:17`, `R/config/nginx.conf:65`)과 7860(`R/project/RUNBOOK.md:9`)이 불일치한다(미검증) | **불충족 가능성**(미검증) | `README.md:47-52`; `R/project/HANDOFF.md:15-22` |
| ffmpeg | stock 워크플로와 검증에 필요. 킷은 "video output needs it"라고 한다. `server.py`가 직접 쓰지 않고 ComfyUI가 PyAV로 인코딩한다는 판단은 미검증(외부 지식) | 미검증 | 미검증. 설치 요구로 유지(§11 volumedetect에도 필요) | `install_nodes.sh:31`; `models.txt:74`; `server.py:240-244` |
| 자동 기동 | 템플릿 `/start.sh`가 한 번 실행한 뒤 `sleep infinity` | 미검증. 포드 기록(커밋 `b9d6240` 메시지, `R/project/HANDOFF.md:43,59-63`)은 clean_kernels·preventive_restart·watchdog·auto_restore·auto_backup 5종이며 listener `@reboot`는 없다. `R/STATUS.md:40-50`은 저장소가 의도한 구성이다. 포드에는 구버전 bootstrap이 남아 있다(`R/docs/OPERATIONAL_VERIFICATION.md:72`). ComfyUI 항목은 어느 기록에도 없다 | 추가가 필요하면 D11. 확인은 I7 `crontab -l` | `server.py:347-349` |
| 셸 실행 환경 | Jupyter exec용 우회(`setsid`, `env -u MPLBACKEND`) | `R/scripts/jupyter_exec.py` 사용 | 적합 | `start.sh:46-49` |

**성능 기준**(`README.md:61-63`, 32GB 카드, 모델 상주, 6 turbo steps)

| 해상도 | 소요 시간 |
|---|---|
| 640×384 | 약 12초 |
| 480×608 | 약 14초 |
| 1280×736 | 약 48초 (5.0 s/step) |

- 세션의 첫 작업에는 모델 스테이징이 약 20초 더 붙는다.
- 608×800에 10초 길이는 18.7 s/step이 걸렸다. 길이가 해상도보다 훨씬 비싸다.
- 3090에서는 이보다 느릴 것으로 예상한다(미검증).
- 해상도는 가로·세로 모두 32의 배수여야 한다(`README.md:73-77`).

---

## 6. 모델 목록 (검증 결과 반영)

- 대상 경로의 기준은 `$COMFY_ROOT/models/`다.
- 크기 검증값은 HF HEAD 요청의 `x-linked-size`이고, sha256은 `x-linked-etag`로 HF API `lfs.sha256`과 일치한다. 2026-09-23 17:1xZ 재확인에서 모두 일치했다.
- GB = 10^9 B, GiB = 2^30 B.
- 라이선스: #1 미검증(Civitai 필드), #2·#2a·#3·#4는 HF 메타데이터상 `minimax-h3-community-license-agreement`(D1). #5·#6·#8은 비고 참조.

| # | 용도 | 파일명 | 대상 경로 | 크기(검증값) | 필수/선택 | 출처 URL | 비고 |
|---|---|---|---|---|---|---|---|
| 1 | DiT (FL2VA와 REF2VA 겸용 hybrid turbo) | `dasiwa_minimax_h3_ref2va_v2_pruned_hybrid_turbo_int8_row-wise_convrot_runtime_mixed.safetensors` | `diffusion_models/MiniMaxH3/` | **미검증**. 킷 표기 19.53(GiB로 추정, 약 20.97e9 B) | 필수 | `https://civitai.com/api/download/models/3314686?fileId=3203135` | 토큰 필요. Civitai 제공명에서 이름을 바꿔 저장한다(`models.txt:12`). `server.py:62` 하드코딩 |
| 2 | 텍스트 인코더 | `qwen3vl_32b_minimax_h3_int4_convrot.safetensors` | `text_encoders/` | 14,952,506,709 B (14.953GB / 13.926GiB) | 필수 | `https://huggingface.co/Abiray/MiniMax-H3-GGUF/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_int4_convrot.safetensors` | `server.py:63` |
| 2a | 텍스트 인코더 대안 | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `text_encoders/` | 15,687,142,551 B | 대안(D6) | `https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | 3090에서는 이득 없음. Abiray의 같은 이름 파일은 사용 금지 |
| 3 | Video VAE | `minimax_h3_video_vae_fp16.safetensors` | `vae/MiniMaxH3/` | 5,207,808,496 B (5.208GB / 4.850GiB) | 필수 | `https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors` | `server.py:64`. Abiray 사본(다른 blob)과 섞어 쓰지 않는다 |
| 3x | Video VAE int8 | `minimax_h3_video_vae_int8_convrot.safetensors` | — | 3,171,670,912 B (Kijai) | **받지 않음** | `https://huggingface.co/Kijai/MiniMax-H3-experimental/resolve/main/minimax_h3_video_vae_int8_convrot.safetensors` | 킷에 따르면 검은 화면이 나온다. U의 기본값이지만 구버전 정보 |
| 4 | Audio VAE | `minimax_h3_audio_vae_fp32.safetensors` | `vae/MiniMaxH3/` | 605,254,808 B (0.605GB / 0.564GiB) | 필수 | `https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_audio_vae_fp32.safetensors` | `server.py:65`. REF2VA와 오디오에 필요 |
| 5 | 잠재 업스케일러 bf16 | 로컬 저장 이름: `minimax_h3_latent_upscaler_3d_bf16.safetensors` | `latent_upscale_models/` | 690,592,992 B | 선택(D8) | 새 경로: `https://huggingface.co/LBH-123-AI/Minimax_h3_latent_Upscaler/resolve/main/minimax_h3_latent_upscaler_3d_conv_v1/minimax_h3_latent_upscaler_3d_conv_v1_bf16.safetensors` | 기존 URL(`download_models.sh:36`)은 404. 대안으로 리비전 `13ccf95d85d120bdbc92c05b1247a6e147bf54bf`에 고정하면 옛 경로도 동작한다. 커스텀 노드가 추가로 필요하다. apache-2.0 |
| 6 | TAE 미리보기 | `taeh3.safetensors` | `vae_approx/` | 9,791,388 B | 킷은 필수로 표기. 모바일 UI는 쓰지 않는다 | `https://huggingface.co/Kijai/MiniMax-H3-TAE/resolve/main/vae_approx/taeh3.safetensors` | KJNodes `ModelPreviewOverride` 전용. apache-2.0 |
| 7 | 2x-AnimeSharpV4_RCAN | 미검증 | `upscale_models/` (Forge ESRGAN 폴더로 가는 심볼릭 링크인지 미검증, D8) | 미검증 | 선택(D8) | `https://openmodeldb.info/` ("AnimeSharpV4" 검색) | 차단되어 형식·라이선스를 확인하지 못했다. 스크립트가 받지 않는다 |
| 8 | 프레임 보간 | `film_net_fp16` 68,882,302 B / `rife_v4.25` 22,674,688 B / `rife_v4.25_heavy` 86,669,816 B / `rife_v4.25_lite` 22,506,384 B / `rife_v4.26` 22,674,688 B / `rife_v4.26_heavy` 22,908,216 B (모두 `.safetensors`) | `frame_interpolation/` (스크립트가 폴더를 만들지 않는다) | 6개 합계 246,316,094 B | 선택(D8) | `https://huggingface.co/Comfy-Org/frame_interpolation/resolve/main/frame_interpolation/<파일명>` | 워크플로가 어느 파일을 쓰는지 미검증. 라이선스 mit-and-apache-2.0 |

### 6.1 무결성 기준값(sha256)과 고정 리비전

| # | sha256 | HF 커밋(리비전 고정용) |
|---|---|---|
| 1 | **미검증.** 사용자 제공 값(I4)을 쓴다 | — |
| 2 | `21fd2e2f06bc4fc422c6aa20893fe189edbbd9ab3068215f96e7a6cf2f6cb5bb` | `9fc3454d3ebe1be1bade862cd4a5011f325a22cb` |
| 2a | `35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6` | `1c41cfca8ebba91d0af792a05c5761fb2c3a7975` |
| 3 | `7c1f131492e7eddacaac9069a61b81bdd39de5cc96561e677c5eab1cdce5e522` | `1c41cfca8ebba91d0af792a05c5761fb2c3a7975` |
| 3x | `9bb2d96f218c76babd85e0611b85ca8fb330a90546c01a0005e8a58a59593410` (디스크에 있으면 식별용. 삭제하려면 경로와 크기를 제시하고 승인받는다) | `e042fe480f58806578713532b8ae4e3d47d1bd63` |
| 4 | `8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48` | `1c41cfca8ebba91d0af792a05c5761fb2c3a7975` |
| 5 | `4f57821f5837f32f7142b67d815606dbd7550f194e5c769f7d6c3f83b146a5e6` | 옛 경로를 쓸 때 `13ccf95d85d120bdbc92c05b1247a6e147bf54bf` |
| 6 | `f0f60fa072089997f817402098c2fd90777cb2660dd79cf5df42fc1e3e08e527` | `a213ac8bf2f148b4f32372279a7f207846978900` |
| 8 | film_net_fp16 `f226e51375dc839d4b40e5c3d63da560dd1ea1c962364ec78f5adf2d05db05c0`<br>rife_v4.25 `1505884b9bdae956795430d2a70f7e2317b2abd8f130f8cfdb35a5759f909481`<br>rife_v4.25_heavy `40aa1838b91531f829caaac026f40d9d2e2f1eb12b65d1d6029a58ae4c703191`<br>rife_v4.25_lite `e5e5fe0286d30708f4c36aa23639a38d3d7cd0c724922c66e6b04130ae12c6e4`<br>rife_v4.26 `151874592c877740e5db11522f4514df569eeafb0a0fcb2696f16e9e8d317c94`<br>rife_v4.26_heavy `d2448f68503134b8c7c5430ce6032d6c76681a9a72f0ea8e0a56c7bee813482f` | `219da3c9d8c357ceaf457fc1d5932c6e861b8dee` |

### 6.2 용량 합계

DiT는 19.53GiB = 20,970,177,823 B로 가정했다(미검증).

| 세트 | 바이트 | GB | GiB |
|---|---|---|---|
| HF 필수 3개(#2, #3, #4) | 20,765,570,013 | 20.77 | 19.34 |
| **모바일 UI 필수(#1–#4)** | 약 41,735,747,836 | **약 41.74** | **약 38.87** |
| 필수 + TAE(#1–#4, #6) | 약 41,745,539,224 | 약 41.75 | 약 38.88 |
| `download_models.sh` 세트(#1–#6, 업스케일러는 새 경로) | 약 42,436,132,216 | 42.44 | 39.52 |
| 선택 포함 전체(#5, #8 전부 추가. #7은 크기 미상) | 약 42,682,448,310 | 약 42.68 | 약 39.75 |

- DiT가 19.5e9 B라면 필수 + TAE는 40.28GB다.
- 디스크 진행 조건(G3, G5): `/workspace` 여유 70GB 이상(모델 42.5GB + H3 ComfyUI·cu128 venv 약 8–10GB(외부 지식, 미검증) + 출력과 재시도 여유 15GB), 컨테이너 `/` 여유 10GB 이상. 미달이면 중단하고 보고한다. `/workspace`를 가득 채우면 Forge 출력, listener 상태, 로그가 깨진다. pip는 `--no-cache-dir`로 실행한다.

---

## 7. 커스텀 노드 / 시스템 의존성

### 7.1 노드 팩

출처는 `install_nodes.sh:18-22`이며 `U:64-69`, `K/models.txt:68-73`과 같다.

| 팩 | 모바일 UI에 필요 | 비고 |
|---|---|---|
| ComfyUI-DaSiWa-Nodes (`darksidewalker/ComfyUI-DaSiWa-Nodes`) | **필요** | Director / DirectorGuide / SigmaShift / Cache가 이 팩에 속한다는 것은 추정이며 미검증이다. 부분 근거: Director 문서가 이 팩에 들어 있다(`README.md:127-128`). 코드는 검토하지 않았다 |
| rgthree | 불필요(미검증 — 그래프 class_type 기준) | stock 워크플로에서만 쓴다 |
| KJNodes | 불필요(미검증 — 그래프 class_type 기준) | TAE 미리보기(`ModelPreviewOverride`)용 |
| GGUF | 불필요(미검증 — 그래프 class_type 기준) | stock 워크플로에서만 쓴다 |
| Comfyui-MMH3-UltimateUpscale (`bbaudio-2025/Comfyui-MMH3-UltimateUpscale`) | 불필요(미검증 — 그래프 class_type 기준) | 코드는 검토하지 않았다 |

- 킷이 검증한 구성은 5종 전부다(`README.md:18`, `models.txt:68`). int4_convrot TE나 int8 row-wise runtime_mixed DiT 로딩이 다른 팩의 패치에 의존하는지는 미검증이다. 따라서 DaSiWa 단독 설치는 검증되지 않은 구성이다(§10 단계 3의 확인 절차).
| (추가 후보) `LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler` | 불필요 | 잠재 업스케일러를 쓸 때만 필요하다. 킷 설치 목록에 없다. 다른 팩이 같은 기능을 주는지는 미검증 |

### 7.2 ComfyUI 코어 요구

- `CLIPLoader`의 `type:"minimax"`(`models.txt:21`)
- `SaveVideo`, `CreateVideo`, `VAEDecodeAudio`
- H3 NestedTensor(`README.md:79`)
- int8 row-wise "runtime_mixed" 로딩
- 이 요구를 충족하는 최소 버전은 미검증이다.
  - Kijai w4a8 모델은 ComfyUI 0.31.0 이상이 필요하다.
  - int8 VAE는 0.36.0에서 최고 속도를 낸다.

### 7.3 ComfyUI 0.30.0에서 없는 노드

- `ModelAttentionBackend`, `MiniMaxChunkFeedForward`(`README.md:86-88`, `models.txt:76-79`).
- 둘 다 bypass 토글 뒤에 있어서 생성은 된다. stock 워크플로에서만 빨갛게 표시된다.
- `server.py`는 이 두 노드를 쓰지 않는다. 다만 OOM 안내 메시지는 "chunking"을 권한다(`server.py:386-387`).

### 7.4 시스템 의존성

- ffmpeg
  - `install_nodes.sh:31`은 없으면 "video output needs it" 경고만 한다(`models.txt:74`).
  - `server.py`는 ffmpeg를 직접 호출하지 않는다. 인코딩은 ComfyUI의 `SaveVideo`가 한다(`server.py:240-244`). ComfyUI가 PyAV로 인코딩해 ffmpeg 바이너리가 없어도 된다는 판단은 미검증(외부 지식)이다.
  - 설치 요구로 유지한다. 킷이 요구하고, §11 `volumedetect`/`signalstats` 검증에도 필요하다.
- 셸 도구: bash(`/dev/tcp` 사용, `start.sh:38`), curl, awk, `/proc`.
- Python 의존성: 표준 라이브러리 외에 `aiohttp`만 있으면 된다(`server.py:19-20`). ComfyUI venv에 이미 들어 있다.

### 7.5 고정과 공급망 요구

- 각 팩을 커밋 SHA로 고정한다. 지금은 `git clone --depth 1`로 HEAD를 받는다(`install_nodes.sh:15`).
- 설치 전에 DaSiWa와 MMH3 코드를 검토한다.
  - 노드 코드는 ComfyUI 안에서 `/workspace` 전체에 접근할 수 있다.
  - 여기에는 기본 경로의 `rclone.conf`(Drive refresh_token)와 포드 `hfdown.sh` 사본의 HF 토큰(`R/project/HANDOFF.md:58`)이 포함된다.
- `pip install -r`에는 제약이 없다(`install_nodes.sh:27`).
  - 설치 전 `pip freeze`로 constraints 파일을 만들어 torch 교체를 막는다.
  - `--no-cache-dir`을 쓴다.
  - 각 팩 requirements.txt의 내용은 미검증이다.
- 반드시 H3 ComfyUI의 venv Python으로 설치한다.
  - `install_nodes.sh:6-7`은 venv가 없으면 system `python3`로 넘어간다.
  - 그러면 cuDNN 우회와 listener가 쓰는 `/usr/local/lib/python3.10/dist-packages`가 오염된다.

---

## 8. 킷 수정 요청 (코드·스크립트 변경)

우선순위의 뜻

- **P0:** 설치, 기동, 외부 노출, 무인 운용 가운데 어느 것이든 하기 전에 필수. 세 단계로 나눈다.
  - **P0-a(설치·다운로드 전, §10 단계 3·4 게이트):** P0-1, P0-2, P0-6, P0-7, P0-14 + 승격 P1-12, P1-13, P2-9.
  - **P0-b(첫 기동 전, §10 단계 5 게이트):** P0-3, P0-4, P0-5, P0-12, P0-13.
  - **P0-c(외부 노출 전, §10 단계 6 게이트):** P0-8 ~ P0-11.
- **P1:** 상시 운용 전에 필요.
- **P2:** 개선.

"상태" 열의 **확인**은 로컬 재현으로 확인했다는 뜻이고, **코드**는 소스를 읽고 판단했다는 뜻이다. 로컬 재현 환경은 aiohttp 3.14.3이다. 포드 ComfyUI venv의 aiohttp 버전은 미검증이며, `%2f` 디코딩과 multipart 크기 제한 동작은 버전에 따라 다를 수 있다.

### P0

| ID | 파일:줄 | 문제 | 필요한 변경 | 상태 |
|---|---|---|---|---|
| P0-1 | `download_models.sh:7` | 하드코딩된 Civitai 토큰(값 생략)이 `${CIVITAI_TOKEN:-...}`의 기본값이다. `CIVITAI_TOKEN=""`로 두어도 하드코딩 값이 쓰인다(B8) | 하드코딩 값을 지우고 `${CIVITAI_TOKEN:?CIVITAI_TOKEN 환경변수 필요}`로 바꿔 없으면 즉시 실패하게 한다. 기존 토큰은 소유자가 폐기한다 | 코드 |
| P0-2 | `download_models.sh:22` | 토큰이 URL 쿼리에 들어가 curl argv에 노출된다. 다운로드 약 10분 동안 `ps`와 `/proc/<pid>/cmdline`으로 컨테이너 안의 모든 프로세스(ComfyUI 커스텀 노드 포함)가 볼 수 있고, Civitai/CDN 접근 로그에도 남는다 | stdin으로 `Authorization: Bearer` 헤더를 넘긴다: `printf 'header = "Authorization: Bearer %s"\n' "$CIVITAI_TOKEN" \| curl -K - …`. printf는 셸 내장이라 argv에 값이 남지 않는다. 파일 방식(`-H @file`)은 쓰지 않는다(환경변수 전용 규칙). Civitai가 Bearer를 받는지는 미검증이다. 받지 않으면 argv 노출을 최소화하는 대안을 검토한다 | 코드 |
| P0-3 | `restart_comfy.sh:3-4,21,38,43-45` | `C`와 `API`가 하드코딩되어 있다. `*main.py*--port*8188*`에 맞는 모든 비조상 프로세스를 SIGTERM으로 죽인 **뒤에** `cd … \|\| exit 1`을 한다. 그래서 포드 ComfyUI가 죽고 다시 뜨지 않는다. 부분 문자열 매칭이라 `--port 18188`도 걸린다. 재기동할 때 `LD_LIBRARY_PATH`가 없고 `--enable-cors-header`가 붙는다 | `C` / `API` / `PY` / `PORT` / `LOG`를 환경변수로 받는다. kill하기 전에 디렉터리와 python이 있는지 확인한다. 자신이 띄운 PID(pidfile)만 종료한다. 포트는 정확히 매칭한다. H3 ComfyUI는 `--listen 127.0.0.1`로 기동하고 `--enable-cors-header`를 뺀다(`server.py:22`의 기본 `COMFY_URL`이 loopback이라 UI는 loopback 접근만 필요하다). 포드 venv를 쓰면 RUNBOOK의 `LD_LIBRARY_PATH`를 적용한다(`R/project/RUNBOOK.md:24-27`). 수정 전까지는 D12(→D3)대로 README:30의 복사를 하지 않아 자동 재시작을 끈다(보조: `RESTART_COMFY`를 존재하지 않는 경로로 export) | 코드 |
| P0-4 | `restart_comfy.sh:27-31,45,49` | SIGTERM이 30초 안에 먹히지 않아도 경고만 하고 새로 띄운다. 헬스체크는 **옛** 프로세스의 응답을 받아 `[ok]`를 출력한다(B11). `/workspace/logs`를 `mkdir -p`하지 않는다. `>`가 포드 RUNBOOK과 같은 `comfyui.log`를 비운다 | SIGKILL로 올리고 포트가 풀렸는지 확인한다. 로그 디렉터리를 만든다. H3 전용 로그 파일을 따로 쓴다 | 코드 |
| P0-5 | `start.sh:5-7,9,49`; `watchdog.sh:26` | `C`/`PY`/`APP`/`LOG`가 하드코딩되어 있다(`:5-7,9`). PY 경로가 없으면 40초 뒤 "did not come up"으로 실패한다. `COMFY_ROOT`/`COMFY_URL`/`RESTART_COMFY`는 호출 셸 환경을 그대로 상속할 뿐(`:49`의 `env`는 환경을 유지한다) start.sh가 설정·검증하지 않는다. 그래서 export 없이 실행되는 경로(watchdog을 export 없이 띄운 경우, cron `@reboot`, 새 셸)에서는 `server.py` 기본값(`/workspace/runpod-slim/ComfyUI`, `:8188` — `server.py:22-23,30`)으로 떨어져 갤러리/업로드 경로가 틀린다. 그 결과 갤러리가 비고, 업로드가 ComfyUI가 읽지 않는 디렉터리로 가서 이미지 모드(I2VA/FL2VA/L2VA/REF2VA)가 깨진다 | 환경변수로 덮어쓸 수 있게 한다. PY가 없으면 실패한다. `COMFY_ROOT`, `COMFY_URL`, `RESTART_COMFY`, 인증 설정, 바인드 호스트를 start.sh에서 명시적으로 설정하고 없으면 실패하게 한다. watchdog도 같은 설정으로 띄운다 | 코드 |
| P0-6 | `install_nodes.sh:6-7` | `$C/.venv-cu128`이 없으면 system `python3`(torch 2.4.0+cu121)로 넘어간다. 의존성이 엉뚱한 인터프리터에 설치되어 노드 import가 실패하고 system dist-packages가 오염된다 | `PY`를 필수 환경변수로 하고, system python으로 넘어가는 경로를 없앤다 | 코드 |
| P0-7 | `download_models.sh:5,13,15-17,47` | `set -o pipefail`이 없어서 `curl … \| tail -2` 뒤의 `$?`가 tail의 값이다(B1). curl이 18/56/33으로 끝나도 비어 있지 않은 `.part`를 완료본으로 이름을 바꾼다(B2). 다음 실행 때는 `[ -s "$2" ]` 때문에 영구히 건너뛴다. `-C -` 이어받기에 무결성 검사가 없다(B3). 실패해도 exit 0과 `__DL_DONE__`을 출력한다(B4, B5) | `set -euo pipefail`을 쓰고 curl 종료 코드를 직접 확인한다. `.part`의 sha256을 §6.1 값과 비교한 **뒤에만** 이름을 바꾼다. 이미 있는 파일도 sha256으로 건너뛸지 판단한다. 하나라도 실패하면 non-zero로 끝낸다. HF URL은 §6.1 커밋으로 고정한다 | 코드 |
| P0-8 | `server.py:761-780` | 모든 라우트에 인증이 없다. `0.0.0.0` 바인드가 하드코딩되어 있다. 누구나 GPU 작업 제출, 취소, 기록 삭제, output 아래 파일 읽기와 삭제, 업로드를 할 수 있다 | 인증 미들웨어를 `/`, `/api/*`, `/media/*`, `/inputmedia/*`, `/api/ws` 전체에 건다. UI 수정 없이 동작하도록 HTTP Basic(같은 출처의 fetch와 WS에 브라우저가 자동으로 붙인다)이나 로그인 쿠키 방식을 쓴다. 헤더 토큰 방식을 쓰려면 `index.html`의 fetch와 WS 호출(`:610, 627-765, 740`)을 고쳐야 한다. 바인드 호스트를 환경변수로 받고 기본값은 `127.0.0.1`로 한다 | 코드 |
| P0-9 | `server.py:569-571` 외 POST 핸들러, `686-696` | `request.json()`이 Content-Type을 확인하지 않는다. `text/plain`으로 보낸 `POST /api/jobs`가 200을 반환했다(CSRF). `/api/jobs/clear`, `/cancel`, multipart 업로드도 같다. `/api/ws`는 Origin을 확인하지 않아서, 외부 Origin으로 연결해도 받아들여지고 프롬프트 전체가 전달됐다(CSWSH) | POST는 `application/json`만 받는다(업로드 제외). 모든 상태 변경 요청과 WS 핸드셰이크에서 Origin 허용 목록을 확인한다 | **확인** |
| P0-10 | `server.py:644-647, 654-656, 662-664` | `str(target).startswith(str(BASE))` 검사에 경로 구분자가 없어서, 이름이 `output`이나 `input`으로 시작하는 형제 디렉터리에 닿는다. `GET /media/..%2foutput_evil%2fsecret.txt`가 200을 반환했다. DELETE는 `h3_mobile/` 밖의 다른 도구 출력도 지운다 | `target.is_relative_to(base)`를 쓴다. DELETE는 `output/h3_mobile/` 아래로 제한한다 | **확인** |
| P0-11 | `server.py:669-683` | 업로드 크기 제한이 없다. `client_max_size`는 multipart 스트리밍에 적용되지 않아 300MB가 저장됐다. 확장자 허용 목록과 내용 검사도 없어서, `.html`이 `/inputmedia`에서 `text/html`로 서빙됐다(저장형 XSS) | 스트리밍 중에 바이트를 세서 상한을 두고 413을 반환한다. png/jpg/jpeg/webp만 허용하고 매직 바이트를 확인한다. `/inputmedia` 응답에 `X-Content-Type-Options: nosniff`를 붙인다 | **확인** |
| P0-12 | `server.py:181-185` (+ 워커 사망: 460, 481, 491 / 진행률 리스너 사망: 516, 522 — `except`(526)가 RuntimeError를 잡지 않음 / 410은 484에서 잡혀 렌더 중인 작업이 failed 처리되고 다음 작업이 동시 제출됨) | `broadcast`가 `await` 도중에 `self.sockets`를 순회하는데(순회 자체는 `try` 밖), 그 사이 WS 접속이나 해제가 일어나면 `RuntimeError: Set changed size during iteration`이 난다. 재현 조건: `send_str`이 양보해야 하며, permessage-deflate 압축 프레임이 16KB를 넘을 때(스냅샷 최대 120건, `server.py:170-176`) 발생했다. 브라우저가 기본으로 압축을 협상하므로 실사용에서도 발생할 수 있다(외부 지식). 재현 결과: 150건 가운데 136건이 500, 큐 25건이 멈춤, `/api/jobs`는 계속 200이라 watchdog이 알아채지 못했다. `h_submit`은 작업을 넣은 **뒤** 500을 반환해서 사용자가 다시 제출하면 중복이 생긴다 | `list(self.sockets)`를 순회한다. 브로드캐스트 예외를 격리한다 | **확인** |
| P0-13 | `server.py:463-486` | 워커가 잡는 예외는 ComfyDown, RuntimeError, ClientError, TimeoutError뿐이다. `json.loads` ValueError나 `jobs.json` KeyError가 나면 워커가 조용히 죽는다. 작업이 `running`에 멈추고 로그도 남지 않는 것을 재현했다 | 루프 전체를 `except Exception`으로 감싼다. 해당 작업을 실패로 처리하고 계속 돈다. 워커와 리스너의 생존 상태를 헬스 엔드포인트로 노출한다 | **확인** |
| P0-14 | `start.sh:9`; `restart_comfy.sh:45`; `watchdog.sh:10`; `README.md:30-31,44` | 로그가 `/workspace/logs`에, 스크립트 사본이 `/workspace` 루트에 놓여 첫 기동 30분 안에 auto_backup이 Drive로 올린다(D10 결정보다 먼저) | H3 로그는 모두 `/workspace/h3_mobile/logs/`에 쓰고, 스크립트는 `/workspace/h3_mobile/` 아래에만 둔다. `START`와 `RESTART_COMFY`도 그 경로를 가리킨다 | 코드 |

### P1

| ID | 파일:줄 | 문제 | 필요한 변경 | 상태 |
|---|---|---|---|---|
| P1-1 | `server.py:128-140` | `save()`는 최신순으로 쓰고 `_load`는 파일 순서대로 붙인다. 그래서 재시작하면 큐가 거꾸로 돈다(1, 2, 3이 3, 2, 1로). 큐 순서는 저장되지 않는다. 300건을 넘으면 가장 오래 대기한 작업이 파일에서 빠진다 | 큐 순서를 따로 저장한다. 대기 중인 작업은 보존 한도에서 제외한다 | **확인** |
| P1-2 | `server.py:413-419, 590-594` | `/interrupt`가 전역이다. `cancelling` 동안 2초마다 다시 보내므로, 공유 ComfyUI에서는 다른 사용자의 렌더를 차례로 중단시킨다. `status="running"`과 `/prompt` 응답 사이에 취소하면 지금 돌고 있는 남의 작업을 끊는다 | 내 `prompt_id`가 실행 중일 때만 interrupt한다(`/queue`로 확인). 대기 중이면 큐에서 지운다. `prompt_id` 지정 interrupt를 0.30.0이 지원하는지는 미검증이다 | 코드 |
| P1-3 | `server.py:408, 413-421` | 폴링 루프에 전체 타임아웃이 없다. 누가 ComfyUI의 history나 큐를 지우거나 `prompt_id`가 None이면(`/history/None` 폴링) 영원히 멈춘다 | `prompt_id`를 검증한다. 전체 타임아웃을 두고 넘으면 실패로 처리한다 | 코드 |
| P1-4 | `server.py:437-438` | OOM 뒤 `/free`를 `unload_models:true`로 호출해서 모든 ComfyUI 사용자의 모델을 내린다 | 설정 플래그로 바꾼다. 공유 인스턴스에서는 기본으로 끈다(D12) | 코드 |
| P1-5 | `server.py:320-335` (특히 `328-331`), `430-432`, `484-486` | 5xx 응답을 모두 ComfyUI 다운으로 간주한다(ComfyUI 핸들러 예외 등). 노드 실행 오류는 `/history`로 보고되어 failed 처리되고, `/prompt` 검증 오류(400)도 RuntimeError로 failed 처리되므로 해당하지 않는다(ComfyUI 동작은 미검증) | 연결 오류, 타임아웃과 5xx를 구분한다. 5xx가 반복되면 재시작 대신 실패로 처리한다 | 코드 |
| P1-6 | `server.py:29, 494-527` | `CLIENT_ID`가 고정되어 있어 두 번째 인스턴스가 이벤트를 가로챈다. 이벤트의 `data.prompt_id`를 확인하지 않고 모두 `MGR.current`에 돌린다. ClientError, TimeoutError, OSError만 잡는다 | 인스턴스마다 고유한 clientId를 쓴다. `prompt_id`가 일치할 때만 반영한다. 예외 처리 범위를 넓힌다 | 코드 |
| P1-7 | `server.py:269-271`; `index.html:368, 768` | 페이지를 열 때 `/api/config`가 실패하거나 localStorage 값이 오래되면 모델명이 `""`로 가고, `normalize`가 이를 받아들여 ComfyUI 검증에서 실패한다 | 빈 값이나 모르는 값이면 서버가 기본값으로 대체한다 | 코드 |
| P1-8 | `server.py:267-298, 287-291, 296, 433-438`; `index.html:274-279, 288, 645` | `mode`, `frame_rate`, `denoise`, shift, cache 값을 검증하지 않는다(`mode:"BOGUS"`, `frame_rate:0`, `denoise:5`가 통과). 상한이 8192×8192, 200 steps, 60초, batch 20이라 32GB 검증 범위를 훨씬 넘는 작업이 OOM을 보장하고, OOM마다 `/free unload_models`가 불린다. 이미지 이름(`../../etc/passwd`)이 그대로 `timeline_data`로 간다. 3장부터는 조용히 버린다. FL2VA에 2장이 필요한지 확인하지 않는다. 잘못된 JSON이면 500이 난다 | 허용 범위를 검증한다. `mode`는 정확히 T2VA/I2VA/FL2VA/L2VA/REF2VA 5개만 허용한다. 폭/높이·duration·batch·steps 상한을 검증된 범위로 낮춘다(예: 짧은 변 ≤768, duration ≤10s, batch ≤4 — 값은 D2 결정 후 확정). 이미지 이름은 basename만 받고 `INPUT_DIR`에 있는지 확인한다. 3장 이상이면 400. FL2VA는 2장을 요구한다. 잘못된 JSON은 400 | **확인**/코드 |
| P1-9 | `watchdog.sh:8-10, 17, 24-26` | `/api/jobs`만 확인해서 워커가 죽은 것을 모른다. 단일 인스턴스 락이 없다. `START`가 없으면 60초마다 영원히 오류를 남긴다. 컨테이너가 재시작되면 되살아나지 않는다 | P0-13의 헬스 엔드포인트를 확인한다. flock 락을 쓴다. `START`가 없으면 종료한다. 자동 기동은 D11 | 코드 |
| P1-10 | `server.py:28` vs `start.sh:8`, `watchdog.sh:8`, `README.md:36,39` | `PORT` 기본값이 8189와 19123으로 다르다 | 한 값으로 통일한다(D4 결과를 반영) | 코드 |
| P1-11 | `server.py:707-713, 721-727` | 시작할 때 ComfyUI가 내려가 있으면 진행 중인 작업을 바로 실패시킨다. 살아 있는 `cancelling` 작업을 `queued`로 되돌려 취소 요청이 사라진다 | 워커와 같은 대기·복구 로직을 쓴다. 취소 상태를 유지한다 | 코드 |
| P1-12 (**P0-a로 승격**) | `download_models.sh:36`, `9-10`, `43-46` | 업스케일러 URL이 404다. 선택 모델을 무조건 받는다. `frame_interpolation` 폴더를 만들지 않는다. 다운로드 전에 여유 공간을 확인하지 않는다(B6, B7) | §6의 새 URL로 바꾸고 기존 이름으로 저장한다. 선택 모델은 플래그로 켠다. 시작할 때 `df`로 여유 공간을 확인한다 | 코드 |
| P1-13 (**P0-a로 승격**) | `install_nodes.sh:13, 15, 27, 32` | 깨진 clone도 디렉터리가 있으면 건너뛴다. clone 실패는 `[FAIL]`만 출력한다. `pip \| tail -3`이 pip의 종료 코드를 가린다. 항상 exit 0으로 끝난다. 커밋 고정이 없다(B9, B10) | 커밋 SHA를 고정해 checkout한다. `pipefail`을 쓰고 실패하면 non-zero로 끝낸다. `pip -c constraints.txt --no-cache-dir`로 설치한다 | 코드 |
| P1-14 | `index.html:610, 627-765, 740` | 루트 절대경로에 의존해서 하위 경로 프록시를 쓸 수 없다 | D4에서 nginx 하위 경로를 고를 때만 상대경로나 base path로 바꾼다 | 코드 |

### P2

| ID | 파일:줄 | 문제 | 필요한 변경 |
|---|---|---|---|
| P2-1 | `start.sh:45`, `restart_comfy.sh:45` | 재시작할 때마다 로그를 비워서 크래시 증거가 사라진다 | append 모드와 로테이션을 쓴다 |
| P2-2 | `start.sh:32, 40` | SIGTERM에서 더 올리지 않는다(B12) | SIGKILL로 올린다 |
| P2-3 | `server.py:555, 558` | `spec[1]`에서 IndexError가 날 수 있다. `object_info`가 모두 non-200이어도 `comfy_ok=True`를 반환한다(연결 실패는 ClientError로 잡혀 False, `server.py:548-549, 558-560`) | 방어 코드를 넣고 상태를 정확히 보고한다 |
| P2-4 | `server.py:386-387` | OOM 안내가 "chunking"을 권하지만 0.30.0에는 그 노드가 없고 UI에도 없다 | 문구를 고친다 |
| P2-5 | `server.py:599-609` | 실행 중인 작업을 삭제해도 ComfyUI의 렌더는 계속된다 | P1-2의 선별 interrupt를 적용한다 |
| P2-6 | `server.py:674-683`; `server.py:27, 138-141` | `input/h3m_*` 업로드 파일을 정리하지 않는다. `jobs.json`에 프롬프트 최대 300건이 평문으로 쌓인다 | 보존 기간을 두고 정리한다. 파일 권한을 제한한다 |
| P2-7 | `server.py:546`; `index.html:780` | VAE 드롭다운에 모든 VAELoader 옵션이 나와 int8을 고를 수 있다 | 허용 목록으로 필터하거나 int8을 설치하지 않는다(D6) |
| P2-8 | `K/models.txt:4`; `U:26-31` | 총량 헤더가 갱신되지 않았고, U는 int8을 권장한다 | 헤더를 42.44GB / 39.52GiB로 고치고 U를 폐기 표시한다 |
| P2-9 (**P0-a로 승격**) | `README.md:30-31` | 스크립트를 `/workspace` 루트로 복사하라고 안내해서 auto_backup 대상이 된다. 루트의 `restart_comfy.sh`는 `server.py:30`의 기본 `RESTART_COMFY` 경로이기도 하다 | `/workspace/h3_mobile/` 아래에 두도록 안내를 바꾼다. README:30의 복사 단계는 수행하지 않는다 |
| P2-10 | `watchdog.sh` | 포드의 Forge watchdog(`/workspace/scripts/watchdog.sh`, `R/project/HANDOFF.md:63`, `R/docs/OPERATIONAL_VERIFICATION.md:36-39`)과 이름이 같다. `/workspace/scripts`에 복사하면 Forge watchdog을 덮어쓰고, `pkill -f watchdog.sh`는 둘 다 죽인다. (킷 `start.sh:28-30`은 cwd가 `/workspace/h3_mobile`인 `server.py`만 죽이므로 `/workspace/listener`의 listener는 안전 — 확인) | `h3_watchdog.sh`로 이름을 바꾸고 `/workspace/h3_mobile/` 아래에만 둔다. 종료할 때는 pidfile을 쓴다 |

---

## 9. 보안·운영 규칙 준수 체크 (CLAUDE.md 대응)

| 규칙 | 킷이나 계획이 걸리는 지점 | 조치 | 확인 방법 |
|---|---|---|---|
| **Pod Protection**: `sydh2pm05u5rg2` 정지 금지 | 포트 추가 pod edit는 컨테이너 재생성이다. `restart_comfy.sh`가 포드 ComfyUI를 죽인다. 새 포드에서 bootstrap을 돌리면 안 된다 | **금지(범위 밖).** `sydh2pm05u5rg2`에는 포트·환경변수·이미지·디스크를 바꾸는 pod edit를 하지 않는다. 필요하면 이 계획이 아니라 별도 위험 검토와 사용자의 명시적 승인 대상이다. 포드의 정지, 재개, 편집은 하지 않는다. RunPod API 호출은 I6a/I6b 범위로 제한한다. 잔액 소진으로 인한 정지를 D13 잔액 조건으로 막는다. P0-3을 적용하기 전까지 자동 재시작을 끈다. 새 포드의 stop/terminate는 그 포드에만 적용하며 승인을 받는다 | 콘솔에서 포드 상태와 포트 구성이 그대로인지 확인한다 |
| **Token Security**: 민감 정보는 환경변수로만, 로그·커밋·공개 채널 금지 | `download_models.sh:7`에 토큰이 하드코딩되어 있다. `:22`에서 argv에 노출된다. auto_backup이 `/workspace` 루트와 `/workspace/scripts/`의 스크립트와 로그를 Drive로 올린다. `runpod_create_pod.py:50`은 API 키를 URL로 보낸다 | 기존 토큰을 폐기하고 재발급한다(소유자). `CIVITAI_TOKEN`, `RUNPOD_API_KEY`, 인증 토큰은 환경변수로만 받는다(전달 경로 I3). 현 포드 Jupyter가 무인증이면 환경변수도 보호되지 않으므로 D14를 먼저 결정하고, 새 토큰은 사용 직후 폐기한다. P0-1과 P0-2를 적용한다. 킷 스크립트는 `/workspace/h3_mobile/` 아래에만 둔다. 명령행과 셸 히스토리에 토큰을 쓰지 않는다 | 킷, 저장소 작업트리, git 히스토리, `/workspace` 루트, `/workspace/scripts`, 로그를 grep해서 0건인지 본다. 다운로드 중 `ps`에 토큰이 보이지 않는지 본다 |
| **공개 저장소**(`castle923/AutoRunpod`) | 원본 킷에는 토큰이 있다. pod ID와 프록시 URL 패턴이 이미 공개되어 있다 | 정화본만 커밋한다(D9, 승인 게이트). 원본 zip은 커밋하지 않는다. 문서를 갱신할 때 새 비밀값을 넣지 않는다 | 커밋 전에 diff를 grep한다 |
| **rclone.conf**: 비공개 Runpod-Backup에만 둔다 | 제3자 커스텀 노드가 `/workspace`의 `rclone.conf`를 읽을 수 있다 | 노드 커밋을 고정하고 검토한다(§7.5). 새 H3 포드(D2=B)에는 `rclone.conf`를 두지 않는 쪽을 검토한다. rclone.conf를 킷이나 저장소로 복사하지 않는다 | 새 포드의 `/workspace`에 rclone.conf가 없는지 확인한다(해당 시) |
| **TLS**: 검증 비활성화 금지, HTTPS_PROXY 해제 금지 | 다운로드 스크립트를 고칠 때 | `-k`/`--insecure`를 넣지 않는다. `HTTPS_PROXY`를 유지한다. 인증서 오류가 나면 우회하지 말고 보고한다 | 수정본을 `-k`, `--insecure`, `verify=False`로 grep한다 |
| **Community Cloud 전용** | D2=B로 새 포드를 만들 때. `runpod_create_pod.py`의 `cloudType` 기본값이 ALL이다(`:106-111`). Secure로 잘못 만든 전례가 있다(`R/SETUP_HISTORY.md:59-60`) | `--cloud-type COMMUNITY`를 명시한다. 생성 전에 사용자에게 파라미터를 보여 준다 | 생성 후 콘솔에서 Community로 표시되는지 확인한다 |
| **Drive 삭제 금지**(명시 확인 없이) | 출력을 백업할 때 `rclone sync`를 쓰면 대상 쪽 파일이 지워진다 | `rclone copy`만 쓴다. 고정 경로에만 쓰며 승인을 받는다(D10). 킷의 `DELETE /media`는 로컬 파일만 지운다 | 백업 스크립트를 검토할 때 `sync`, `delete`, `purge`가 없는지 확인한다 |
| **4팀 공유 드라이브**(ID `1rId_zhT9twxCTK8Y9QA2q94-mrMH5mm-`): 읽기를 포함한 모든 접근에 절차와 명시적 "승인"이 필요 | 저장소의 rclone 목적지는 모두 `gdrive:런포드 백업/...` 또는 `gdrive:{project_name}/`이며 4팀을 가리키는 곳은 없다. 다만 listener `/upload`의 `project_name`을 검증하지 않는다(`R/listener/server.py:458, 532-538`). 경로로 도달할 수 있는지는 미검증이다 | 이번 작업의 어떤 단계도 4팀 공유 드라이브를 대상으로 하지 않는다(기본 제외. 꼭 필요하면 CLAUDE.md 절차를 건별로 거친다). 새 스크립트에는 "4팀" 문자열과 해당 ID를 거부하는 검사를 넣는다. Drive 쓰기 전에 rclone remote 루트 키를 확인한다(D10, I7). 상위 폴더로 sync하지 않는다. listener `project_name` 검증은 킷과 별도로 수정을 요청한다 | 새 스크립트에 거부 검사가 있는지 확인한다. 조사와 작업 로그에 4팀 접근이 없는지 확인한다 |

---

## 10. 실행 순서 (단계별 계획)

`[G#]`는 사용자 승인 게이트다. 되돌릴 수 없거나, 비용이 들거나, 서비스를 재시작하거나, 포드 구성을 건드리는 단계에서는 반드시 멈추고 명시적 승인을 받는다.

### 단계 0 — 사전 확인 (비용 없음, 포드 변경 없음)

1. **[G1]** D1 라이선스 판단. 진행 여부를 정한다.
2. 토큰 소유자가 기존 Civitai 토큰을 폐기하고 새 토큰을 발급한다(I2, I3). zip의 추가 공유를 멈춘다.
3. 사용자가 콘솔에서 `sydh2pm05u5rg2`의 상태, 포트, 데이터센터, Jupyter 인증 설정을 확인한다(I5). 이 단계에서 포드를 시작, 재개, 편집하지 않는다.
4. 읽기 전용 명령의 출력을 모은다(I7).
5. D2~D17을 결정한다. D14가 A이면 **[G0]**: SSH 48031 접속을 먼저 확인한 뒤 Jupyter 인증 적용과 `jupyter_exec.py`·`auto_clean_kernels.py` 수정을 승인받는다.

### 단계 1 — 킷 수정 (로컬 스크래치패드, 포드와 무관)

1. P0-a, P0-b, P0-c를 모두 적용한다(§8 머리의 단계 구분). 각 단계는 해당 게이트 전에 끝나야 한다: P0-a → 단계 3·4, P0-b → 단계 5, P0-c → 단계 6. 나머지 P1은 상시 운용(단계 7) 전까지 적용한다.
2. 테스트 하니스(가짜 ComfyUI. 조사 때 쓴 하니스는 저장소에 없다. 보관하려면 비공개 `castle923/Runpod-Backup`에 둔다. 없으면 §11의 명령으로 다시 만든다)로 다음을 다시 재현하고 수정됐는지 확인한다.
   - 경쟁 조건
   - CSRF와 CSWSH
   - 경로 우회
   - 업로드 제한
   - 큐 순서
3. 정화본에서 토큰을 grep해서 0건인지 확인한다.
4. **[G2]** D9에 따라 저장소에 커밋할지 승인받는다. 공개 저장소라면 diff를 사용자가 직접 검토한다.

### 단계 2 — 실행 환경 준비

**D2=A (기존 포드)**

1. 디스크 여유와 ComfyUI 상태를 확인한다(읽기 전용). 진행 조건은 §6.2(`/workspace` 여유 70GB, `/` 여유 10GB 이상). 미달이면 중단하고 보고한다.
2. **[G3]** 포드에 새 디렉터리를 만들고 설치해도 되는지 승인받는다.
   - 경로·포트·기동 방식은 D3 권장값(`/workspace/h3/comfy`, 8190, `--listen 127.0.0.1`).
   - `pip freeze` 스냅샷을 먼저 저장한다.
   - H3 전용 ComfyUI와 venv를 별도 경로에 설치한다.
   - 기존 `/workspace/ComfyUI`, `/workspace/venvs/comfyui`, system python은 건드리지 않는다.

**D2=B (새 포드)**

1. **[G3']** 비용을 승인받는다: GPU, 시간당 상한, 볼륨 100GB 이상, 사용 후 정책, 종료 시각. 승인 전에 D13의 잔액 조건을 확인한다.
2. 생성 파라미터를 제시한다(D13 권장값): `--cloud-type COMMUNITY`, `--gpu-type`, `--data-center-id`, 포트 `19123/http,22/tcp`(8188 제외), 컨테이너 디스크 30GB 이상, 호스트 드라이버 580 이상. 스크립트를 쓰면 `--dry-run` 출력을 승인받는다(I6b).
3. 생성 후 `bootstrap_pod.sh`와 `new_pod_generate.sh`는 실행하지 않는다.
4. 생성 직후 확인(미검증 항목): 템플릿 `/start.sh`의 ComfyUI 기동 플래그(`--listen` 값), Jupyter 인증 여부. `curl -sI https://<new_pod>-8188.proxy.runpod.net/`과 `-8888`이 401 또는 404인지 본다. ComfyUI가 `0.0.0.0`으로 떠 있으면 `--listen 127.0.0.1`로 다시 띄운다.

### 단계 3 — 노드 설치

1. **[G4]** 제3자 코드를 실행하기 전에 승인받는다.
   - 대상: DaSiWa 1개만(모바일 UI 전용). stock 워크플로를 원하면 나머지 팩도 포함한다.
   - 커밋 SHA와 검토 결과를 제시한다.
2. 수정된 `install_nodes.sh`에 `PY`와 constraints를 지정해 실행한다.
3. ComfyUI를 기동하고 `/object_info`에서 노드와 `minimax` 옵션을 확인한다.
   - D2=A라면 이 기동은 단계 5의 G6 시간창 안에서 하거나, listener `/status`의 `batch_job`이 비어 있을 때만 한다.
   - DaSiWa 설치 후 `/object_info`에 MiniMaxH3Director/DirectorGuide/SigmaShift/Cache 4종이 모두 있고, 스모크 테스트에서 DiT/TE 로딩이 성공하는지 확인한다. 하나라도 없거나 로딩이 실패하면 검토(G4 재적용) 후 나머지 팩(킷 검증 구성 5종)을 추가한다.

### 단계 4 — 모델 다운로드

1. **[G5]** 디스크 약 42GB 사용과 토큰 사용을 승인받는다. 파일 목록, 크기, 대상 경로(§6)를 제시한다. 진행 조건은 §6.2(`/workspace` 여유 70GB, `/` 여유 10GB 이상)이며, 미달이면 중단하고 보고한다.
2. `CIVITAI_TOKEN`은 I3 전달 경로(`read -rs` 후 같은 셸에서 실행)로만 준다. 스크립트는 `/workspace/h3_mobile/` 아래에서 실행한다.
3. 필수 4개를 받는다(TAE는 D8에 따라).
4. sha256을 검증한다. int8 VAE는 받지 않는다. DiT 검증 직후 Civitai 토큰을 폐기한다.
5. 이 조사 환경에서는 civitai.com 확인이 차단되어 DiT 정보가 미검증이다. 포드에서 civitai.com에 접속되는지도 미검증이다.

### 단계 5 — 첫 기동과 스모크 테스트

1. D2=A라면 **[G6]** Forge와 listener를 멈추는 시간창을 승인받는다. 시간창 최대 길이는 사용자가 정한다. 절차는 다음과 같다.
   - 사전 확인: `curl -s localhost:5000/status`로 `batch_job`이 비어 있는지, `crontab -l`, `tmux ls`, `ps -eo pid,args | grep -E "watchdog.sh|preventive_restart"`로 Forge를 되살리는 주체를 확인한다.
   - Forge watchdog 루프가 돌고 있으면 함께 멈추고, preventive_restart cron 줄은 시간창 동안 주석 처리한다(G8과 같은 승인). "HFdyd 포드 정밀검사" Routine(`R/MONITORING_ROUTINES.md:47-50`)의 일시중지도 승인받는다.
   - 중지: `tmux kill-session -t listener; pkill -f "launch.py --port 3001"`.
   - H3 ComfyUI를 기동하고 테스트한다. 끝나면 H3를 종료한다.
   - 복구: `bash /workspace/listener/start.sh`(listener가 Forge를 다시 띄운다), 멈췄던 watchdog 루프 재기동, cron 줄과 Routine 원복.
   - 복구 확인: `tmux ls`, `curl -sf localhost:3001/sdapi/v1/progress`, Forge :3000 응답, listener state의 `restart_storm_stopped=false`.
2. 수정된 `server.py`를 `127.0.0.1`에 바인드하고 인증을 켠 채 기동한다.
   - `RESTART_COMFY`는 P0-3을 적용한 H3 전용 스크립트(`/workspace/h3_mobile/` 아래)일 때만 지정한다.
   - 그렇지 않으면 README:30의 복사를 하지 않은 상태로 두고, 보조로 존재하지 않는 경로를 export한다.
3. §11의 생성, 보안, 안정성 테스트를 수행한다. VRAM과 컨테이너 메모리 피크를 기록한다. D2=A는 §11의 진행 기준(go/no-go)을 적용한다.

### 단계 6 — 외부 노출

1. **[G7]** D4의 노출 방식을 승인받는다. SSH 터널(A), 인증 붙은 cloudflared(B), 기존 외부 포트 재사용(C — 기존 ComfyUI 재기동 포함, 별도 승인), 또는 (D2=B) 생성 시 넣은 포트(F) 가운데 하나다.
2. pod edit는 하지 않는다(E는 범위 밖).
3. 인증 없이 접근할 수 없는지 확인한다.

### 단계 7 — 상시 운용

1. **[G8]** crontab 변경을 승인받는다: H3 ComfyUI, `mobile_start`, `h3_watchdog`(P2-10)의 `@reboot`. 각 줄은 P0-5의 환경변수를 명시적으로 설정한다.
2. listener 메모리 임계치 정책을 조정할지 따로 승인받는다.

### 단계 8 — 백업 (선택)

1. **[G9]** Drive 쓰기 경로를 승인받는다.
   - 고정 경로에 `rclone copy`만 쓴다.
   - 4팀 공유 드라이브는 제외하고, 거부 검사와 rclone 루트 키 확인(D10)을 거친다.
   - H3 로그가 `/workspace/h3_mobile/logs/`에 있는지(P0-14) 확인한다.

### 단계 9 — 문서화

1. 상세 구성은 비공개 `castle923/Runpod-Backup`에 기록한다(D9=C). 공개 HANDOFF.md/STATUS.md에는 비밀이 없는 한 줄 요약만 두고, 노출 URL·포트·인증 방식은 적지 않는다.
2. **[G2 재적용]** 비밀값은 넣지 않는다.

### 단계 10 — 종료와 정리 (D2=B)

1. **[G10]** 새 포드를 stop할지 terminate할지 승인받는다.
2. `sydh2pm05u5rg2`는 대상이 아니다.
3. terminate하면 볼륨과 모델 약 42GB가 사라진다.

---

## 11. 완료 기준 / 검증 체크리스트

각 묶음의 `[단계]` 표시는 그 검증이 통과해야 넘어갈 수 있는 게이트다(§8 P0-a/b/c, §10).

**모델과 무결성** `[P0-a 이후, 단계 5 전]`

- [ ] 필수 4개 파일의 `sha256sum`이 §6.1 값과 같다. DiT는 사용자가 제공한 I4 값과 비교한다.
- [ ] `vae/MiniMaxH3/`에 int8 VAE가 없다. 남은 `.part` 파일이 없다.
- [ ] 수정된 `download_models.sh`
  - [ ] `CIVITAI_TOKEN`이 없으면 즉시 non-zero로 끝난다.
  - [ ] 다운로드를 강제로 끊으면 non-zero로 끝나고 `.part`를 완료본으로 바꾸지 않는다.

**노드와 코어** `[P0-a 이후, 단계 5 전]`

- [ ] `/object_info`에 `MiniMaxH3Director`, `MiniMaxH3DirectorGuide`, `MiniMaxH3SigmaShift`, `MiniMaxH3Cache`가 있다.
- [ ] `CLIPLoader`의 `type`에 `minimax`가 있다.
- [ ] stock DaSiWa 워크플로를 열었을 때 빨간 노드는 `ModelAttentionBackend`와 `MiniMaxChunkFeedForward` 2개뿐이다. 이 항목은 stock 워크플로를 쓸 때만 확인한다.
- [ ] ComfyUI 로그에 커스텀 노드 import 실패가 없다.
- [ ] (D2=A) 설치 전 `pip freeze`와 비교해 기존 `/workspace/venvs/comfyui`와 system dist-packages가 변하지 않았다.

**생성** `[P0-b 이후, 단계 6 전]`

- [ ] 640×384, 기본 길이(4초)의 T2VA 작업이 완료되고 `output/h3_mobile/gen_*.mp4`가 생긴다.
- [ ] 검은 화면이 아니다. 킷의 고장 출력은 "Y=16, zero variance"(`models.txt:32-33`)라 평균 밝기 > 0으로는 걸러지지 않는다. 밝은 장면 프롬프트로 `ffmpeg -i out.mp4 -vf signalstats,metadata=print:file=- -f null -`를 실행해 YAVG ≥ 20이고 YMAX−YMIN ≥ 32인 프레임이 90% 이상인지 본다.
- [ ] 오디오 트랙이 있고, `ffmpeg -af volumedetect`에서 mean_volume > −50 dB, max_volume > −20 dB다.
- [ ] I2VA에 이미지 1장, FL2VA에 이미지 2장(첫/끝), REF2VA에 이미지 1장을 올리면 H3 ComfyUI의 `input/`에 파일이 생기고 각 작업이 성공한다.
- [ ] 32의 배수가 아닌 값(예: 650×490)을 API로 보내면 서버가 640×480으로 내림 처리해 저장한다(`/api/jobs`의 params로 확인, `server.py:287-288`). 오류 문구(`server.py:388-390`)는 normalize를 우회할 때만 나온다.
- [ ] 첫 작업의 소요 시간, VRAM 피크, 컨테이너 메모리 피크를 기록했다.
- [ ] (D2=A 진행 기준) 640×384·4초 작업이 OOM 없이 N분(사용자가 정함) 안에 끝나고, 컨테이너 메모리 피크가 90%(listener 재시작 임계치) 미만이다. 하나라도 어기면 D2=B로 전환한다.

**보안** `[P0-c 이후, 단계 6 전]`

- [ ] 인증 없는 요청은 `/`, `/api/*`, `/media/*`, `/inputmedia/*`, `/api/ws` 모두에서 401이나 거부를 받는다.
- [ ] `Content-Type: text/plain`으로 보낸 `POST /api/jobs`는 거부된다.
- [ ] 외부 Origin의 WS 핸드셰이크는 거부된다.
- [ ] `GET /media/..%2foutput_evil%2fsecret.txt`는 404를 받는다(형제 디렉터리를 만들어 테스트).
- [ ] 상한을 넘는 업로드는 413, `.html`과 `.svg` 업로드는 거부된다.
- [ ] H3 ComfyUI가 `--listen 127.0.0.1`로, `--enable-cors-header` 없이 돌고 있다.
- [ ] (D2=B) `https://<pod>-8188.proxy.runpod.net/system_stats`가 응답하지 않는다.
- [ ] H3 UI와 H3 ComfyUI 포트는 인증 없이 접근할 수 없다. 기존 8888/8188/7777 노출은 D14 결과로 따로 판정한다.
- [ ] 토큰을 grep하면 0건이다: 킷, 저장소 작업트리, git 히스토리, 그리고 auto_backup이 올리는 로컬 원본(`/workspace` 루트의 느슨한 파일, `/workspace/scripts`, 최근 24시간 `/workspace/logs`). Drive 쪽은 사용자가 직접 확인한다.
- [ ] 사용한 Civitai 토큰을 DiT 검증 직후 폐기했다(소유자 확인).
- [ ] 다운로드 중 `ps`에 토큰이 보이지 않는다.

**안정성** `[P0-b 이후, 상시 운용(단계 7) 전]`

- [ ] 스크래치 하니스에서 WS 클라이언트 8개가 접속·해제를 반복하는 동안 150건을 제출해도 500이 0건이고 워커가 살아 있다.
- [ ] `server.py`를 재시작해도 큐가 제출 순서대로 실행된다.
- [ ] H3 ComfyUI를 강제로 죽이면 복구가 H3 인스턴스만 다시 띄운다. 포드의 기존 ComfyUI, Forge, listener의 PID는 그대로다.
- [ ] 워커 태스크가 멈추면 watchdog이 감지해서 다시 띄운다.
- [ ] 작업을 취소해도 다른 프롬프트가 interrupt되지 않는다(공유 인스턴스를 쓰는 경우).

**공존과 운영** `[단계 5 종료 시, 상시 운용 전]`

- [ ] (D2=A) 테스트가 끝난 뒤 Forge :3000이 정상 응답하고, listener가 다시 돌고, storm이 없다.
- [ ] `sydh2pm05u5rg2`의 상태와 포트 구성이 바뀌지 않았다(사용자가 콘솔에서 확인).
- [ ] (D2=B) 새 포드가 Community Cloud로 표시된다.
- [ ] 킷 스크립트와 H3 로그가 `/workspace` 루트, `/workspace/scripts/`, `/workspace/logs/`에 없다. 즉 auto_backup 대상에서 빠져 있다.
- [ ] 포드의 `/workspace/scripts/watchdog.sh`(Forge watchdog)가 변경되지 않았다(P2-10).
- [ ] (D2=A) G6에서 멈춘 watchdog 루프, cron 줄, Routine이 원복되었다.
- [ ] 4팀 공유 드라이브에 접근하거나 쓴 적이 없다. 새 스크립트에 거부 검사가 있다.

---

## 12. 미해결 질문 / 리스크

### 12.1 사용자에게 묻는 질문

1. **라이선스**(D1): 대한민국은 제외 지역이다. MiniMax에 문의할지, 진행할지?
2. **포드 상태**(I5): 2026-09-23 16:59Z·17:20Z·17:36Z·17:48Z에 3000/8188/8888/7777과 미노출 19123이 모두 같은 404(본문 없음)였다. 포드가 RUNNING인가, 아니면 프록시 전체 문제인가? 마지막 정상 관측은 09-22 약 01:40–02:00Z다.
3. **포드 ComfyUI**
   - 지금도 떠 있는가? 최신 기록(`R/project/HANDOFF.md:19,39`, 09-20)은 가동이고, `R/SETUP_HISTORY.md:33-34`의 "미복원"은 이전 포드 기록이다.
   - 버전은 무엇인가(I7 `git describe`)?
   - `/workspace/start_comfyui.sh`의 내용은?
   - 실제 cmdline은? RUNBOOK의 중지 명령 `pkill -f "ComfyUI/main.py"`(`R/project/RUNBOOK.md:22`)는 `cd` 후 `python3 main.py`로 띄운 프로세스와 맞지 않을 수 있다.
4. **Civitai 토큰 소유자**가 사용자 본인인가? 폐기를 누가 하는가?
5. **DiT 정보**: 모델 버전 3314686은 CivArchive의 3314675("Hybrid v2")와 어떤 관계인가? 파일 sha256은?
6. **cron 등록 여부**(I7): 포드 기록상 watchdog·preventive_restart가 있고 listener `@reboot`는 없다(커밋 `b9d6240`, `R/project/HANDOFF.md:43,59-63`). 실제 `crontab -l`과 `tmux ls` 결과는? watchdog과 preventive_restart는 둘 다 Forge를 따로 다시 띄운다.
7. **선택 모델**: RIFE를 쓴다면 어느 파일인가? 잠재 업스케일러를 쓸 것인가(노드가 추가로 필요하다)?

### 12.2 리스크

| 리스크 | 영향 | 완화 |
|---|---|---|
| 3090 24GB에서 OOM, 또는 Ampere에서 int8 row-wise/int4 convrot 미지원(미검증) | 생성 불가 또는 매우 느림 | D2=B. 아니면 C(저메모리 변형)를 실험하되 결과를 보장하지 않는다 |
| H3 RAM 오프로드가 listener의 90% 규칙을 건드림(미검증) | Forge가 불필요하게 재시작되거나 storm, OOM killer가 ComfyUI나 Forge 배치를 죽임 | D5 A(배타적 시간창), 임계치 정책 조정 |
| torch/ComfyUI 업그레이드가 기존 환경을 깸 | M7, Anima, cuDNN 우회 손상 | D3 B(별도 설치), `pip freeze`와 constraints |
| 제3자 노드 코드(DaSiWa, MMH3)를 검토하지 않음 | `/workspace` 비밀 파일(rclone.conf, HF 토큰)에 접근. 이미지 경로(`timeline_data`)가 `input/` 밖을 읽는지도 미검증 | 커밋 고정과 검토. 새 포드에 비밀 파일을 두지 않는다 |
| 노드 requirements가 torch를 교체(미검증) | venv 손상 | constraints 파일 |
| int8 VAE 검은 화면의 원인 미확정(0.30.0 버전 문제일 수 있음) | 더 작은 VAE를 못 씀 | fp16을 유지한다. Comfy-Org 신규 int8은 별도 검증 전까지 쓰지 않는다 |
| `prompt_id` 지정 interrupt를 0.30.0이 지원하는지 모름 | 공유 인스턴스에서 남의 렌더를 중단 | 전용 인스턴스 사용과 P1-2 |
| Civitai가 Bearer 헤더를 받는지 모름 | 토큰이 argv에 계속 노출됨 | P0-2 대안 검토, 다운로드 동안 다른 프로세스를 최소화 |
| 새 포드의 재고와 정지 후 GPU 재확보 실패 | 모델 재다운로드, 비용 | D13 정책. terminate 전에 반드시 승인 |
| auto_backup이 킷 스크립트와 로그를 Drive로 업로드 | 비밀 유출(로그 내용은 주로 배너·트레이스백, 미검증) | 스크립트·로그 위치 규칙(P0-14, P2-9) |
| 포드의 `/workspace/scripts/hfdown.sh`에 든 HF 토큰(`R/project/HANDOFF.md:58`)이 30분마다 Drive 스냅샷으로 올라감(`R/scripts/auto_backup_workspace.sh:44`, 킷과 별개) | HF 토큰 유출 | 토큰을 환경변수로 옮기고, HF 토큰 교체 여부를 사용자가 결정한다 |
| 현 포드 Jupyter(8888)가 무인증일 가능성(§0 #6) | 포드 내 모든 비밀(환경변수, rclone.conf, HF 토큰)과 코드 실행 노출 | D14 |
| 두 포드 동시 과금으로 잔액 소진(D2=B) | `sydh2pm05u5rg2`까지 정지될 수 있음(외부 지식, 미검증) | D13 잔액 조건, 종료 시각 사전 지정 |
| listener `/upload`의 `project_name`을 검증하지 않음(킷과 별개) | 경로를 통해 4팀 공유 드라이브에 쓰기가 가능할 수 있음(미검증) | 별도 수정 요청. Drive에는 접근하지 않고 코드로만 대응 |
| 디스크와 컨테이너 디스크 여유 미확인 | 다운로드나 설치 실패 | I7의 `df`/`du`, P1-12 사전 점검 |
| AUP #12(공개 게시물에 기계 생성 표시) | 라이선스 위반 | 게시할 때 표시하도록 운영 규칙에 넣는다 |
