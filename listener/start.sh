#!/bin/bash
# Start listener server in tmux with auto-restart loop.
# If the listener process crashes, it restarts automatically after 3 seconds.
tmux kill-session -t listener 2>/dev/null
tmux new-session -d -s listener "while true; do cd /workspace/listener && python3 server.py 2>&1 | tee -a /workspace/listener/listener.log; echo \"\$(date -u +%Y-%m-%dT%H:%M:%SZ) listener exited, restarting in 3s...\" >> /workspace/listener/listener.log; sleep 3; done"
