#!/bin/bash
# 새 RunPod 포드에서 딱 한 번 실행하는 통합 부트스트랩 스크립트.
# 이 스크립트 하나만 받아서 실행하면, 아래 과정이 전부 자동으로 진행된다:
#
#   1. git 설정 보정 (오래된 git의 GitHub HTTP/2 파싱 버그 회피)
#   2. GitHub castle923/AutoRunpod 저장소를 클론 (설정/스크립트의 "원본")
#   3. GitHub castle923/Runpod-Backup(비공개) 저장소에서 rclone gdrive 인증 정보
#      (secrets/rclone.conf)를 가져와 ~/.config/rclone/rclone.conf에 배치 — rclone 수동
#      인증 없이 바로 gdrive 접근 가능해짐
#   4. config.json, ui-config.json을 Forge 실제 경로에 배치
#   5. scripts/*, dynamic_prompts/*를 /workspace로 배치, 실행 권한 부여
#   6. submit_job.py 안의 포드 URL을 현재 포드 주소로 자동 치환
#   7. 리스너 서버(/workspace/listener)와 restart_forge_clean.sh 배치
#   8. nginx에 Gradio SSE 블록이 든 설정 배치 후 reload
#   9. crontab 등록 (auto_clean_kernels, auto_backup_workspace, auto_restore_on_boot,
#      그리고 @reboot 리스너 기동)
#  10. auto_restore_on_boot.sh를 즉시 1회 실행 — 재부팅을 기다리지 않고 바로
#      LoRA/체크포인트/dynamic_prompts를 gdrive에서 복원 시작
#
# 즉, "포드 생성 → 이 스크립트 실행" 두 단계만으로 예전에 사람이 수십 분~수 시간 걸려
# 손으로 하던 재구축 과정(rclone 인증 포함) 전체가 자동화된다.
#
# 사용법 (새 포드의 Jupyter 터미널 또는 SSH에서):
#   export GITHUB_TOKEN="ghp_xxx"   # 필수 — Runpod-Backup이 비공개 저장소라서 rclone 비밀정보를
#                                    # 가져오려면 반드시 필요함 (repo 읽기 권한이 있는 Personal
#                                    # Access Token)
#   curl -sL https://raw.githubusercontent.com/castle923/AutoRunpod/main/scripts/bootstrap_pod.sh | bash
#
# 이 스크립트가 하지 "않는" 것 (사람이 반드시 별도로 해야 함):
#   - LoRA/체크포인트 자체의 최초 대량 다운로드 완료까지 기다리는 것
#     (백그라운드로 시작은 되지만, 668개 전부 받는 데는 실제로 시간이 걸림)
#   - Forge/watchdog 프로세스를 처음 기동하는 것 (도커 이미지가 자동 기동하지 않는 경우
#     수동으로 Forge를 한 번 실행해야 할 수 있음)
#
# 보안 주의: GITHUB_TOKEN이 새는 순간 castle923/Runpod-Backup에 접근 가능한 사람은 누구나
# 사용자님의 구글 드라이브 전체에 접근할 수 있는 refresh_token을 얻게 됨. 이 토큰은 환경변수로만
# 전달하고, 절대 로그/커밋/공개 채널에 남기지 말 것.

set -u
REPO_URL="https://github.com/castle923/AutoRunpod.git"
CLONE_DIR="/workspace/_bootstrap_autorunpod"
FORGE_ROOT="/workspace/stable-diffusion-webui-forge"
LOGDIR="/workspace/logs"
_warnings=0
mkdir -p "$LOGDIR"

log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" | tee -a "$LOGDIR/bootstrap.log"
}
warn() {
  _warnings=$((_warnings + 1))
  log "WARNING: $1"
}

log "=== bootstrap_pod.sh started ==="

# 1. git HTTP/2 파싱 버그 회피 (오래된 git 버전에서 GitHub clone이 실패하는 문제)
git config --global http.version HTTP/1.1

# 2. 저장소 클론 (이미 있으면 최신으로 pull)
#    토큰은 http.extraHeader로 전달하여 .git/config에 남기지 않음
GIT_AUTH=()
if [ -n "${GITHUB_TOKEN:-}" ]; then
  GIT_AUTH=(-c "http.extraHeader=Authorization: Bearer ${GITHUB_TOKEN}")
