#!/bin/bash
# 포드 부팅 시 자동 실행: LoRA/체크포인트/설정이 비어있거나 불완전하면 gdrive에서 자동 복원.
# 이미 완전하면(개수 일치) 아무 것도 하지 않고 즉시 종료 — 매 부팅마다 실행해도 안전(idempotent).
#
# crontab에 @reboot로 등록해서 사용:
#   @reboot /workspace/scripts/auto_restore_on_boot.sh >> /workspace/logs/auto_restore.log 2>&1

set -u
LOGDIR=/workspace/logs
mkdir -p "$LOGDIR"
FORGE_ROOT=/workspace/stable-diffusion-webui-forge
LORA_DIR="$FORGE_ROOT/models/Lora"
CKPT_DIR="$FORGE_ROOT/models/Stable-diffusion"
EXPECTED_CKPT="waiNSFWIllustrious_v140.safetensors"

log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" >> "$LOGDIR/auto_restore.log"
}

log "=== auto_restore_on_boot.sh started ==="

# 1. rclone 설정 복구 (없으면)
if [ ! -f /root/.config/rclone/rclone.conf ] && [ -f /workspace/rclone_backup_config/rclone.conf ]; then
  mkdir -p /root/.config/rclone
  cp /workspace/rclone_backup_config/rclone.conf /root/.config/rclone/rclone.conf
  log "rclone.conf restored from /workspace/rclone_backup_config/"
fi

if ! rclone lsd gdrive: > /dev/null 2>&1; then
  log "ERROR: rclone gdrive remote not reachable, aborting auto-restore. Configure rclone manually (see BACKUP_AND_RESTORE.md)."
  exit 1
fi

# 2. LoRA 복원 (개수가 gdrive와 다르면 부족한 것만 채움 — rclone copy는 이미 있는 파일은 건너뜀)
mkdir -p "$LORA_DIR"
local_count=$(find "$LORA_DIR" -type f -iname '*.safetensors' 2>/dev/null | wc -l)
remote_count=$(rclone lsf -R --files-only 'gdrive:런포드 백업/Lora/' 2>/dev/null | grep -c '\.safetensors$')

if [ "$local_count" -lt "$remote_count" ]; then
  log "LoRA count mismatch (local=$local_count, gdrive=$remote_count) — restoring missing files"
  rclone copy 'gdrive:런포드 백업/Lora/' "$LORA_DIR/" --transfers 6 --checkers 8 >> "$LOGDIR/auto_restore.log" 2>&1
  log "LoRA restore copy finished"
else
  log "LoRA already complete (local=$local_count, gdrive=$remote_count) — skipping"
fi

# 3. 체크포인트 복원 (없으면)
mkdir -p "$CKPT_DIR"
if [ ! -f "$CKPT_DIR/$EXPECTED_CKPT" ]; then
  log "checkpoint missing — restoring $EXPECTED_CKPT"
  rclone copy "gdrive:런포드 백업/체크포인트/$EXPECTED_CKPT" "$CKPT_DIR/" --transfers 2 >> "$LOGDIR/auto_restore.log" 2>&1
  log "checkpoint restore finished"
else
  log "checkpoint already present — skipping"
fi

# 4. dynamic_prompts 복원 (없으면)
if [ ! -d /workspace/dynamic_prompts ] || [ -z "$(ls -A /workspace/dynamic_prompts 2>/dev/null)" ]; then
  mkdir -p /workspace/dynamic_prompts
  rclone copy 'gdrive:런포드 백업/dynamic_prompts/' /workspace/dynamic_prompts/ --transfers 2 >> "$LOGDIR/auto_restore.log" 2>&1
  log "dynamic_prompts restored"
else
  log "dynamic_prompts already present — skipping"
fi

# 5. 무결성 검증 (헤더/오프셋) — 문제 있으면 로그에 남기고 조용히 넘어감(자동 삭제/재다운로드는 하지 않음, 사람이 검토)
if [ -f /workspace/scripts/verify_lora_integrity.py ]; then
  python3 /workspace/scripts/verify_lora_integrity.py "$LORA_DIR" >> "$LOGDIR/auto_restore.log" 2>&1
  log "integrity check finished (see log above for corrupted file count)"
fi

log "=== auto_restore_on_boot.sh finished ==="
