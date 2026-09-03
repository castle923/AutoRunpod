# 백업/복원 구조와 rclone 작동 원리

**주의**: 이 문서에는 실제 계정 자격증명(OAuth 토큰, refresh token 등)이 없습니다.
그런 값들은 절대 GitHub에 커밋하지 않으며, 필요할 때마다 별도로(gdrive 비공개 백업 또는
직접 재인증) 가져와야 합니다. 이 문서는 **구조와 절차**만 설명합니다.

작성 시각(KST): 2026-09-03 11:15

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
- **이 실제 값들은 GitHub에 올리지 않는다.** 대신:
  1. 구글드라이브 자체에 `런포드 백업/rclone_backup_config/rclone.conf`(또는 유사 경로)로
     별도 백업해두는 방법이 있지만, 이 역시 "포드가 완전히 죽었을 때"는 접근할 방법이 없다는
     동일한 딜레마가 있다.
  2. 가장 안전한 방법은 **매번 새 포드에서 `rclone config`로 구글 계정을 다시 OAuth 인증**하는 것.
     이러면 브라우저로 구글 로그인 화면이 뜨고, 권한을 승인하면 새 토큰이 발급된다.
  3. 또는 사용자가 미리 안전한 곳(비밀번호 관리자 등)에 client_id/secret/refresh_token을
     따로 보관해뒀다가, 새 포드에 수동으로 붙여넣는 방법도 가능하다.

### 새 포드에서 rclone 처음부터 설정하는 절차

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