fi

# fetch URL과 push URL을 독립적으로 검사하여 내장 인증정보를 제거
sanitize_origin_url() {
  local repo_dir="$1"
  local clean_url="$2"
  local _url _push_url _did_sanitize=false _ok=true

  _url=$(git -C "$repo_dir" remote get-url origin 2>/dev/null || true)
  if [[ "$_url" == *"@"* ]] || [[ "$_url" == *"ghp_"* ]] || [[ "$_url" == *"gho_"* ]]; then
    if git -C "$repo_dir" remote set-url origin "$clean_url" 2>/dev/null; then
      _did_sanitize=true
    else
      warn "Failed to sanitize fetch URL in $repo_dir"
      _ok=false
    fi
  fi

  _push_url=$(git -C "$repo_dir" remote get-url --push origin 2>/dev/null || true)
  if [ -n "$_push_url" ] && { [[ "$_push_url" == *"@"* ]] || [[ "$_push_url" == *"ghp_"* ]] || [[ "$_push_url" == *"gho_"* ]]; }; then
    if git -C "$repo_dir" remote set-url --push origin "$clean_url" 2>/dev/null; then
      _did_sanitize=true
    else
      warn "Failed to sanitize push URL in $repo_dir"
      _ok=false
    fi
  fi

  if [ "$_did_sanitize" = true ] && [ "$_ok" = true ]; then
    log "Sanitized embedded token from origin URL in $repo_dir"
  fi
}

# pull 후 작업 트리 상태를 검증 — 복구 실패 시 2를 반환하여 호출자가 배치를 건너뛰게 한다
# 반환값: 0=성공, 1=실패했지만 작업트리 안전, 2=작업트리 손상(배치 불가)
safe_pull() {
  local repo_dir="$1"
  shift
  if ! git "$@" -C "$repo_dir" pull >> "$LOGDIR/bootstrap.log" 2>&1; then
    if [ -f "$repo_dir/.git/MERGE_HEAD" ]; then
      if ! git -C "$repo_dir" merge --abort >> "$LOGDIR/bootstrap.log" 2>&1; then
        warn "git merge --abort failed in $repo_dir — worktree may be corrupted"
        return 2
      fi
      warn "git pull caused merge conflict in $repo_dir — aborted merge, using previous state"
    elif [ -d "$repo_dir/.git/rebase-merge" ] || [ -d "$repo_dir/.git/rebase-apply" ]; then
      warn "git pull left rebase state in $repo_dir — worktree corrupted"
      return 2
    else
      warn "git pull failed for $repo_dir — using existing clone"
    fi
    # 복구 후 작업 트리가 깨끗한지 최종 확인
    local _status_out _status_rc=0
    _status_out=$(git -C "$repo_dir" status --porcelain 2>&1) || _status_rc=$?
    if [ "$_status_rc" -ne 0 ]; then
      warn "git status failed in $repo_dir (exit $_status_rc) — cannot verify worktree"
      return 2
    fi
    if [ -n "$_status_out" ]; then
      warn "worktree still dirty after recovery in $repo_dir — files may be inconsistent"
      return 2
    fi
    return 1
  fi
  # pull 성공 후에도 작업 트리 정결 확인
  local _status_out2 _status_rc2=0
  _status_out2=$(git -C "$repo_dir" status --porcelain 2>&1) || _status_rc2=$?
  if [ "$_status_rc2" -ne 0 ]; then
    warn "git status failed after successful pull in $repo_dir (exit $_status_rc2)"
    return 2
  fi
  if [ -n "$_status_out2" ]; then
    warn "worktree dirty after successful pull in $repo_dir — unexpected local changes"
    return 2
  fi
  return 0
}

if [ -d "$CLONE_DIR/.git" ]; then
  sanitize_origin_url "$CLONE_DIR" "$REPO_URL"
  log "repo already cloned — pulling latest"
  _pull_rc=0
  safe_pull "$CLONE_DIR" "${GIT_AUTH[@]}" || _pull_rc=$?
  if [ "$_pull_rc" -eq 2 ]; then
    log "ERROR: AutoRunpod worktree corrupted — cannot deploy files safely, aborting."
    exit 1
  fi
