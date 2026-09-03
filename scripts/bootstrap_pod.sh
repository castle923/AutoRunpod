#!/bin/bash
# 새 RunPod 포드에서 딱 한 번 실행하는 통합 부트스트랩 스크립트.
# 이 스크립트 하나만 받아서 실행하면, 아래 과정이 전부 자동으로 진행된다:
#
#   1. git 설정 보정 (오래된 git의 GitHub HTTP/2 파싱 버그 회피)
#   2. GitHub castle923/AutoRunpod 저장소를 클론 (설정/스크립트의 "원본")
#   3. config.json, ui-config.json을 Forge 실제 경로에 배치
#   4. scripts/*, dynamic_prompts/*를 /workspace로 배치, 실행 권한 부여
#   5. submit_job.py 안의 포드 URL을 현재 포드 주소로 자동 치환
#   6. crontab에 5종 자동화(auto_clean_kernels, preventive_restart, watchdog,
#      auto_restore_on_boot, auto_backup_workspace)를 중복 없이 등록
#   7. auto_restore_on_boot.sh를 즉시 1회 실행 — 재부팅을 기다리지 않고 바로
#      LoRA/체크포인트/dynamic_prompts를 gdrive에서 복원 시작
#
# 즉, "포드 생성 → rclone 인증(1회, 수동) → 이 스크립트 실행" 세 단계만으로
# 예전에 사람이 수십 분~수 시간 걸려 손으로 하던 재구축 과정 대부분이 자동화된다.
#
# 사용법 (새 포드의 Jupyter 터미널 또는 SSH에서):
#   export GITHUB_TOKEN="ghp_xxx"   # AutoRunpod가 비공개 저장소인 경우에만 필요
#   curl -sL https://raw.githubusercontent.com/castle923/AutoRunpod/main/scripts/bootstrap_pod.sh | bash
#
# 이 스크립트가 하지 "않는" 것 (사람이 반드시 별도로 해야 함):
#   - rclone gdrive 인증 (OAuth 브라우저 승인 필요 — BACKUP_AND_RESTORE.md 참고)
#   - LoRA/체크포인트 자체의 최초 대량 다운로드 완료까지 기다리는 것
#     (백그라운드로 시작은 되지만, 668개 전부 받는 데는 실제로 시간이 걸림)
#   - Forge/watchdog 프로세스를 처음 기동하는 것 (도커 이미지가 자동 기동하지 않는 경우
#     수동으로 Forge를 한 번 실행해야 할 수 있음)

set -u
REPO_URL="https://github.com/castle923/AutoRunpod.git"
CLONE_DIR="/workspace/_bootstrap_autorunpod"
FORGE_ROOT="/workspace/stable-diffusion-webui-forge"
LOGDIR="/workspace/logs"
mkdir -p "$LOGDIR"

log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" | tee -a "$LOGDIR/bootstrap.log"
}

log "=== bootstrap_pod.sh started ==="

# 1. git HTTP/2 파싱 버그 회피 (오래된 git 버전에서 GitHub clone이 실패하는 문제)
git config --global http.version HTTP/1.1

# 2. 저장소 클론 (이미 있으면 최신으로 pull)
if [ -n "${GITHUB_TOKEN:-}" ]; then
  CLONE_URL="https://${GITHUB_TOKEN}@github.com/castle923/AutoRunpod.git"
else
  CLONE_URL="$REPO_URL"
fi

if [ -d "$CLONE_DIR/.git" ]; then
  log "repo already cloned — pulling latest"
  git -C "$CLONE_DIR" pull >> "$LOGDIR/bootstrap.log" 2>&1
else
  log "cloning $REPO_URL"
  git clone --depth 1 "$CLONE_URL" "$CLONE_DIR" >> "$LOGDIR/bootstrap.log" 2>&1
fi

if [ ! -d "$CLONE_DIR" ]; then
  log "ERROR: clone failed, aborting bootstrap."
  exit 1
fi

# 3. config.json / ui-config.json 배치
mkdir -p "$FORGE_ROOT"
[ -f "$CLONE_DIR/config.json" ] && cp "$CLONE_DIR/config.json" "$FORGE_ROOT/config.json" && log "config.json deployed"
[ -f "$CLONE_DIR/ui-config.json" ] && cp "$CLONE_DIR/ui-config.json" "$FORGE_ROOT/ui-config.json" && log "ui-config.json deployed"

# 4. scripts/, dynamic_prompts/ 배치
mkdir -p /workspace/scripts /workspace/dynamic_prompts
cp "$CLONE_DIR"/scripts/*.sh "$CLONE_DIR"/scripts/*.py /workspace/scripts/ 2>/dev/null
cp "$CLONE_DIR"/dynamic_prompts/* /workspace/dynamic_prompts/ 2>/dev/null
chmod +x /workspace/scripts/*.sh 2>/dev/null
log "scripts/ and dynamic_prompts/ deployed"

# 5. submit_job.py의 포드 URL을 현재 포드 주소로 자동 치환
if [ -f /workspace/scripts/submit_job.py ] && [ -n "${RUNPOD_POD_ID:-}" ]; then
  sed -i "s/[a-z0-9]\{10,\}-3000/${RUNPOD_POD_ID}-3000/g" /workspace/scripts/submit_job.py
  log "submit_job.py pod URL updated to ${RUNPOD_POD_ID}"
else
  log "RUNPOD_POD_ID not set or submit_job.py missing — pod URL in submit_job.py must be fixed manually"
fi

# 6. crontab 5종 등록 (중복 없이)
CRON_ENTRIES=(
  "*/5 * * * * /usr/bin/python3 /workspace/scripts/auto_clean_kernels.py >> /workspace/logs/auto_clean_kernels.log 2>&1"
  "*/10 * * * * /usr/bin/python3 /workspace/scripts/preventive_restart.py >> /workspace/logs/preventive_restart_cron.log 2>&1"
  "@reboot /workspace/scripts/watchdog.sh >> /workspace/logs/watchdog_stdout.log 2>&1"
  "@reboot /workspace/scripts/auto_restore_on_boot.sh >> /workspace/logs/auto_restore.log 2>&1"
  "*/30 * * * * /workspace/scripts/auto_backup_workspace.sh >> /workspace/logs/auto_backup.log 2>&1"
)
current_cron=$(crontab -l 2>/dev/null || true)
new_cron="$current_cron"
for entry in "${CRON_ENTRIES[@]}"; do
  script_name=$(echo "$entry" | grep -oE '/workspace/scripts/[a-zA-Z_]+\.(sh|py)')
  if ! echo "$current_cron" | grep -qF "$script_name"; then
    new_cron="$new_cron
$entry"
  fi
done
echo "$new_cron" | crontab -
log "crontab synced (5 automation entries ensured)"

# 7. auto_restore_on_boot.sh 즉시 1회 실행 (재부팅을 기다리지 않고 바로 복원 시작)
if [ -f /workspace/scripts/auto_restore_on_boot.sh ]; then
  log "running auto_restore_on_boot.sh once now (LoRA/checkpoint/dynamic_prompts restore)"
  bash /workspace/scripts/auto_restore_on_boot.sh
fi

log "=== bootstrap_pod.sh finished ==="
log "다음 단계: rclone이 아직 인증되지 않았다면 'rclone config'로 gdrive를 수동 인증하세요 (BACKUP_AND_RESTORE.md 참고)."
