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
EVENT_LOG = os.path.join(LISTENER_DIR, "listener_events.log")

# 컨테이너 메모리 상한 감시.
# 이 포드는 cgroup으로 약 62GB 상한이 걸려 있는데, free(1)은 호스트 전체(251GB)를
# 보여주기 때문에 여유가 있는 것처럼 착각하게 된다. 상한에 닿으면 커널이 Forge를
# SIGKILL로 죽이고, 파이썬 예외가 없어서 로그에는 진행률이 뚝 끊긴 흔적만 남는다.
CGROUP_V1_USAGE = "/sys/fs/cgroup/memory/memory.usage_in_bytes"
CGROUP_V1_LIMIT = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
CGROUP_V1_STAT = "/sys/fs/cgroup/memory/memory.stat"
CGROUP_V2_CURRENT = "/sys/fs/cgroup/memory.current"
CGROUP_V2_MAX = "/sys/fs/cgroup/memory.max"
CGROUP_V2_STAT = "/sys/fs/cgroup/memory.stat"

MEM_WARN_PCT = 80.0
MEM_HIGH_PCT = 90.0
MEM_RESTART_COOLDOWN = 900  # 메모리 사유 재시작 후 최소 대기(초)
NO_LIMIT = 1 << 60
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
    "last_restart_reason": None,
    "restart_storm_stopped": False,
    "batch_completed": False,
    "batch_job": "",
    "batch_progress": 0.0,
    "last_job_nonempty": False,
    "batch_start_idx": None,
    "batch_job_timestamp": None,
    "batch_aborted": False,
    "batch_start_restart_count": 0,
    "mem_usage_gb": None,
    "mem_limit_gb": None,
    "mem_pct": None,
    "mem_peak_pct": 0.0,
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


def forge_stuck(timeout=5):
    """Check if Forge is in a stuck/interrupted state that needs restart."""
    try:
        r = requests.get(FORGE_API, timeout=timeout)
        if r.status_code != 200:
            return False, "not_responding"
        data = r.json()
        interrupted = data.get("state", {}).get("interrupted", False)
        job = data.get("state", {}).get("job", "") or ""
        if interrupted and not job:
            return True, "interrupted_idle"
        return False, "ok"
    except Exception:
        return False, "error"


def log_event(msg):
    try:
        with open(EVENT_LOG, "a") as f:
            f.write("%s %s\n" % (now_iso(), msg))
    except Exception:
        pass


def _read_int(path):
    try:
        raw = open(path).read().strip()
        return None if raw == "max" else int(raw)
    except Exception:
        return None


def _inactive_file(stat_path, key):
    """페이지 캐시 중 회수 가능한 몫. 이걸 빼야 실제 사용량이 나온다."""
    try:
        for line in open(stat_path):
            parts = line.split()
            if len(parts) == 2 and parts[0] == key:
                return int(parts[1])
    except Exception:
        pass
    return 0


def container_memory():
    """(실사용 바이트, 상한 바이트). 알 수 없으면 (None, None).

    usage_in_bytes에는 회수 가능한 페이지 캐시가 포함돼 있어서 그대로 쓰면
    rclone 업로드나 zip 생성 직후 90%를 넘긴 것처럼 보인다. 그래서 inactive_file을
    빼고 working set 기준으로 판단한다.
    """
    if os.path.exists(CGROUP_V1_USAGE):
        usage = _read_int(CGROUP_V1_USAGE)
        limit = _read_int(CGROUP_V1_LIMIT)
        cache = _inactive_file(CGROUP_V1_STAT, "total_inactive_file")
    elif os.path.exists(CGROUP_V2_CURRENT):
        usage = _read_int(CGROUP_V2_CURRENT)
        limit = _read_int(CGROUP_V2_MAX)
        cache = _inactive_file(CGROUP_V2_STAT, "inactive_file")
    else:
        return None, None

    if usage is None or limit is None or limit >= NO_LIMIT:
        return None, None
    return max(usage - cache, 0), limit


def monitor_memory():
    """상한 대비 사용률을 감시한다.

    작업 도중에는 절대 재시작하지 않는다 — 진행 중인 배치를 죽이면 대기열이
    통째로 날아가서, 막으려던 손실을 그대로 일으키게 된다. 대신 경고만 남기고,
    작업이 비어 있는 순간에만 재시작해서 메모리를 회수한다.
    """
    last_mem_restart = 0.0
    warned = False
    while True:
        usage, limit = container_memory()
        if usage is not None:
            pct = usage / limit * 100.0
            state = load_state()
            peak = max(state.get("mem_peak_pct") or 0.0, pct)
            update_state(
                mem_usage_gb=round(usage / 1e9, 2),
                mem_limit_gb=round(limit / 1e9, 2),
                mem_pct=round(pct, 1),
                mem_peak_pct=round(peak, 1),
            )

            if pct >= MEM_WARN_PCT:
                if not warned:
                    log_event("WARN memory %.1f%% (%.1f/%.1f GB) job=%r"
                              % (pct, usage / 1e9, limit / 1e9, state.get("batch_job")))
                    warned = True
            else:
                warned = False

            job = state.get("batch_job") or ""
            if (pct >= MEM_HIGH_PCT and not job
                    and time.time() - last_mem_restart > MEM_RESTART_COOLDOWN):
                log_event("memory %.1f%% and idle — restarting Forge to reclaim" % pct)
                do_restart(reason="memory %.1f%% of container limit while idle" % pct)
                last_mem_restart = time.time()
        time.sleep(30)