else
  log "cloning $REPO_URL"
  if ! git "${GIT_AUTH[@]}" clone --depth 1 "$REPO_URL" "$CLONE_DIR" >> "$LOGDIR/bootstrap.log" 2>&1; then
    log "ERROR: clone failed, aborting bootstrap."
    exit 1
  fi
fi

if [ ! -d "$CLONE_DIR" ]; then
  log "ERROR: clone directory missing, aborting bootstrap."
  exit 1
fi

# 3. rclone gdrive 인증 정보 자동 배치 (Runpod-Backup 비공개 저장소에서 가져옴)
BACKUP_CLONE_DIR="/workspace/_bootstrap_runpod_backup"
BACKUP_REPO_URL="https://github.com/castle923/Runpod-Backup.git"
if [ -n "${GITHUB_TOKEN:-}" ]; then
  if [ -d "$BACKUP_CLONE_DIR/.git" ]; then
    sanitize_origin_url "$BACKUP_CLONE_DIR" "$BACKUP_REPO_URL"
    _backup_pull_rc=0
    safe_pull "$BACKUP_CLONE_DIR" "${GIT_AUTH[@]}" || _backup_pull_rc=$?
    if [ "$_backup_pull_rc" -eq 2 ]; then
      warn "Runpod-Backup worktree corrupted — skipping rclone.conf deployment from this checkout"
    fi
  else
    if ! git "${GIT_AUTH[@]}" clone --depth 1 "$BACKUP_REPO_URL" "$BACKUP_CLONE_DIR" >> "$LOGDIR/bootstrap.log" 2>&1; then
      warn "Runpod-Backup clone failed — rclone.conf must be configured manually"
      _backup_pull_rc=2
    fi
  fi
  if [ "${_backup_pull_rc:-0}" -eq 2 ]; then
    log "Skipping rclone.conf deployment — Runpod-Backup checkout is not trustworthy"
  elif [ -f "$BACKUP_CLONE_DIR/secrets/rclone.conf" ]; then
    mkdir -p /root/.config/rclone /workspace/rclone_backup_config
    if cp "$BACKUP_CLONE_DIR/secrets/rclone.conf" /root/.config/rclone/rclone.conf && \
       cp "$BACKUP_CLONE_DIR/secrets/rclone.conf" /workspace/rclone_backup_config/rclone.conf; then
      log "rclone.conf restored from Runpod-Backup(secrets/rclone.conf) automatically"
    else
      warn "rclone.conf copy failed — check disk space and permissions"
    fi
  else
    warn "Runpod-Backup clone succeeded but secrets/rclone.conf not found — rclone must be configured manually"
  fi
else
  warn "GITHUB_TOKEN not set — cannot fetch rclone.conf from private Runpod-Backup repo. Run 'rclone config' manually, or re-run with GITHUB_TOKEN set."
fi

# 3-2. GITHUB_TOKEN을 /workspace/.env에 저장 (cron에서 사용)
#      기존 .env가 있으면 GITHUB_TOKEN 행만 교체하고 나머지는 보존
if [ -n "${GITHUB_TOKEN:-}" ]; then
  ENV_FILE="/workspace/.env"
  _env_tmpfile=$(mktemp /workspace/.env.XXXXXX) || { warn "mktemp failed for .env"; _env_tmpfile=""; }
  if [ -n "$_env_tmpfile" ]; then
    chmod 600 "$_env_tmpfile"
    _env_ok=true
    if [ -f "$ENV_FILE" ]; then
      _gv_exit=0
      grep -v '^GITHUB_TOKEN=' "$ENV_FILE" > "$_env_tmpfile" || _gv_exit=$?
      if [ "$_gv_exit" -ge 2 ]; then
        warn "Failed to read existing $ENV_FILE (grep exit $_gv_exit)"
        rm -f "$_env_tmpfile"
        _env_ok=false
      fi
    fi
    if [ "$_env_ok" = true ]; then
      if echo "GITHUB_TOKEN=${GITHUB_TOKEN}" >> "$_env_tmpfile" && mv "$_env_tmpfile" "$ENV_FILE"; then
        chmod 600 "$ENV_FILE"
        log "GITHUB_TOKEN saved to /workspace/.env for cron scripts"
      else
        warn "Failed to write $ENV_FILE — cron scripts may lack GITHUB_TOKEN"
        rm -f "$_env_tmpfile"
      fi
    fi
  fi
