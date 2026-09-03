#!/bin/bash
# /workspace에서 "중요하지만 아직 gdrive/GitHub에 반영 안 됐을 수 있는" 파일들을 주기적으로
# gdrive에 스냅샷 백업한다. 대용량 모델/venv는 대상이 아님(이미 별도 경로로 관리됨).
#
# 대상:
#   - /workspace 바로 아래의 느슨한 파일들 (*.ipynb, *.py, *.sh, *.txt, *.json 등 — 작업 중 만든 잡다한 파일)
#   - /workspace/scripts/, /workspace/dynamic_prompts/, config.json, ui-config.json (최신 상태 유지)
#   - /workspace/logs/*.log (최근 크래시/작업 이력 — 디버깅용)
#
# crontab에 30분마다 등록해서 사용:
#   */30 * * * * /workspace/scripts/auto_backup_workspace.sh >> /workspace/logs/auto_backup.log 2>&1

set -u
LOGDIR=/workspace/logs
mkdir -p "$LOGDIR"
FORGE_ROOT=/workspace/stable-diffusion-webui-forge
DEST="gdrive:런포드 백업/workspace_snapshot"

log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" >> "$LOGDIR/auto_backup.log"
}

log "=== auto_backup_workspace.sh started ==="

if ! rclone lsd gdrive: > /dev/null 2>&1; then
  log "ERROR: rclone gdrive remote not reachable, skipping this cycle."
  exit 1
fi

# 1. /workspace 바로 아래 느슨한 파일들 (하위 폴더 제외, 파일만)
mkdir -p /tmp/workspace_loose_files
rm -f /tmp/workspace_loose_files/* 2>/dev/null
find /workspace -maxdepth 1 -type f \( -iname "*.ipynb" -o -iname "*.py" -o -iname "*.sh" \
  -o -iname "*.txt" -o -iname "*.json" -o -iname "*.md" \) -exec cp {} /tmp/workspace_loose_files/ \;
loose_count=$(ls /tmp/workspace_loose_files/ 2>/dev/null | wc -l)
if [ "$loose_count" -gt 0 ]; then
  rclone copy /tmp/workspace_loose_files/ "$DEST/loose_files/" --transfers 4 >> "$LOGDIR/auto_backup.log" 2>&1
  log "backed up $loose_count loose file(s) from /workspace root"
else
  log "no loose files at /workspace root to back up"
fi

# 2. 스크립트/설정/dynamic_prompts (최신 상태로 계속 덮어쓰기 — 원본은 이 폴더들이므로 손실 위험 없음)
[ -d /workspace/scripts ] && rclone copy /workspace/scripts/ "$DEST/scripts/" --transfers 4 >> "$LOGDIR/auto_backup.log" 2>&1
[ -d /workspace/dynamic_prompts ] && rclone copy /workspace/dynamic_prompts/ "$DEST/dynamic_prompts/" --transfers 2 >> "$LOGDIR/auto_backup.log" 2>&1
[ -f "$FORGE_ROOT/config.json" ] && rclone copyto "$FORGE_ROOT/config.json" "$DEST/config.json" >> "$LOGDIR/auto_backup.log" 2>&1
[ -f "$FORGE_ROOT/ui-config.json" ] && rclone copyto "$FORGE_ROOT/ui-config.json" "$DEST/ui-config.json" >> "$LOGDIR/auto_backup.log" 2>&1
log "scripts/config/dynamic_prompts synced"

# 3. 최근 로그 (디버깅용, 최근 것만)
if [ -d /workspace/logs ]; then
  rclone copy /workspace/logs/ "$DEST/logs/" --transfers 4 --max-age 24h >> "$LOGDIR/auto_backup.log" 2>&1
  log "recent logs (last 24h) synced"
fi

log "=== auto_backup_workspace.sh finished ==="
