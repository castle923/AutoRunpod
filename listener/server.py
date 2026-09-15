import os
import io
import json
import time
import glob
import zipfile
import threading
import subprocess
from datetime import datetime, timezone

import psutil
import requests
from flask import Flask, jsonify, request

LISTENER_DIR = "/workspace/listener"
STATE_PATH = os.path.join(LISTENER_DIR, "state.json")
FORGE_API = "http://localhost:3001/sdapi/v1/progress?skip_current_image=true"
RESTART_SCRIPT = "/workspace/restart_forge_clean.sh"
FORGE_LOG = "/workspace/logs/forge_new.log"
OUTPUTS_ROOT = "/workspace/stable-diffusion-webui-forge/output/txt2img-images"
RCLONE_CONFIG = "/workspace/rclone.conf"
RCLONE_REMOTE = "gdrive:"

app = Flask(__name__)
STATE_LOCK = threading.Lock()
START_TIME = time.time()

DEFAULT_STATE = {
    "restart_count": 0,
    "restart_times": [],
    "last_crash_time": None,
    "last_restart_ok": None,
    "restart_storm_stopped": False,
    "batch_completed": False,
    "batch_job": "",
    "batch_progress": 0.0,
    "last_job_nonempty": False,
    "batch_start_idx": None,
    "batch_job_timestamp": None,
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_state():
    if not os.path.exists(STATE_PATH):
        return dict(DEFAULT_STATE)
    try:
        with open(STATE_PATH, "r") as f:
            data = json.load(f)
        merged = dict(DEFAULT_STATE)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_STATE)


def save_state(state):
    tmp_path = STATE_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp_path, STATE_PATH)


def update_state(**kwargs):
    with STATE_LOCK:
        state = load_state()
        state.update(kwargs)
        save_state(state)
        return state


def find_launch_pid():
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if any("launch.py" in part for part in cmdline):
                return proc.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def forge_responsive(timeout=5):
    try:
        r = requests.get(FORGE_API, timeout=timeout)
        return r.status_code == 200 and '"progress"' in r.text
    except Exception:
        return False


