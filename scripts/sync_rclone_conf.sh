#!/bin/bash
# rclone.conf 자동 동기화 스크립트
# GitHub Runpod-Backup 리포의 secrets/rclone.conf를 포드에 동기화한다.
# crontab에 등록하여 주기적으로 실행 (예: 매 6시간).
#
# 사용법:
#   export GITHUB_TOKEN="ghp_xxx"
#   bash /workspace/scripts/sync_rclone_conf.sh
#
# 동작 원리:
#   1. Runpod-Backup 리포에서 secrets/rclone.conf를 fetch
#   2. 포드의 /workspace/rclone.conf와 비교
#   3. 다르면 업데이트하고 연결 테스트
#   4. 포드에서 갱신된 토큰이 있으면 리포에 push (양방향 동기화)

set -u
LOGFILE="/workspace/logs/sync_rclone.log"
BACKUP_DIR="/workspace/_bootstrap_runpod_backup"
POD_CONF="/workspace/rclone.conf"
REPO_CONF="$BACKUP_DIR/secrets/rclone.conf"
LOCKFILE="/workspace/logs/sync_rclone.lock"
mkdir -p /workspace/logs

log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" | tee -a "$LOGFILE"
}

# 동시 실행 방지 (flock)
# exec 9> 로 잠금 파일 열기를 먼저 검증하고, flock 실패를 구분한다
if ! exec 9>"$LOCKFILE"; then
  log "ERROR: Cannot open lock file $LOCKFILE"
  exit 1
fi
_flock_exit=0
flock -n 9 || _flock_exit=$?
if [ "$_flock_exit" -eq 1 ]; then
  log "Another sync_rclone_conf.sh is already running — skipping"
  exit 0
elif [ "$_flock_exit" -ne 0 ]; then
  log "ERROR: flock failed (exit $_flock_exit) — cannot acquire lock"
  exit 1
fi

# cron 실행 시 환경변수가 없으므로 /workspace/.env 에서 로드
if [ -z "${GITHUB_TOKEN:-}" ] && [ -f /workspace/.env ]; then
  _grep_exit=0
  _token_line=$(grep -m1 '^GITHUB_TOKEN=' /workspace/.env) || _grep_exit=$?
  if [ "$_grep_exit" -eq 0 ] && [ -n "$_token_line" ]; then
    GITHUB_TOKEN="${_token_line#GITHUB_TOKEN=}"
    export GITHUB_TOKEN
  elif [ "$_grep_exit" -ge 2 ]; then
    log "ERROR: grep failed reading /workspace/.env (exit $_grep_exit)"
    exit 1
  fi
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
  log "ERROR: GITHUB_TOKEN not set — cannot sync rclone.conf (set via env or /workspace/.env)"
  exit 1
fi

BACKUP_REPO_URL="https://github.com/castle923/Runpod-Backup.git"

# rclone.conf에서 gdrive 섹션의 지정 필드를 추출하는 공용 함수
# 파서 종료 코드를 검사하여 파싱 실패와 빈 값을 구분한다
extract_rclone_field() {
  local conf_path="$1"
  local field="$2"
  python3 -c "
import configparser, json, sys
c = configparser.ConfigParser()
read_ok = c.read('$conf_path')
if not read_ok:
    print('__PARSE_ERROR__', file=sys.stderr)
    sys.exit(2)
gdrive = None
for s in c.sections():
    if c.get(s, 'type', fallback='') == 'drive':
        gdrive = s
        break
if gdrive is None:
    for s in c.sections():
        gdrive = s
        break
if gdrive is None:
    print('__NO_SECTION__', file=sys.stderr)
    sys.exit(2)
if '$field' == 'client_id':
    print(c.get(gdrive, 'client_id', fallback=''))
elif '$field' == 'expiry':
    t = c.get(gdrive, 'token', fallback='')
    if not t:
        print('__NO_TOKEN__', file=sys.stderr)
        sys.exit(2)
    try:
        tj = json.loads(t)
    except json.JSONDecodeError:
        print('__BAD_TOKEN_JSON__', file=sys.stderr)
        sys.exit(2)
    exp = tj.get('expiry', '')
    if not exp:
        print('__NO_EXPIRY__', file=sys.stderr)
        sys.exit(2)
    print(exp)
" 2>/dev/null
}

# 1. 리포 클론 또는 pull (토큰은 헤더로 전달, .git/config에 남기지 않음)
GIT_AUTH_HEADER="Authorization: Bearer ${GITHUB_TOKEN}"

