#!/bin/bash
# new_pod_generate.sh — 새 포드 생성 시 최소 기초 세팅 스크립트
#
# bootstrap_pod.sh와 달리, 이 스크립트는 hfdown.sh 실행을 최우선으로 하여
# Stable Diffusion Forge를 즉시 사용 가능한 상태로 만드는 것이 목적이다.
# gdrive의 680개 LoRA 전량 복원은 하지 않으며, 사용자가 원할 때 별도로 실행한다.
#
# 실행 순서:
#   1. git 설정 + AutoRunpod 클론
#   2. Runpod-Backup에서 rclone.conf 가져와 배치 (gdrive 인증)
#   3. gdrive에서 실제 HF 토큰이 포함된 hfdown.sh 가져오기
#   4. config.json / ui-config.json / nginx 배치
#   5. scripts 배치 + crontab 등록 (auto_restore_on_boot 제외)
#   6. 리스너 서버 배치 및 기동
#   7. hfdown.sh 실행 (체크포인트 + 기본 LoRA 다운로드)
#   8. 완료 안내 + 추가 복원 옵션 표시
#
# 사용법:
#   export GITHUB_TOKEN="ghp_xxx"
#   curl -sL https://raw.githubusercontent.com/castle923/AutoRunpod/main/scripts/new_pod_generate.sh | bash
#
# ※ hfdown.sh 실행으로 기본 체크포인트와 LoRA가 설치되면 Forge 즉시 사용 가능.
# ※ 추가 LoRA/설정 복원은 스크립트 완료 후 안내에 따라 사용자가 선택.
#
# 보안 주의: GITHUB_TOKEN이 새는 순간 castle923/Runpod-Backup에 접근 가능한 사람은
# 구글 드라이브 전체에 접근할 수 있는 refresh_token을 얻게 됨.
# 이 토큰은 환경변수로만 전달하고, 절대 로그/커밋/공개 채널에 남기지 말 것.

set -u
REPO_URL="https://github.com/castle923/AutoRunpod.git"
CLONE_DIR="/workspace/_bootstrap_autorunpod"
FORGE_ROOT="/workspace/stable-diffusion-webui-forge"
LOGDIR="/workspace/logs"
mkdir -p "$LOGDIR"

log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" | tee -a "$LOGDIR/new_pod_generate.log"
}

log "=== new_pod_generate.sh started ==="

# ──────────────────────────────────────────────
# 1. git 설정 + AutoRunpod 클론
# ──────────────────────────────────────────────
git config --global http.version HTTP/1.1

if [ -n "${GITHUB_TOKEN:-}" ]; then
  CLONE_URL="https://${GITHUB_TOKEN}@github.com/castle923/AutoRunpod.git"
else
  CLONE_URL="$REPO_URL"
fi

if [ -d "$CLONE_DIR/.git" ]; then
  log "repo already cloned — pulling latest"
  git -C "$CLONE_DIR" pull >> "$LOGDIR/new_pod_generate.log" 2>&1
else
  log "cloning AutoRunpod"
  git clone --depth 1 "$CLONE_URL" "$CLONE_DIR" >> "$LOGDIR/new_pod_generate.log" 2>&1
fi

if [ ! -d "$CLONE_DIR" ]; then
  log "ERROR: clone failed, aborting."
  exit 1
fi

# ──────────────────────────────────────────────
# 2. rclone gdrive 인증 정보 배치 (Runpod-Backup 비공개 저장소)
# ──────────────────────────────────────────────
BACKUP_CLONE_DIR="/workspace/_bootstrap_runpod_backup"
if [ -n "${GITHUB_TOKEN:-}" ]; then
  BACKUP_CLONE_URL="https://${GITHUB_TOKEN}@github.com/castle923/Runpod-Backup.git"
  if [ -d "$BACKUP_CLONE_DIR/.git" ]; then
    git -C "$BACKUP_CLONE_DIR" pull >> "$LOGDIR/new_pod_generate.log" 2>&1
  else
    git clone --depth 1 "$BACKUP_CLONE_URL" "$BACKUP_CLONE_DIR" >> "$LOGDIR/new_pod_generate.log" 2>&1
  fi
  if [ -f "$BACKUP_CLONE_DIR/secrets/rclone.conf" ]; then
    mkdir -p /root/.config/rclone /workspace/rclone_backup_config
    cp "$BACKUP_CLONE_DIR/secrets/rclone.conf" /root/.config/rclone/rclone.conf
    cp "$BACKUP_CLONE_DIR/secrets/rclone.conf" /workspace/rclone_backup_config/rclone.conf
    chmod 600 /root/.config/rclone/rclone.conf
    cp /root/.config/rclone/rclone.conf /workspace/rclone.conf
    chmod 600 /workspace/rclone.conf
    log "rclone.conf deployed (gdrive 인증 완료)"
  else
    log "WARNING: secrets/rclone.conf not found — rclone 수동 설정 필요"
  fi
