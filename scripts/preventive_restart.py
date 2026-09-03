#!/usr/bin/env python3
import requests, subprocess, time, os

LOGDIR = "/workspace/logs"
STATE_FILE = "/workspace/logs/last_preventive_restart.txt"
RESTART_INTERVAL_SEC = 5 * 3600  # 5 hours

def log(msg):
    with open(f"{LOGDIR}/preventive_restart.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")

def get_last_restart():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return float(f.read().strip())
    return time.time()  # first run: treat as just restarted, don't restart immediately

def set_last_restart(ts):
    with open(STATE_FILE, "w") as f:
        f.write(str(ts))

last = get_last_restart()
now = time.time()
elapsed = now - last

if elapsed < RESTART_INTERVAL_SEC:
    exit(0)

try:
    r = requests.get("http://127.0.0.1:3001/sdapi/v1/progress?skip_current_image=true", timeout=10)
    job = r.json().get("state", {}).get("job", "")
except Exception as e:
    log(f"could not check progress, skipping this cycle: {e}")
    exit(0)

if job != "":
    log(f"restart due ({elapsed/3600:.1f}h since last) but job in progress ('{job}') - deferring")
    exit(0)

log(f"restart due ({elapsed/3600:.1f}h since last), job idle - performing preventive restart")
subprocess.run(["bash","-lc","pkill -9 -f \"launch.py --port 3001\""])
time.sleep(3)
subprocess.run(["bash","-lc",
    "cd /workspace/stable-diffusion-webui-forge && "
    "export COMMANDLINE_ARGS=\"--port 3001 --listen --api --xformers --enable-insecure-extension-access --no-half-vae\" && "
    f"ts=$(date +%s) && setsid env -u MPLBACKEND /workspace/venvs/stable-diffusion-webui-forge/bin/python3 launch.py $COMMANDLINE_ARGS > {LOGDIR}/forge_auto_$ts.log 2>&1 < /dev/null &"
])
set_last_restart(now)
log("preventive restart triggered")
