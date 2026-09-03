#!/usr/bin/env python3
# 두 종류의 커널 누적을 모두 정리한다:
#   1. 좀비 프로세스: Jupyter API에는 없는데 ipykernel 프로세스만 남은 것 (기존 로직)
#   2. 유휴 등록 커널: API에는 정상 등록돼 있지만(execution_state=idle) 오래 방치된 것.
#      jupyter_exec.py 류의 도구가 호출마다 새 커널을 만들고 절대 닫지 않아서 계속 쌓이는
#      원인이 바로 이것 — 기존 스크립트는 여기를 전혀 건드리지 않아 실제 누적을 못 막았음.
#      idle_minutes 이상 유휴 상태인 것만 DELETE (실행 중이거나 최근 활동은 절대 건드리지 않음).
import subprocess, requests, re
from datetime import datetime, timezone, timedelta

IDLE_MINUTES = 20

try:
    s = requests.Session()
    base_url = "http://127.0.0.1:8888"
    s.get(f"{base_url}/lab", timeout=15)
    xsrf = s.cookies.get("_xsrf")
    headers = {"X-XSRFToken": xsrf} if xsrf else {}
    kr = s.get(f"{base_url}/api/kernels", headers=headers, timeout=15)
    kernels = kr.json()
    active_ids = set(k["id"] for k in kernels)
except Exception as e:
    print("api fetch failed:", e)
    kernels = []
    active_ids = None

ps = subprocess.run(["bash","-lc","pgrep -af ipykernel"], capture_output=True, text=True)
lines = ps.stdout.strip().split("\n") if ps.stdout.strip() else []

if active_ids is not None:
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
        print(f"killed {len(orphan_pids)} orphan kernel process(es)")

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=IDLE_MINUTES)
    deleted = 0
    for k in kernels:
        if k.get("execution_state") != "idle":
            continue
        try:
            last_activity = datetime.fromisoformat(k["last_activity"].replace("Z", "+00:00"))
        except Exception:
            continue
        if last_activity < cutoff:
            r = s.delete(f"{base_url}/api/kernels/{k['id']}", headers=headers, timeout=15)
            if r.status_code in (204, 404):
                deleted += 1
    if deleted:
        print(f"deleted {deleted} idle registered kernel(s) (idle > {IDLE_MINUTES}m)")