def forge_log_active(window=180):
    """Forge 로그가 최근에 쓰였으면 살아서 무언가 하고 있다는 뜻.

    interrupted=True는 고장 신호가 아니다. 설정에서 'Reload UI'를 누르거나
    사용자가 생성을 수동 중단해도 그대로 남고, 다음 작업이 시작될 때까지
    해제되지 않는다. 실제로 UI 재시작 직후 16초 만에 멀쩡한 Forge를 죽인 적이
    있다. 반면 진짜로 고착된 Forge는 아무것도 기록하지 못하므로, 로그 활동
    유무가 둘을 가르는 신호가 된다.
    """
    try:
        return time.time() - os.path.getmtime(FORGE_LOG) < window
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
        last_restart_reason=reason,
        restart_storm_stopped=False,
    )
    return ok, "recovered" if ok else "restart script ran but Forge did not become responsive within 120s"


def monitor_forge_process():
    startup_grace = time.time() + 120
    consecutive_unresponsive = 0
    consecutive_stuck = 0
    consecutive_missing = 0
    UNRESPONSIVE_THRESHOLD = 6
    STUCK_THRESHOLD = 120  # 5초 x 120 = 10분
    MISSING_THRESHOLD = 2

    while True:
        if time.time() < startup_grace:
            time.sleep(5)
            continue

        pid = find_launch_pid()

        if pid is None:
            # psutil.process_iter는 부하가 걸린 순간 대상 프로세스를 놓치거나
            # AccessDenied로 건너뛸 수 있다. 여기서 바로 재시작하면 멀쩡히 배치를
            # 돌리던 Forge를 죽이게 되므로, API 응답으로 한 번 더 확인한다.
            if forge_responsive(timeout=5):
                log_event("PID를 찾지 못했지만 API가 응답함 — 재시작 보류(오탐)")
                consecutive_missing = 0
                time.sleep(5)
                continue
            consecutive_missing += 1
            if consecutive_missing >= MISSING_THRESHOLD:
                consecutive_unresponsive = 0
                consecutive_stuck = 0
                consecutive_missing = 0
                do_restart(reason="process missing")
                startup_grace = time.time() + 120
            time.sleep(5)
            continue
        consecutive_missing = 0

        if not forge_responsive(timeout=5):
            consecutive_unresponsive += 1
            if consecutive_unresponsive >= UNRESPONSIVE_THRESHOLD:
                do_restart(reason=f"API unresponsive for {consecutive_unresponsive * 5}s")
                consecutive_unresponsive = 0
                consecutive_stuck = 0
                startup_grace = time.time() + 120
        else:
            consecutive_unresponsive = 0

        stuck, stuck_reason = forge_stuck(timeout=5)
        if stuck and forge_log_active():
            if consecutive_stuck:
                log_event("stuck 후보였으나 Forge 로그 활동 감지 — 카운터 초기화")
            stuck = False
            consecutive_stuck = 0

        if stuck:
            consecutive_stuck += 1
            if consecutive_stuck == 1:
                log_event("stuck 후보 관측 시작 (%s) — %d초간 지속되면 재시작"
                          % (stuck_reason, STUCK_THRESHOLD * 5))
            if consecutive_stuck >= STUCK_THRESHOLD:
                do_restart(reason=f"stuck state: {stuck_reason} for {consecutive_stuck * 5}s")
                consecutive_stuck = 0
                consecutive_unresponsive = 0
                startup_grace = time.time() + 120
        else:
            consecutive_stuck = 0

        time.sleep(5)


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
                    updates["batch_aborted"] = False
                    updates["batch_start_idx"] = start_idx
                    updates["batch_job_timestamp"] = job_ts
                    updates["batch_start_restart_count"] = state.get("restart_count", 0)
                elif job_nonempty:
                    updates["batch_completed"] = False
                elif was_nonempty and not job_nonempty:
                    # 작업이 비었다고 해서 다 끝난 게 아니다. Forge가 재시작되면
                    # 대기열이 통째로 사라지면서 똑같이 "유휴"로 보인다. 배치가 도는
                    # 동안 재시작이 있었는지로 둘을 구분한다 — 이걸 구분하지 못해
                    # 리코 배치가 83/100에서 끊긴 걸 완료로 오판한 적이 있다.
                    aborted = state.get("restart_count", 0) > state.get("batch_start_restart_count", 0)
                    updates["batch_completed"] = True
                    updates["batch_aborted"] = aborted
                    log_event("배치 종료 — %s (job=%r)"
                              % ("재시작으로 중단됨" if aborted else "정상 완료", job_ts))

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
        "batch_aborted": state.get("batch_aborted"),
        "batch_start_idx": state.get("batch_start_idx"),
        "batch_job_timestamp": state.get("batch_job_timestamp"),
        "last_crash_time": state.get("last_crash_time"),
        "restart_count": state.get("restart_count"),
        "last_restart_reason": state.get("last_restart_reason"),
        "restart_storm_stopped": state.get("restart_storm_stopped"),
        "mem_usage_gb": state.get("mem_usage_gb"),
        "mem_limit_gb": state.get("mem_limit_gb"),
        "mem_pct": state.get("mem_pct"),
        "mem_peak_pct": state.get("mem_peak_pct"),
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
    threading.Thread(target=monitor_memory, daemon=True).start()

    app.run(host="0.0.0.0", port=5000, threaded=True)


if __name__ == "__main__":
    main()
