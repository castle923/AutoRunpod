#!/usr/bin/env python3
import subprocess, requests, re

try:
    s = requests.Session()
    base_url = "http://127.0.0.1:8888"
    s.get(f"{base_url}/lab", timeout=15)
    kr = s.get(f"{base_url}/api/kernels", timeout=15)
    kernels = kr.json()
    active_ids = set(k["id"] for k in kernels)
except Exception as e:
    print("api fetch failed:", e)
    active_ids = None

ps = subprocess.run(["bash","-lc","pgrep -af ipykernel"], capture_output=True, text=True)
lines = ps.stdout.strip().split("\n") if ps.stdout.strip() else []

if active_ids is None:
    exit(0)

orphan_pids = []
for line in lines:
    m = re.search(r"-f\s+(\S+kernel-([0-9a-f-]+)\.json)", line)
    pid = line.split()[0]
    if m:
        kid = m.group(2)
        if kid not in active_ids:
            orphan_pids.append(pid)
    else:
        orphan_pids.append(pid)

if orphan_pids:
    subprocess.run(["bash","-lc", "kill -9 " + " ".join(orphan_pids)], capture_output=True, text=True)
    print(f"killed {len(orphan_pids)} orphan kernels")