fi

# 4. config.json / ui-config.json 배치
mkdir -p "$FORGE_ROOT"
if [ -f "$CLONE_DIR/config.json" ]; then
  if cp "$CLONE_DIR/config.json" "$FORGE_ROOT/config.json"; then
    log "config.json deployed"
  else
    warn "config.json 복사 실패"
  fi
fi
if [ -f "$CLONE_DIR/ui-config.json" ]; then
  if cp "$CLONE_DIR/ui-config.json" "$FORGE_ROOT/ui-config.json"; then
    log "ui-config.json deployed"
  else
    warn "ui-config.json 복사 실패"
  fi
fi

# 5. scripts/, dynamic_prompts/ 배치
mkdir -p /workspace/scripts /workspace/dynamic_prompts
if ! cp "$CLONE_DIR"/scripts/*.sh "$CLONE_DIR"/scripts/*.py /workspace/scripts/ 2>/dev/null; then
  warn "scripts/ 복사 실패 — 자동화 스크립트가 누락될 수 있음"
fi
if ! cp "$CLONE_DIR"/dynamic_prompts/* /workspace/dynamic_prompts/ 2>/dev/null; then
  warn "dynamic_prompts/ 복사 실패"
fi
chmod +x /workspace/scripts/*.sh 2>/dev/null
log "scripts/ and dynamic_prompts/ deployed"

# 6. submit_job.py의 포드 URL을 현재 포드 주소로 자동 치환
if [ -f /workspace/scripts/submit_job.py ] && [ -n "${RUNPOD_POD_ID:-}" ]; then
  sed -i "s/[a-z0-9]\{10,\}-3000/${RUNPOD_POD_ID}-3000/g" /workspace/scripts/submit_job.py
  log "submit_job.py pod URL updated to ${RUNPOD_POD_ID}"
else
  log "RUNPOD_POD_ID not set or submit_job.py missing — pod URL in submit_job.py must be fixed manually"
fi

# 6-2. 리스너 서버 배치 (감시·자동복구·업로드 API)
mkdir -p /workspace/listener
_listener_ok=true
if ! cp "$CLONE_DIR"/listener/server.py /workspace/listener/server.py 2>/dev/null; then
  warn "listener/server.py 복사 실패"; _listener_ok=false
fi
if ! cp "$CLONE_DIR"/listener/start.sh /workspace/listener/start.sh 2>/dev/null; then
  warn "listener/start.sh 복사 실패"; _listener_ok=false
fi
chmod +x /workspace/listener/start.sh 2>/dev/null
if ! cp "$CLONE_DIR"/scripts/restart_forge_clean.sh /workspace/restart_forge_clean.sh 2>/dev/null; then
  warn "restart_forge_clean.sh 복사 실패"
fi
chmod +x /workspace/restart_forge_clean.sh 2>/dev/null
if [ "$_listener_ok" = true ]; then
  log "listener + restart_forge_clean.sh deployed"
fi

# 6-3. nginx 설정 배치
if [ -f "$CLONE_DIR/config/nginx.conf" ]; then
  cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.orig 2>/dev/null
  if ! cp "$CLONE_DIR/config/nginx.conf" /etc/nginx/nginx.conf; then
    warn "nginx.conf 복사 실패"
  elif ! nginx -t >/dev/null 2>&1; then
    cp /etc/nginx/nginx.conf.orig /etc/nginx/nginx.conf 2>/dev/null
    warn "nginx.conf 검증 실패 — 원본으로 되돌림"
  elif nginx -s reload 2>/dev/null || nginx 2>/dev/null; then
    log "nginx.conf deployed and reloaded"
  else
    warn "nginx.conf 배치됐으나 reload/start 실패 — 수동 확인 필요"
  fi
fi

# 6-4. rclone.conf를 /workspace 안에도 둔다
if [ -f /root/.config/rclone/rclone.conf ]; then
  if cp /root/.config/rclone/rclone.conf /workspace/rclone.conf; then
    chmod 600 /workspace/rclone.conf
    log "rclone.conf mirrored to /workspace"
  else
    warn "rclone.conf mirror to /workspace failed"
  fi
fi

# 7. crontab 등록 (중복 없이)
#
#    watchdog.sh 와 preventive_restart.py 는 의도적으로 제외한다. 둘 다 독자적으로
#    pkill 후 Forge 를 직접 띄우는데, 리스너도 5초마다 감시하다가 프로세스가 사라지면
#    재시작한다. 두 주체가 동시에 띄우면 Forge 가 중복 기동되어 포트 3001 점유에
#    실패한다. 게다가 preventive_restart.py 는 작업이 돌고 있으면 무기한 미루므로,
#    정작 막아야 할 긴 배치 도중의 메모리 누적에는 아무 효과가 없다.
#    메모리 감시는 리스너가 직접 한다 (80% 경고 / 90%+ 유휴일 때만 재시작).
CRON_ENTRIES=(
  "*/5 * * * * /usr/bin/python3 /workspace/scripts/auto_clean_kernels.py >> /workspace/logs/auto_clean_kernels.log 2>&1"
  "*/30 * * * * /workspace/scripts/auto_backup_workspace.sh >> /workspace/logs/auto_backup.log 2>&1"
  "@reboot /workspace/scripts/auto_restore_on_boot.sh >> /workspace/logs/auto_restore.log 2>&1"
  "@reboot /workspace/listener/start.sh >> /workspace/logs/listener_boot.log 2>&1"
  "0 */6 * * * /workspace/scripts/sync_rclone_conf.sh >> /workspace/logs/sync_rclone.log 2>&1"
)
current_cron=$(crontab -l 2>/dev/null || true)
new_cron="$current_cron"
for entry in "${CRON_ENTRIES[@]}"; do
  script_path=$(echo "$entry" | grep -oE '/workspace/[a-zA-Z_/]+\.(sh|py)')
  if [ -z "$script_path" ] || ! echo "$current_cron" | grep -qF "$script_path"; then
    new_cron="$new_cron
