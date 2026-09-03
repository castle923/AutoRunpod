#!/bin/bash
LOGDIR=/workspace/logs
mkdir -p "$LOGDIR"
while true; do
  if [ ! -f /root/.config/rclone/rclone.conf ] && [ -f /workspace/rclone_backup_config/rclone.conf ]; then
    mkdir -p /root/.config/rclone
    cp /workspace/rclone_backup_config/rclone.conf /root/.config/rclone/rclone.conf
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) rclone.conf restored from persistent backup" >> "$LOGDIR/watchdog_auto.log"
  fi
  if ! curl -sS --max-time 5 -o /dev/null http://127.0.0.1:3001/sdapi/v1/progress; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Forge down, restarting..." >> "$LOGDIR/watchdog_auto.log"
    pkill -9 -f "launch.py --port 3001" 2>/dev/null
    sleep 2
    cd /workspace/stable-diffusion-webui-forge
    export COMMANDLINE_ARGS="--port 3001 --listen --api --xformers --enable-insecure-extension-access --no-half-vae"
    ts=$(date +%s)
    setsid env -u MPLBACKEND /workspace/venvs/stable-diffusion-webui-forge/bin/python3 launch.py $COMMANDLINE_ARGS \
      > "$LOGDIR/forge_auto_${ts}.log" 2>&1 < /dev/null &
    sleep 60
  fi
  sleep 15
done