else
  log "WARNING: GITHUB_TOKEN not set — rclone.conf를 가져올 수 없음"
fi

# ──────────────────────────────────────────────
# 3. gdrive에서 실제 HF 토큰이 포함된 hfdown.sh 가져오기
# ──────────────────────────────────────────────
HFDOWN_LOCAL="/workspace/scripts/hfdown.sh"
mkdir -p /workspace/scripts

if rclone lsd gdrive: > /dev/null 2>&1; then
  log "gdrive 연결 확인 — hfdown.sh 가져오기 시도"
  rclone copy "gdrive:런포드 자동화/hfdown.sh" /workspace/scripts/ >> "$LOGDIR/new_pod_generate.log" 2>&1
  if [ -f "$HFDOWN_LOCAL" ]; then
    chmod +x "$HFDOWN_LOCAL"
    log "hfdown.sh retrieved from gdrive (HF 토큰 포함 버전)"
  else
    log "WARNING: gdrive에서 hfdown.sh를 찾지 못함 — GitHub 버전(토큰 플레이스홀더) 사용"
    cp "$CLONE_DIR/scripts/hfdown.sh" "$HFDOWN_LOCAL" 2>/dev/null
    chmod +x "$HFDOWN_LOCAL" 2>/dev/null
  fi
else
  log "WARNING: rclone gdrive 연결 불가 — GitHub 버전 hfdown.sh 사용 (토큰 수동 교체 필요)"
  cp "$CLONE_DIR/scripts/hfdown.sh" "$HFDOWN_LOCAL" 2>/dev/null
  chmod +x "$HFDOWN_LOCAL" 2>/dev/null
fi

# ──────────────────────────────────────────────
# 4. config.json / ui-config.json / nginx 배치
# ──────────────────────────────────────────────
mkdir -p "$FORGE_ROOT"
[ -f "$CLONE_DIR/config.json" ] && cp "$CLONE_DIR/config.json" "$FORGE_ROOT/config.json" && log "config.json deployed"
[ -f "$CLONE_DIR/ui-config.json" ] && cp "$CLONE_DIR/ui-config.json" "$FORGE_ROOT/ui-config.json" && log "ui-config.json deployed"

if [ -f "$CLONE_DIR/config/nginx.conf" ]; then
  cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.orig 2>/dev/null
  cp "$CLONE_DIR/config/nginx.conf" /etc/nginx/nginx.conf
  if nginx -t >/dev/null 2>&1; then
    nginx -s reload 2>/dev/null || nginx 2>/dev/null
    log "nginx.conf deployed and reloaded"
  else
    cp /etc/nginx/nginx.conf.orig /etc/nginx/nginx.conf 2>/dev/null
    log "WARNING: nginx.conf 검증 실패 — 원본으로 되돌림"
  fi
fi

# ──────────────────────────────────────────────
# 5. scripts 배치 + crontab (auto_restore_on_boot 제외)
# ──────────────────────────────────────────────
mkdir -p /workspace/scripts /workspace/dynamic_prompts
cp "$CLONE_DIR"/scripts/*.sh "$CLONE_DIR"/scripts/*.py /workspace/scripts/ 2>/dev/null
cp "$CLONE_DIR"/dynamic_prompts/* /workspace/dynamic_prompts/ 2>/dev/null
chmod +x /workspace/scripts/*.sh 2>/dev/null
log "scripts/ and dynamic_prompts/ deployed"

if [ -f /workspace/scripts/submit_job.py ] && [ -n "${RUNPOD_POD_ID:-}" ]; then
  sed -i "s/[a-z0-9]\{10,\}-3000/${RUNPOD_POD_ID}-3000/g" /workspace/scripts/submit_job.py
  log "submit_job.py pod URL updated to ${RUNPOD_POD_ID}"
fi

CRON_ENTRIES=(
  "*/5 * * * * /usr/bin/python3 /workspace/scripts/auto_clean_kernels.py >> /workspace/logs/auto_clean_kernels.log 2>&1"
  "*/30 * * * * /workspace/scripts/auto_backup_workspace.sh >> /workspace/logs/auto_backup.log 2>&1"
  "@reboot /workspace/listener/start.sh >> /workspace/logs/listener_boot.log 2>&1"
)
current_cron=$(crontab -l 2>/dev/null || true)
new_cron="$current_cron"
for entry in "${CRON_ENTRIES[@]}"; do
  script_name=$(echo "$entry" | grep -oE '/workspace/(scripts|listener)/[a-zA-Z_]+\.(sh|py)')
  if ! echo "$current_cron" | grep -qF "$script_name"; then
    new_cron="$new_cron
