#!/usr/bin/env python3
"""ComfyUI /prompt 직접 제출 클라이언트.

Chibi 프론트엔드가 steps/CFG 를 잠가 두기 때문에 값을 바꿔 검증하려면
백엔드 API 를 직접 두드리는 수밖에 없다. 이 스크립트가 그 역할을 한다.

  # 1) 설치된 모델/LoRA/샘플러 목록 확인 (잘린 LoRA 이름 복원용)
  python3 comfy_client.py --host https://<tunnel> probe

  # 2) 관측된 세팅 그대로 N장
  python3 comfy_client.py --host https://<tunnel> run -n 20

  # 3) 대조군: 해상도만 바꿔 같은 시드로 비교
  python3 comfy_client.py --host https://<tunnel> run -n 20 --size 1024x1024 --seed-base 1000

Chibi 는 재연결 시 이전 prompt_id 를 다시 구독하지 않아 결과를 놓친다.
여기서는 WebSocket 이 끊겨도 /history/<prompt_id> 로 결과를 회수한다.
"""
import argparse, json, os, re, sys, time, uuid, urllib.parse
import urllib.request

try:
    import websocket  # websocket-client
except ImportError:
    websocket = None


def _req(host, path, data=None, timeout=60):
    url = host.rstrip("/") + path
    body = json.dumps(data).encode() if data is not None else None
    hdr = {"Content-Type": "application/json"} if body else {}
    with urllib.request.urlopen(urllib.request.Request(url, body, hdr), timeout=timeout) as r:
        return json.loads(r.read())


def probe(host):
    info = _req(host, "/object_info")
    def opts(node, key):
        try:
            return info[node]["input"]["required"][key][0]
        except Exception:
            return []
    print("checkpoints:", opts("CheckpointLoaderSimple", "ckpt_name"))
    loras = opts("LoraLoader", "lora_name")
    print("loras: %d개" % len(loras))
    for n in loras:
        if "ANIM" in n.upper() or "달타" in n:
            print("   [일치]", n)
    print("samplers:", opts("KSampler", "sampler_name"))
    print("schedulers:", opts("KSampler", "scheduler"))
    return info


def resolve_lora(host, hint):
    """UI 에서 '달타셀일러_ANIM...' 로 잘린 이름을 실제 파일명으로 복원."""
    info = _req(host, "/object_info")
    loras = info["LoraLoader"]["input"]["required"]["lora_name"][0]
    stem = hint.replace("PLACEHOLDER_", "").split("...")[0].rsplit(".", 1)[0]
    cand = [n for n in loras if n.startswith(stem)]
    if len(cand) == 1:
        return cand[0]
    raise SystemExit("LoRA 확정 불가 (후보 %d개): %s" % (len(cand), cand[:10]))


def build(tpl, positive, negative, w, h, seed, steps, cfg, sampler, sched, lora, batch):
    g = json.loads(json.dumps(tpl))
    g["2"]["inputs"]["lora_name"] = lora
    g["3"]["inputs"]["text"] = positive
    g["4"]["inputs"]["text"] = negative
    g["5"]["inputs"].update(width=w, height=h, batch_size=batch)
    g["6"]["inputs"].update(seed=seed, steps=steps, cfg=cfg,
                            sampler_name=sampler, scheduler=sched)
    return g


def submit(host, graph, client_id):
    return _req(host, "/prompt", {"prompt": graph, "client_id": client_id})["prompt_id"]


def collect(host, prompt_id, outdir, ws=None, timeout=600):
    """WebSocket 이 있으면 진행률을 보여주고, 끊기면 /history 로 회수한다."""
    deadline = time.time() + timeout
    if ws is not None:
        try:
            while time.time() < deadline:
                msg = ws.recv()
                if isinstance(msg, bytes):
                    continue                      # PREVIEW_IMAGE 프레임은 버린다
                ev = json.loads(msg)
                if ev.get("type") == "progress":
                    d = ev["data"]
                    print("\r  %d/%d" % (d["value"], d["max"]), end="", flush=True)
                if (ev.get("type") == "executing"
                        and ev["data"].get("node") is None
                        and ev["data"].get("prompt_id") == prompt_id):
                    break
        except Exception as e:
            print("\n  [ws 끊김: %s] /history 로 회수" % e)
    print()

    hist = {}
    while time.time() < deadline:
        hist = _req(host, "/history/%s" % prompt_id)
        if prompt_id in hist:
            break
        time.sleep(1.0)
    if prompt_id not in hist:
        print("  회수 실패:", prompt_id)
        return []

    saved = []
    for node in hist[prompt_id]["outputs"].values():
        for img in node.get("images", []):
            q = urllib.parse.urlencode(
                {"filename": img["filename"], "subfolder": img.get("subfolder", ""),
                 "type": img.get("type", "output")})
            dst = os.path.join(outdir, img["filename"])
            with urllib.request.urlopen(host.rstrip("/") + "/view?" + q, timeout=120) as r, \
                 open(dst, "wb") as f:
                f.write(r.read())
            saved.append(dst)
    return saved


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", required=True)
    p.add_argument("cmd", choices=["probe", "run"])
    p.add_argument("--workflow", default=os.path.join(os.path.dirname(__file__), "workflow_anima.json"))
    p.add_argument("--positive", default="")
    p.add_argument("--negative", default="")
    p.add_argument("--prompt-file", help="positive/negative 를 담은 JSON")
    p.add_argument("-n", type=int, default=1)
    p.add_argument("--batch", type=int, default=1)
    p.add_argument("--size", default="1536x1536")
    p.add_argument("--steps", type=int, default=16)
    p.add_argument("--cfg", type=float, default=1.0)
    p.add_argument("--sampler", default="er_sde")
    p.add_argument("--scheduler", default="simple")
    p.add_argument("--seed-base", type=int, default=None, help="고정하면 대조군 비교 가능")
    p.add_argument("--out", default="./out")
    a = p.parse_args()

    if a.cmd == "probe":
        probe(a.host)
        return

    tpl = json.load(open(a.workflow))
    if a.prompt_file:
        d = json.load(open(a.prompt_file))
        a.positive, a.negative = d.get("positive", ""), d.get("negative", "")
    if not a.positive:
        sys.exit("--positive 또는 --prompt-file 필요")

    w, h = (int(x) for x in a.size.lower().split("x"))
    lora = resolve_lora(a.host, tpl["2"]["inputs"]["lora_name"])
    print("LoRA 확정:", lora)
    os.makedirs(a.out, exist_ok=True)

    cid = str(uuid.uuid4())
    ws = None
    if websocket is not None:
        try:
            wsurl = re.sub(r"^http", "ws", a.host.rstrip("/")) + "/ws?clientId=" + cid
            ws = websocket.WebSocket()
            ws.connect(wsurl, timeout=30)
        except Exception as e:
            print("[ws 연결 실패, /history 폴링으로 진행: %s]" % e)

    for i in range(a.n):
        seed = (a.seed_base + i) if a.seed_base is not None else uuid.uuid4().int % (2**32)
        g = build(tpl, a.positive, a.negative, w, h, seed,
                  a.steps, a.cfg, a.sampler, a.scheduler, lora, a.batch)
        pid = submit(a.host, g, cid)
        print("[%d/%d] seed=%d %dx%d cfg=%.1f steps=%d -> %s"
              % (i + 1, a.n, seed, w, h, a.cfg, a.steps, pid))
        for f in collect(a.host, pid, a.out, ws):
            print("   저장:", f)

    if ws:
        ws.close()


if __name__ == "__main__":
    main()