$entry"
  fi
done
if ! echo "$new_cron" | crontab - 2>>"$LOGDIR/bootstrap.log"; then
  warn "crontab 등록 실패 — 자동화 작업(백업/복원/동기화)이 예약되지 않음"
else
  log "crontab synced (5 automation entries ensured)"
fi

# 8. auto_restore_on_boot.sh 즉시 1회 실행 (재부팅을 기다리지 않고 바로 복원 시작)
if [ -f /workspace/scripts/auto_restore_on_boot.sh ]; then
  log "running auto_restore_on_boot.sh once now (LoRA/checkpoint/dynamic_prompts restore)"
  if ! bash /workspace/scripts/auto_restore_on_boot.sh; then
    warn "auto_restore_on_boot.sh 실행 실패 — LoRA/체크포인트 복원을 수동으로 확인하세요"
  fi
fi

# 9. 리스너 즉시 기동 (재부팅을 기다리지 않는다)
if [ -x /workspace/listener/start.sh ]; then
  bash /workspace/listener/start.sh
  sleep 5
  if curl -sS --max-time 5 http://localhost:5000/health >/dev/null 2>&1; then
    log "listener started and responding on :5000"
  else
    warn "listener 기동 확인 실패 — 'bash /workspace/listener/start.sh' 로 수동 확인 필요"
  fi
fi

# 10. 최종 상태 보고 — 경고 횟수에 따라 완료/부분완료 구분
log "=== bootstrap_pod.sh finished ==="
if [ "$_warnings" -gt 0 ]; then
  log "부분 완료: $_warnings 개 경고 발생 — 위 로그에서 WARNING 항목을 확인하세요."
  if rclone lsd gdrive: > /dev/null 2>&1; then
    log "rclone gdrive 연결은 확인됨."
  else
    log "다음 단계: rclone이 아직 인증되지 않았습니다. GITHUB_TOKEN을 설정하고 재실행하거나, 'rclone config'로 gdrive를 수동 인증하세요."
  fi
  exit 1
else
  if rclone lsd gdrive: > /dev/null 2>&1; then
    log "rclone gdrive 연결 확인됨 — 모든 단계 완료."
  else
    log "다음 단계: rclone이 아직 인증되지 않았습니다. GITHUB_TOKEN을 설정하고 재실행하거나, 'rclone config'로 gdrive를 수동 인증하세요 (BACKUP_AND_RESTORE.md 참고)."
    exit 1
  fi
fi