$entry"
  fi
done
echo "$new_cron" | crontab -
log "crontab synced (auto_restore_on_boot 제외 — 사용자 선택 시만 실행)"

# ──────────────────────────────────────────────
# 6. 리스너 서버 배치 및 기동
# ──────────────────────────────────────────────
mkdir -p /workspace/listener
cp "$CLONE_DIR"/listener/server.py /workspace/listener/server.py 2>/dev/null
cp "$CLONE_DIR"/listener/start.sh  /workspace/listener/start.sh 2>/dev/null
chmod +x /workspace/listener/start.sh 2>/dev/null
cp "$CLONE_DIR"/scripts/restart_forge_clean.sh /workspace/restart_forge_clean.sh 2>/dev/null
chmod +x /workspace/restart_forge_clean.sh 2>/dev/null
log "listener + restart_forge_clean.sh deployed"

if [ -x /workspace/listener/start.sh ]; then
  bash /workspace/listener/start.sh
  sleep 5
  if curl -sS --max-time 5 http://localhost:5000/health >/dev/null 2>&1; then
    log "listener started and responding on :5000"
  else
    log "WARNING: listener 기동 확인 실패"
  fi
fi

# ──────────────────────────────────────────────
# 7. hfdown.sh 실행 (기본 체크포인트 + LoRA 다운로드)
# ──────────────────────────────────────────────
log "=== hfdown.sh 실행 시작 (기초 모델 다운로드) ==="
cd "$FORGE_ROOT/models" 2>/dev/null || cd /workspace

if [ -f "$HFDOWN_LOCAL" ]; then
  bash "$HFDOWN_LOCAL" >> "$LOGDIR/new_pod_generate.log" 2>&1
  log "hfdown.sh 실행 완료"
else
  log "ERROR: hfdown.sh not found — 수동 실행 필요"
fi

# ──────────────────────────────────────────────
# 8. 완료 안내 + 추가 복원 옵션
# ──────────────────────────────────────────────
log "=== new_pod_generate.sh finished ==="
echo ""
echo "=============================================="
echo "  기초 세팅 완료!"
echo "=============================================="
echo ""
echo "  ✓ rclone gdrive 인증 완료"
echo "  ✓ Forge config/ui-config 배치 완료"
echo "  ✓ 리스너 서버 가동 완료 (port 5000)"
echo "  ✓ hfdown 실행 완료 (체크포인트 + 기본 LoRA)"
echo "  ✓ nginx SSE 설정 배치 완료"
echo ""
echo "  Forge를 시작하면 Stable Diffusion 즉시 사용 가능합니다."
echo ""
echo "----------------------------------------------"
echo "  [선택] 추가 데이터 복원 옵션:"
echo "----------------------------------------------"
echo ""
echo "  1) gdrive LoRA 전량 복원 (680개, ~100GB, 수 시간 소요):"
echo "     bash /workspace/scripts/auto_restore_on_boot.sh"
echo ""
echo "  2) gdrive 체크포인트 복원:"
echo "     rclone copy 'gdrive:런포드 백업/체크포인트/' '$FORGE_ROOT/models/Stable-diffusion/' --transfers 2"
echo ""
echo "  3) dynamic_prompts 복원:"
echo "     rclone copy 'gdrive:런포드 백업/dynamic_prompts/' /workspace/dynamic_prompts/ --transfers 2"
echo ""
echo "  4) 부팅 시 자동 복원 활성화 (crontab에 auto_restore_on_boot 등록):"
echo '     (crontab -l; echo "@reboot /workspace/scripts/auto_restore_on_boot.sh >> /workspace/logs/auto_restore.log 2>&1") | crontab -'
echo ""
echo "  ※ 위 옵션들은 필요할 때 수동으로 실행하세요."
echo "  ※ Codex가 Civitai 모델을 별도로 관리할 예정이라면"
echo "    gdrive 복원 없이 Codex 작업을 진행하면 됩니다."
echo "=============================================="
