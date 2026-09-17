#!/usr/bin/env python3
"""배치 완료를 기다렸다가 자동으로 묶어 Google Drive에 업로드한다.

리스너(/status)를 주기적으로 확인하다가 작업이 비고 batch_completed 가 서면
finish_multiday.py 를 실행한다.

중요한 안전장치가 하나 있다. Forge가 재시작되면 대기열이 통째로 사라지면서
작업이 비어 정상 완료와 똑같이 보인다. 실제로 리코 배치가 83/100에서 끊긴 것을
완료로 오판해 미완성본을 드라이브에 올린 적이 있다. 그래서 리스너가 노출하는
batch_aborted 를 함께 확인해, 중단으로 끝난 경우에는 업로드하지 않고 로그에
경보만 남기고 종료한다 — 사람이 판단할 일이기 때문이다.

사용법:
  python3 auto_finish_watcher.py 테리_R_1 --lora 오버더월-테리1 \
      --spec 2026-09-16:437 --spec 2026-09-17:0

  배치가 UTC 자정을 넘길 가능성이 있으면 다음 날짜도 --spec 으로 함께 넘긴다.
  실제로 담기는 파일은 PNG 메타데이터의 <lora:...> 로 걸러지므로, 해당 날짜에
  다른 프로젝트 이미지가 있어도 섞이지 않는다.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.request

STATUS_URL = "http://localhost:5000/status"
RESTART_URL = "http://localhost:5000/restart"
FINISH = "/workspace/scripts/finish_multiday.py"
IDLE_CONFIRMATIONS = 3
POLL_SECONDS = 120


def restart_forge(log):
    """업로드 검증이 끝난 뒤 Forge를 재시작해 메모리를 회수한다.

    배치 한 번(2시간)에 메모리가 20%p 가까이 오르고 끝나도 내려오지 않는다.
    다음 배치가 그 위에서 출발하면 상한(62GB)까지의 거리가 그만큼 줄어든다.
    재시작 비용은 기동 15초 + 첫 모델 로드 11초로 2시간 배치의 0.3% 수준이고,
    회수량은 20GB 이상이라 교환비가 크게 유리하다.

    업로드가 끝난 뒤로 미루는 이유는 두 가지다. 후처리가 출력 파일을 읽는
    도중에 끊지 않기 위해서고, 배치를 곧바로 이어 시작하는 경우와 부딪히지
    않기 위해서다. 그래서 재시작 직전에 작업이 비어 있는지 한 번 더 확인하고,
    새 배치가 이미 시작됐으면 건드리지 않는다.
    """
    try:
        with urllib.request.urlopen(STATUS_URL, timeout=10) as r:
            s = json.load(r)
    except Exception as e:
        log("재시작 전 상태 확인 실패, 건너뜀: %r" % e)
        return

    job = s.get("batch_job") or ""
    if job:
        log("새 배치가 이미 시작됨(%s) — 재시작하지 않음" % job)
        return

    before = s.get("mem_usage_gb")
    log("업로드 검증 완료, 유휴 확인 — Forge 재시작 (현재 메모리 %.2fGB)" % (before or 0.0))
    try:
        req = urllib.request.Request(RESTART_URL, data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:
            log("재시작 응답: %s" % r.read().decode()[:200])
    except Exception as e:
        log("재시작 요청 실패: %r" % e)
        return

    try:
        time.sleep(10)
        with urllib.request.urlopen(STATUS_URL, timeout=10) as r:
            after = json.load(r).get("mem_usage_gb")
        log("메모리 %.2fGB -> %.2fGB" % (before or 0.0, after or 0.0))
    except Exception as e:
        log("재시작 후 확인 실패: %r" % e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_name")
    ap.add_argument("--lora", required=True, help="메타데이터에서 찾을 캐릭터 LoRA 이름")
    ap.add_argument("--spec", action="append", required=True, help="날짜:시작[:끝]")
    ap.add_argument("--log", default=None, help="로그 경로 (기본: /workspace/logs/<project>_autofinish.log)")
    ap.add_argument("--poll", type=int, default=POLL_SECONDS)
    ap.add_argument("--no-restart-after", action="store_true",
                    help="업로드 검증 후 Forge를 재시작하지 않는다")
    args = ap.parse_args()

    log_path = args.log or "/workspace/logs/%s_autofinish.log" % args.project_name

    def log(msg):
        line = "%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), msg)
        with open(log_path, "a") as f:
            f.write(line)

    log("watcher started  project=%s lora=%s specs=%s" % (args.project_name, args.lora, args.spec))
    idle = 0
    while True:
        try:
            with urllib.request.urlopen(STATUS_URL, timeout=10) as r:
                s = json.load(r)
            job = s.get("batch_job") or ""
            done = s.get("batch_completed")
            aborted = s.get("batch_aborted")

            if done and not job:
                idle += 1
                log("idle %d/%d (aborted=%s)" % (idle, IDLE_CONFIRMATIONS, aborted))
            else:
                if idle:
                    log("유휴 연속 초기화, job=%s" % job)
                idle = 0
                log("진행 중: %s (mem %.1f%%)" % (job, s.get("mem_pct") or 0.0))

            if idle >= IDLE_CONFIRMATIONS:
                if aborted:
                    log("!! 배치가 재시작으로 중단됨 — 업로드하지 않음. 사람이 확인 필요 "
                        "(last_restart_reason=%s)" % s.get("last_restart_reason"))
                    return 2
                log("정상 완료 확인 — finish_multiday 실행")
                cmd = ["python3", FINISH, args.project_name, "--lora", args.lora]
                for sp in args.spec:
                    cmd += ["--spec", sp]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=14400)
                log("stdout:\n" + r.stdout)
                if r.stderr:
                    log("stderr:\n" + r.stderr[-2000:])
                log("watcher done rc=%d" % r.returncode)
                if r.returncode == 0 and not args.no_restart_after:
                    restart_forge(log)
                return r.returncode
        except Exception as e:
            log("error: %r" % e)
        time.sleep(args.poll)


if __name__ == "__main__":
    sys.exit(main())
