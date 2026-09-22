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
exec 9>"$LOCKFILE"
if ! flock -n 9; then
  log "Another sync_rclone_conf.sh is already running — skipping"
  exit 0
fi

# cron 실행 시 환경변수가 없으므로 /workspace/.env 에서 로드
if [ -z "${GITHUB_TOKEN:-}" ] && [ -f /workspace/.env ]; then
  _grep_exit=0
  _token_line=$(grep -m1 '^GITHUB_TOKEN=' /workspace/.env) || _grep_exit=$?
  if [ "$_grep_exit" -eq 0 ] && [ -n "$_token_line" ]; then
    GITHUB_TOKEN="${_token_line#GITHUB_TOKEN=}"
    export GITHUB_TOKEN
  elif [ "$_grep_exit" -ge 2 ]; then
    log "ERROR: grep failed reading /workspace/.env (exit $?)"
    exit 1
  fi
fi

if [ -z "${GITHUB_TOKEN:-}" ]; then
  log "ERROR: GITHUB_TOKEN not set — cannot sync rclone.conf (set via env or /workspace/.env)"
  exit 1
fi

BACKUP_REPO_URL="https://github.com/castle923/Runpod-Backup.git"

# 1. 리포 클론 또는 pull (토큰은 헤더로 전달, .git/config에 남기지 않음)
GIT_AUTH_HEADER="Authorization: Bearer ${GITHUB_TOKEN}"
if [ -d "$BACKUP_DIR/.git" ]; then
  # 기존 클론의 origin URL에 토큰이 박혀 있으면 안전한 URL로 교체
  _current_url=$(git -C "$BACKUP_DIR" remote get-url origin 2>/dev/null || true)
  if [[ "$_current_url" == *"@"* ]] || [[ "$_current_url" == *"ghp_"* ]] || [[ "$_current_url" == *"gho_"* ]]; then
    git -C "$BACKUP_DIR" remote set-url origin "$BACKUP_REPO_URL"
    log "Sanitized embedded token from existing clone origin URL"
  fi

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

  # client_id 추출 및 비교 — 서로 다른 OAuth 앱의 토큰을 섞으면 안 됨
  extract_client_id() {
    python3 -c "
import configparser
c = configparser.ConfigParser()
c.read('$1')
for s in c.sections():
    print(c.get(s, 'client_id', fallback=''))
    break
" 2>/dev/null
  }

  REPO_CID=$(extract_client_id "$REPO_CONF")
  POD_CID=$(extract_client_id "$POD_CONF")

  if [ -n "$REPO_CID" ] && [ -n "$POD_CID" ] && [ "$REPO_CID" != "$POD_CID" ]; then
    log "WARNING: client_id mismatch — repo='$REPO_CID' pod='$POD_CID'. Skipping sync to prevent token/app mix. Align client_id manually."
    exit 1
  fi

  # 어느 쪽이 더 최신인지 확인 (토큰 expiry 비교)
  extract_expiry() {
    python3 -c "
import configparser, json
c = configparser.ConfigParser()
c.read('$1')
for s in c.sections():
    t = c.get(s, 'token', fallback='{}')
    print(json.loads(t).get('expiry', ''))
    break
" 2>/dev/null
  }

  REPO_EXPIRY=$(extract_expiry "$REPO_CONF")
  POD_EXPIRY=$(extract_expiry "$POD_CONF")

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

    _commit_exit=0
    git -c user.name="sync_rclone_conf" -c user.email="bot@runpod" commit -m "rclone 토큰 자동 동기화 (포드 → 리포)" >> "$LOGFILE" 2>&1 || _commit_exit=$?
    if [ "$_commit_exit" -eq 0 ]; then
      if git -c "http.extraHeader=$GIT_AUTH_HEADER" push origin main >> "$LOGFILE" 2>&1; then
        log "Pushed updated rclone.conf to repo"
      else
        log "ERROR: git push failed — repo may be out of sync"
        exit 1
      fi
    elif [ "$_commit_exit" -eq 1 ]; then
      log "WARNING: nothing to commit (rclone.conf unchanged in git)"
    else
      log "ERROR: git commit failed (exit $_commit_exit)"
      exit 1
    fi
  else
    # 리포 토큰이 더 최신 → 포드에 적용
    log "Repo token is newer — updating pod"
    cp "$POD_CONF" "$POD_CONF.bak"
    if ! cp "$REPO_CONF" "$POD_CONF"; then
      log "ERROR: Failed to update pod rclone.conf"
      exit 1
    fi
    log "Pod rclone.conf updated from repo"
  fi
else
  # 포드에 rclone.conf가 없으면 리포에서 복사
  if ! cp "$REPO_CONF" "$POD_CONF"; then
    log "ERROR: Failed to create pod rclone.conf from repo"
    exit 1
  fi
  log "Pod rclone.conf created from repo"
fi

# 3. 연결 테스트 (포드 conf 기준)
if rclone about gdrive: --config "$POD_CONF" > /dev/null 2>&1; then
  log "rclone gdrive connection OK"
else
  log "ERROR: rclone gdrive connection failed — token may need manual renewal"
  exit 1
fi
