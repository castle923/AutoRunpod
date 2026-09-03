# 백업/복원 구조와 rclone 작동 원리

**주의**: 이 문서 자체에는 실제 계정 자격증명(OAuth 토큰, refresh token 등)이 없습니다.
실제 값은 **`castle923/Runpod-Backup`(비공개 저장소)의 `secrets/rclone.conf`에만** 저장되어
있으며, `bootstrap_pod.sh`가 새 포드 부팅 시 자동으로 가져다 씁니다.
**`castle923/AutoRunpod`는 공개 저장소이므로 이 문서를 포함해 그 어떤 파일에도 실제 값을
커밋하지 않습니다** — 이 문서는 어느 저장소에 복사되어 있든 **구조와 절차**만 설명합니다.

작성 시각(KST): 2026-09-03 11:15 / 갱신: 2026-09-03 (rclone 자동 배치 방식 반영)

## 전체 구조 요약

```
[포드 로컬 디스크]  ←rclone→  [구글드라이브]              [GitHub]
/workspace/...                 런포드 백업/                AutoRunpod / Runpod-Backup
  models/Lora/         ←──→      Lora/ (668개 safetensors)   (LoRA 파일 자체는 없음)
  models/Stable-diffusion/ ←──→  체크포인트/                 (체크포인트 자체는 없음)
  scripts/              ──→      스크립트/                   scripts/ (동일 내용, 여기가 원본)
  config.json 등        ──→      설정/                       config.json 등 (동일 내용)
  (생성된 이미지)         ──→      압축파일/, <프로젝트명>/     (해당 없음)
```

- **구글드라이브**: 용량이 큰 실제 데이터(LoRA, 체크포인트, 생성된 이미지 결과물)를 저장.
- **GitHub**: 용량이 작은 설정 파일과 스크립트를 저장 — "포드를 어떻게 다시 만들지"에 대한 청사진.
- 포드가 완전히 사라져도, **구글드라이브(데이터) + GitHub(설정/절차)** 두 개만 있으면 처음부터
  다시 구성할 수 있어야 한다는 게 이 구조의 목적.

## rclone이 하는 일

`rclone`은 포드 안에서 구글드라이브를 마치 로컬 폴더처럼 다루게 해주는 CLI 도구다.
이 프로젝트에서는 `gdrive`라는 이름의 remote(원격 저장소 별칭)로 등록되어 있고,
아래처럼 쓰인다:

```bash
# 목록 보기
rclone lsf 'gdrive:런포드 백업/Lora/'

# 다운로드 (구글드라이브 → 포드)
rclone copy 'gdrive:런포드 백업/Lora/' /workspace/stable-diffusion-webui-forge/models/Lora/ \
  --transfers 6 --checkers 8 -v

# 업로드 (포드 → 구글드라이브)
rclone copyto /workspace/프로젝트.zip 'gdrive:프로젝트명/프로젝트.zip'

# 전수 대조 검증 (누락/손상 확인, 실제로는 다운로드하지 않고 크기/해시만 비교)
rclone check 'gdrive:런포드 백업/Lora/' /workspace/stable-diffusion-webui-forge/models/Lora/ -v

# 폴더/파일 공유 링크 생성
rclone link 'gdrive:런포드 백업/Lora/하나비/'
```

### rclone 설정 파일 구조 (`~/.config/rclone/rclone.conf`)

새 포드에서 rclone을 다시 쓰려면, 아래 **형식**의 설정 파일이 필요하다 (실제 값은 비밀):

```ini
[gdrive]
type = drive
client_id = <구글 클라우드 콘솔에서 발급받은 OAuth client ID>
client_secret = <해당 client secret>
scope = drive
token = {"access_token": "...", "token_type": "Bearer", "refresh_token": "...", "expiry": "..."}
```

- `access_token`은 보통 1시간 정도면 만료되지만, `refresh_token`이 있으면 rclone이 자동으로
  갱신하므로 access_token 자체는 만료돼도 상관없다.
- **공개 저장소(AutoRunpod)에는 이 실제 값들을 절대 올리지 않는다.** 대신 두 가지 경로가 있다:
  1. **(현재 방식, 자동)** 실제 값을 `castle923/Runpod-Backup`(비공개 저장소)의
     `secrets/rclone.conf`에 저장해두고, `bootstrap_pod.sh`가 새 포드 부팅 시 `GITHUB_TOKEN`으로
     그 저장소를 클론해서 자동으로 `~/.config/rclone/rclone.conf`에 배치한다. 사람이 매번 OAuth
     인증을 반복할 필요가 없어짐. 단, `GITHUB_TOKEN`이 새면 Runpod-Backup에 접근 가능한 사람이
     구글 드라이브 전체에 접근할 수 있게 되므로 토큰 관리에 주의.
  2. **(수동, 예비)** `GITHUB_TOKEN`이 없거나 Runpod-Backup 접근이 안 될 때는, 매번 새 포드에서
     `rclone config`로 구글 계정을 다시 OAuth 인증한다 (브라우저 로그인 화면 → 승인 → 새 토큰
     발급).