def do_restart(reason="auto"):
    """Runs the restart sequence. Returns (ok: bool, message: str)."""
    state = load_state()
    now = time.time()
    recent = [t for t in state.get("restart_times", []) if now - t < 300]

    if len(recent) >= 3:
        update_state(
            restart_storm_stopped=True,
            last_crash_time=now_iso(),
        )
        return False, "restart storm: 3+ restarts within 5 minutes, stopping auto-restart"

    try:
        if os.path.exists(FORGE_LOG):
            ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            crash_log = f"/workspace/logs/forge-crash-{ts}.log"
            subprocess.run(["mv", "-f", FORGE_LOG, crash_log], check=False)

        subprocess.Popen(
            ["setsid", RESTART_SCRIPT],
            stdout=open(FORGE_LOG, "a"),
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        update_state(
            restart_times=recent + [now],
            restart_count=state.get("restart_count", 0) + 1,
            last_crash_time=now_iso(),
            last_restart_ok=False,
        )
        return False, f"failed to launch restart script: {e}"

    ok = False
    deadline = now + 120
    while time.time() < deadline:
        if forge_responsive(timeout=5):
            ok = True
            break
        time.sleep(3)

    update_state(
        restart_times=recent + [now],
        restart_count=state.get("restart_count", 0) + 1,
        last_crash_time=now_iso(),
        last_restart_ok=ok,
        restart_storm_stopped=False,
    )
    return ok, "recovered" if ok else "restart script ran but Forge did not become responsive within 120s"


def monitor_forge_process():
    while True:
        pid = find_launch_pid()
        if pid is None:
            do_restart(reason="process missing")
        time.sleep(2)


def _current_max_idx():
    """Return the highest image index in today's output folder, or -1."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    outdir = os.path.join(OUTPUTS_ROOT, today)
    if not os.path.isdir(outdir):
        return -1
    max_idx = -1
    for name in os.listdir(outdir):
        m = name.split("-", 1)
        if len(m) >= 1:
            try:
                idx = int(m[0])
                if idx > max_idx:
                    max_idx = idx
            except ValueError:
                pass
    return max_idx


def monitor_batch_progress():
    while True:
        try:
            r = requests.get(FORGE_API, timeout=5)
            if r.status_code == 200 and '"progress"' in r.text:
                data = r.json()
                job = data.get("state", {}).get("job", "") or ""
                job_ts = data.get("state", {}).get("job_timestamp", "") or ""
                progress = data.get("progress", 0.0) or 0.0
                state = load_state()
                was_nonempty = state.get("last_job_nonempty", False)
                job_nonempty = bool(job)

                updates = {
                    "batch_job": job,
                    "batch_progress": progress,
                    "last_job_nonempty": job_nonempty,
                }

                if job_nonempty and not was_nonempty:
                    start_idx = _current_max_idx() + 1
                    updates["batch_completed"] = False
                    updates["batch_start_idx"] = start_idx
                    updates["batch_job_timestamp"] = job_ts
                elif job_nonempty:
                    updates["batch_completed"] = False
                elif was_nonempty and not job_nonempty:
                    updates["batch_completed"] = True

                update_state(**updates)
        except Exception:
            pass
        time.sleep(5)


def build_zip(project_name, date_folder, start_idx, end_idx):
    outdir = os.path.join(OUTPUTS_ROOT, date_folder)
    files = sorted(glob.glob(os.path.join(outdir, "*")))
    selected = []
    for f in files:
        base = os.path.basename(f)
        idx_str = base.split("-", 1)[0]
        try:
            idx = int(idx_str)
        except ValueError:
            continue
        if idx < start_idx:
            continue
        if end_idx is not None and idx > end_idx:
            continue
        selected.append(f)

    if not selected:
        return None, 0

    zip_path = f"/workspace/{project_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in selected:
            zf.write(f, arcname=os.path.basename(f))

    return zip_path, len(selected)


def rclone_upload_and_verify(zip_path, project_name):
    local_size = os.path.getsize(zip_path)
    zip_basename = os.path.basename(zip_path)
    destinations = [
        f"{RCLONE_REMOTE}{project_name}/",
        f"{RCLONE_REMOTE}런포드 백업/압축파일/",
    ]

    results = {}
    for dest in destinations:
        r = subprocess.run(
            ["rclone", "--config", RCLONE_CONFIG, "copy", zip_path, dest],
            capture_output=True, text=True, timeout=1800,
        )
        if r.returncode != 0:
            results[dest] = {"ok": False, "error": r.stderr[-1000:]}
            continue

        size_out = subprocess.run(
            ["rclone", "--config", RCLONE_CONFIG, "size", dest + zip_basename, "--json"],
            capture_output=True, text=True, timeout=120,
        )
        remote_size = None
        if size_out.returncode == 0:
            try:
                remote_size = json.loads(size_out.stdout).get("bytes")
            except Exception:
                remote_size = None

        results[dest] = {
            "ok": remote_size == local_size,
            "remote_size": remote_size,
            "local_size": local_size,
        }

    all_ok = all(v.get("ok") for v in results.values())
    return all_ok, local_size, results


@app.route("/health", methods=["GET"])
def health():
    return "ok"


@app.route("/status", methods=["GET"])
def status():
    state = load_state()
    pid = find_launch_pid()
    return jsonify({
        "forge_alive": pid is not None,
        "forge_pid": pid,
        "batch_progress": state.get("batch_progress"),
        "batch_job": state.get("batch_job"),
        "batch_completed": state.get("batch_completed"),
        "batch_start_idx": state.get("batch_start_idx"),
        "batch_job_timestamp": state.get("batch_job_timestamp"),
        "last_crash_time": state.get("last_crash_time"),
        "restart_count": state.get("restart_count"),
        "restart_storm_stopped": state.get("restart_storm_stopped"),
        "uptime_seconds": round(time.time() - START_TIME, 1),
    })


@app.route("/restart", methods=["POST"])
def restart():
    ok, message = do_restart(reason="manual")
    return jsonify({"ok": ok, "message": message}), (200 if ok else 500)


@app.route("/upload", methods=["POST"])
def upload():
    body = request.get_json(force=True, silent=True) or {}
    project_name = body.get("project_name")
    date_folder = body.get("date_folder")
    start_idx = body.get("start_idx")
    end_idx = body.get("end_idx")

    if not project_name or not date_folder or start_idx is None:
        return jsonify({"ok": False, "error": "project_name, date_folder, start_idx are required"}), 400

    try:
        start_idx = int(start_idx)
        end_idx = int(end_idx) if end_idx is not None else None
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "start_idx/end_idx must be integers"}), 400

    zip_path, count = build_zip(project_name, date_folder, start_idx, end_idx)
    if zip_path is None:
        return jsonify({"ok": False, "error": "no matching images found"}), 404

    ok, local_size, results = rclone_upload_and_verify(zip_path, project_name)
    return jsonify({
        "ok": ok,
        "project_name": project_name,
        "image_count": count,
        "zip_path": zip_path,
        "local_size": local_size,
        "upload_results": results,
    }), (200 if ok else 500)


def main():
    os.makedirs(LISTENER_DIR, exist_ok=True)
    if not os.path.exists(STATE_PATH):
        save_state(dict(DEFAULT_STATE))

    threading.Thread(target=monitor_forge_process, daemon=True).start()
    threading.Thread(target=monitor_batch_progress, daemon=True).start()

    app.run(host="0.0.0.0", port=5000, threaded=True)


if __name__ == "__main__":
    main()
