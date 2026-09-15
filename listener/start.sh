#!/bin/bash
tmux kill-session -t listener 2>/dev/null
tmux new-session -d -s listener "cd /workspace/listener && python3 server.py 2>&1 | tee -a /workspace/listener/listener.log"