### 새 포드에서 rclone 수동으로 설정하는 절차 (자동 배치가 안 될 때만)

```bash
# 1. rclone 설치 확인
which rclone || (curl https://rclone.org/install.sh | sudo bash)

# 2. 대화형 설정 (권장 — 브라우저 OAuth 인증)
rclone config
# n) New remote
# name> gdrive
# Storage> drive (Google Drive)
# client_id, client_secret: 비워두면 rclone 기본 앱 사용 (또는 직접 발급한 값 입력)
# scope> 1 (Full access)
# 이후 "브라우저에서 인증하시겠습니까?" → y, 링크를 열어 구글 계정으로 로그인/승인

# 3. 연결 확인
rclone lsd gdrive:

# 4. 설정 파일을 포드 재부팅에도 살아남도록 백업 (watchdog.sh가 자동으로 이 경로에서 복구함)
mkdir -p /workspace/rclone_backup_config
cp ~/.config/rclone/rclone.conf /workspace/rclone_backup_config/rclone.conf

# 5. (선택) 이 토큰을 Runpod-Backup의 secrets/rclone.conf에도 반영해두면 다음 포드부터는
#    bootstrap_pod.sh가 자동으로 가져다 씀 — GitHub 웹 UI에서 파일을 열어 덮어쓰기만 하면 됨.
```

## 백업할 때(현재 포드 → 새로운 백업) 정보를 가져오는 방법

새 정보(신규 LoRA, 완료된 프로젝트, 수정된 스크립트 등)를 백업하고 싶을 때 실제로 쓰는 명령 패턴:

```bash
# 새 LoRA 파일 추가 (덮어쓰기 금지, 항상 copy만 사용)
rclone copy /workspace/새로운로라.safetensors 'gdrive:런포드 백업/Lora/'

# 완료된 프로젝트 백업 (finish_project.py가 이 과정을 자동화함)
python3 /workspace/scripts/finish_project.py <프로젝트명> <날짜폴더> <baseline번호>

# 수정된 설정/스크립트를 gdrive에도 반영
rclone copy /workspace/stable-diffusion-webui-forge/config.json 'gdrive:런포드 백업/설정/'
rclone copy /workspace/scripts/ 'gdrive:런포드 백업/스크립트/'

# 수정된 설정/스크립트를 GitHub에도 반영 (별도 git 저장소 클론 후)
cp /workspace/stable-diffusion-webui-forge/config.json ~/autorunpod/
cp /workspace/scripts/*.py /workspace/scripts/*.sh ~/autorunpod/scripts/
cd ~/autorunpod && git add -A && git commit -m "설명" && git push
```

## 무결성 검증 방법

LoRA/체크포인트가 다운로드/복원 중 손상되지 않았는지 두 단계로 확인한다:

1. **`rclone check`**: 구글드라이브 원본과 포드에 있는 파일을 크기·해시 기준으로 전수 대조.
   차이가 있으면 파일명과 함께 알려준다.
2. **`scripts/verify_lora_integrity.py`**: safetensors 파일 자체의 내부 구조(헤더 JSON +
   텐서 데이터 오프셋)를 파싱해서, 파일이 중간에 잘리지 않았는지 확인한다.
   ```bash
   python3 scripts/verify_lora_integrity.py /workspace/stable-diffusion-webui-forge/models/Lora
   ```
   "corrupted/suspicious files: 0"이 나오면 전부 정상.

## 구글드라이브 `런포드 백업/` 폴더 구조 (2026-09-03 기준)

```
런포드 백업/
├── Lora/                 668개 safetensors (+ 일부 하위 폴더: 하나비/, 치지직/, 미츄/ 등 미리보기 포함)
├── 체크포인트/            waiNSFWIllustrious_v140.safetensors
├── 스크립트/              watchdog.sh, auto_clean_kernels.py, preventive_restart.py, submit_job.py
├── 설정/                 config.json, ui-config.json
├── dynamic_prompts/       submit_job.py가 참조하는 프롬프트 텍스트
├── 압축파일/              완료된 프로젝트들의 zip 아카이브
├── 업스케일러/            RealESRGAN 모델 (보통 도커 이미지에 이미 내장되어 있어 필수 아님)
├── payload_예시/          Forge API 페이로드 예시 json
└── IL_미리보기/            컬렉션별 미리보기 이미지 (VLYZ, 미츄, 스텔라이브 등)
```

별도로 `런포드 자동화/` 폴더(구글드라이브 최상위)에는 최초 구축 당시의 작업 스테이징 파일들과
`hfdown.sh`, 셋업 요약 문서가 있음 (`SETUP_HISTORY.md` 참고).