sanitize_origin_url() {
  local repo_dir="$1"
  local clean_url="$2"
  local _url
  _url=$(git -C "$repo_dir" remote get-url origin 2>/dev/null || true)
  if [[ "$_url" == *"@"* ]] || [[ "$_url" == *"ghp_"* ]] || [[ "$_url" == *"gho_"* ]]; then
    if ! git -C "$repo_dir" remote set-url origin "$clean_url"; then
      log "ERROR: Failed to sanitize origin URL in $repo_dir"
      exit 1
    fi
    local _push_url
    _push_url=$(git -C "$repo_dir" remote get-url --push origin 2>/dev/null || true)
    if [ -n "$_push_url" ] && { [[ "$_push_url" == *"@"* ]] || [[ "$_push_url" == *"ghp_"* ]] || [[ "$_push_url" == *"gho_"* ]]; }; then
      if ! git -C "$repo_dir" remote set-url --push origin "$clean_url"; then
        log "ERROR: Failed to sanitize push URL in $repo_dir"
        exit 1
      fi
    fi
    log "Sanitized embedded token from origin URL in $repo_dir"
  fi
}

if [ -d "$BACKUP_DIR/.git" ]; then
  sanitize_origin_url "$BACKUP_DIR" "$BACKUP_REPO_URL"

  if ! git -C "$BACKUP_DIR" -c "http.extraHeader=$GIT_AUTH_HEADER" fetch origin main >> "$LOGFILE" 2>&1; then
    log "ERROR: git fetch failed — cannot sync"
    exit 1
  fi
  if ! git -C "$BACKUP_DIR" reset --hard origin/main >> "$LOGFILE" 2>&1; then
    log "ERROR: git reset failed — repo may be corrupted"
    exit 1
  fi
else
  if ! git -c "http.extraHeader=$GIT_AUTH_HEADER" clone --depth 1 "$BACKUP_REPO_URL" "$BACKUP_DIR" >> "$LOGFILE" 2>&1; then
    log "ERROR: git clone failed — cannot sync"
    exit 1
  fi
fi

if [ ! -f "$REPO_CONF" ]; then
  log "ERROR: secrets/rclone.conf not found in repo"
  exit 1
fi

# 2. 비교: 리포 vs 포드
if [ -f "$POD_CONF" ]; then
  REPO_HASH=$(sha256sum "$REPO_CONF" | cut -d' ' -f1)
  POD_HASH=$(sha256sum "$POD_CONF" | cut -d' ' -f1)

  if [ "$REPO_HASH" = "$POD_HASH" ]; then
    log "rclone.conf already in sync — no action needed"
    exit 0
  fi

  # client_id 추출 및 비교
  REPO_CID=$(extract_rclone_field "$REPO_CONF" "client_id")
  _repo_cid_exit=$?
  POD_CID=$(extract_rclone_field "$POD_CONF" "client_id")
  _pod_cid_exit=$?

  if [ "$_repo_cid_exit" -ne 0 ]; then
    log "ERROR: Failed to parse repo rclone.conf — aborting sync"
    exit 1
  fi
  if [ "$_pod_cid_exit" -ne 0 ]; then
    log "ERROR: Failed to parse pod rclone.conf — aborting sync"
    exit 1
  fi

  # 빈 client_id = rclone 기본 OAuth 앱 사용. 한쪽만 custom이면 앱이 다른 것이므로 차단
  if [ -z "$REPO_CID" ] && [ -n "$POD_CID" ]; then
    log "WARNING: client_id mismatch — repo uses default OAuth app, pod uses custom '$POD_CID'. Align client_id manually."
    exit 1
  elif [ -n "$REPO_CID" ] && [ -z "$POD_CID" ]; then
    log "WARNING: client_id mismatch — repo uses custom '$REPO_CID', pod uses default OAuth app. Align client_id manually."
    exit 1
  elif [ -n "$REPO_CID" ] && [ -n "$POD_CID" ] && [ "$REPO_CID" != "$POD_CID" ]; then
    log "WARNING: client_id mismatch — repo='$REPO_CID' pod='$POD_CID'. Align client_id manually."
    exit 1
  fi

  # 토큰 expiry 추출 및 검증
  REPO_EXPIRY=$(extract_rclone_field "$REPO_CONF" "expiry")
  _repo_exp_exit=$?
  POD_EXPIRY=$(extract_rclone_field "$POD_CONF" "expiry")
  _pod_exp_exit=$?

  if [ "$_repo_exp_exit" -ne 0 ] || [ -z "$REPO_EXPIRY" ]; then
    log "ERROR: Failed to extract valid expiry from repo rclone.conf — aborting sync"
    exit 1
  fi
  if [ "$_pod_exp_exit" -ne 0 ] || [ -z "$POD_EXPIRY" ]; then
    log "ERROR: Failed to extract valid expiry from pod rclone.conf — aborting sync"
    exit 1
  fi

  log "Repo token expiry: $REPO_EXPIRY"
  log "Pod  token expiry: $POD_EXPIRY"

  if [[ "$POD_EXPIRY" > "$REPO_EXPIRY" ]]; then
    # 포드 토큰이 더 최신 → rclone 동작 검증 후 리포에 push
    log "Pod token is newer — verifying before push"

    if ! rclone about gdrive: --config "$POD_CONF" > /dev/null 2>&1; then
      log "ERROR: Pod rclone.conf failed verification — not pushing broken config to repo"
      exit 1
    fi

    if ! cp "$POD_CONF" "$REPO_CONF"; then
      log "ERROR: Failed to copy pod conf to repo staging"
      exit 1
    fi

    cd "$BACKUP_DIR"
    if ! git add secrets/rclone.conf; then
      log "ERROR: git add failed"
      exit 1
    fi

    # git diff --cached --quiet로 staged 변경 유무를 먼저 확인
    # commit 실패(hook 거부 등)와 "변경 없음"을 구분하기 위함
    if git diff --cached --quiet; then
      log "WARNING: nothing to commit (rclone.conf unchanged in git)"
    else
      if ! git -c user.name="sync_rclone_conf" -c user.email="bot@runpod" commit -m "rclone 토큰 자동 동기화 (포드 → 리포)" >> "$LOGFILE" 2>&1; then
        log "ERROR: git commit failed (hook rejection or other error)"
        exit 1
      fi
      if ! git -c "http.extraHeader=$GIT_AUTH_HEADER" push origin main >> "$LOGFILE" 2>&1; then
        log "ERROR: git push failed — repo may be out of sync"
        exit 1
      fi
      log "Pushed updated rclone.conf to repo"
    fi
  else
    # 리포 토큰이 더 최신 → 후보 파일에서 검증 후 포드에 적용
    log "Repo token is newer — verifying before applying to pod"

    _candidate=$(mktemp /workspace/.rclone_candidate.XXXXXX)
    chmod 600 "$_candidate"
    if ! cp "$REPO_CONF" "$_candidate"; then
      rm -f "$_candidate"
      log "ERROR: Failed to create candidate rclone.conf"
      exit 1
    fi

    if ! rclone about gdrive: --config "$_candidate" > /dev/null 2>&1; then
      rm -f "$_candidate"
      log "ERROR: Repo rclone.conf failed verification — keeping current pod config"
      exit 1
    fi

    if ! cp "$POD_CONF" "$POD_CONF.bak"; then
      rm -f "$_candidate"
      log "ERROR: Failed to create backup of pod rclone.conf"
      exit 1
    fi
    chmod 600 "$POD_CONF.bak"

    if ! mv "$_candidate" "$POD_CONF"; then
      log "ERROR: Failed to replace pod rclone.conf — restoring backup"
      cp "$POD_CONF.bak" "$POD_CONF" 2>/dev/null
      exit 1
    fi
    chmod 600 "$POD_CONF"
    log "Pod rclone.conf updated from repo (verified)"
  fi
else
  # 포드에 rclone.conf가 없으면 리포에서 복사 후 검증
  _candidate=$(mktemp /workspace/.rclone_candidate.XXXXXX)
  chmod 600 "$_candidate"
  if ! cp "$REPO_CONF" "$_candidate"; then
    rm -f "$_candidate"
    log "ERROR: Failed to create candidate rclone.conf from repo"
    exit 1
  fi

  if ! rclone about gdrive: --config "$_candidate" > /dev/null 2>&1; then
    log "WARNING: Repo rclone.conf failed verification — deploying anyway (token may need renewal)"
  fi

  if ! mv "$_candidate" "$POD_CONF"; then
    rm -f "$_candidate"
    log "ERROR: Failed to create pod rclone.conf"
    exit 1
  fi
  chmod 600 "$POD_CONF"
  log "Pod rclone.conf created from repo"
fi

# 3. 최종 연결 테스트 (파일 동기화 완료와 별도로 실제 연결을 확인)
if rclone about gdrive: --config "$POD_CONF" > /dev/null 2>&1; then
  log "rclone gdrive connection OK"
else
  log "WARNING: rclone gdrive connection failed after sync — token may need manual renewal"
  exit 1
fi
