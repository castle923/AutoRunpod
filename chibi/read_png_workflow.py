#!/usr/bin/env python3
"""ComfyUI / A1111 출력 PNG 에서 생성 정보를 뽑아낸다.

포드가 죽어 있어도 PNG 한 장이면 UI 에서 잘려 보이던 LoRA 전체 파일명과
실제 사용된 seed 를 복원할 수 있다. ComfyUI 는 워크플로 JSON 을 통째로
tEXt 청크(prompt / workflow)에 넣고, A1111 은 parameters 에 텍스트로 넣는다.

  python3 read_png_workflow.py IMG.png            # 요약
  python3 read_png_workflow.py IMG.png --raw      # 원본 JSON 전문
  python3 read_png_workflow.py *.png --summary    # 여러 장 한 줄 요약
"""
import argparse, json, struct, sys, zlib


def png_text_chunks(path):
    """PNG 의 tEXt / zTXt / iTXt 청크를 {키: 값} 으로 읽는다."""
    out = {}
    with open(path, "rb") as f:
        if f.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError("PNG 가 아님: %s" % path)
        while True:
            head = f.read(8)
            if len(head) < 8:
                break
            ln, typ = struct.unpack(">I4s", head)
            body = f.read(ln)
            f.read(4)                                   # CRC
            try:
                if typ == b"tEXt":
                    k, v = body.split(b"\x00", 1)
                    out[k.decode("latin-1")] = v.decode("utf-8", "replace")
                elif typ == b"zTXt":
                    k, rest = body.split(b"\x00", 1)
                    out[k.decode("latin-1")] = zlib.decompress(rest[1:]).decode("utf-8", "replace")
                elif typ == b"iTXt":
                    k, rest = body.split(b"\x00", 1)
                    comp = rest[0]
                    rest = rest[2:].split(b"\x00", 1)[1].split(b"\x00", 1)[1]
                    out[k.decode("latin-1")] = (zlib.decompress(rest) if comp else rest
                                                ).decode("utf-8", "replace")
            except Exception:
                pass                                    # 깨진 청크는 건너뛴다
            if typ == b"IEND":
                break
    return out


def parse_comfy(graph):
    """워크플로 그래프에서 관심 있는 값만 추려낸다."""
    r = {"ckpt": None, "unet": None, "clip": None, "vae": None, "loras": [], "positive": None, "negative": None, "sampler": {}, "size": None}
    ks = None
    for node in graph.values():
        if not isinstance(node, dict):
            continue
        ct, ins = node.get("class_type"), node.get("inputs", {})
        if ct == "CheckpointLoaderSimple":
            r["ckpt"] = ins.get("ckpt_name")
        elif ct in ("UNETLoader", "UNETLoaderGGUF"):
            r["unet"] = ins.get("unet_name")
        elif ct in ("CLIPLoader", "DualCLIPLoader"):
            r["clip"] = ins.get("clip_name") or ins.get("clip_name1")
        elif ct == "VAELoader":
            r["vae"] = ins.get("vae_name")
        elif ct in ("LoraLoader", "LoraLoaderModelOnly"):
            r["loras"].append({"name": ins.get("lora_name"),
                               "model": ins.get("strength_model"),
                               "clip": ins.get("strength_clip")})
        elif ct in ("EmptyLatentImage", "EmptySD3LatentImage"):
            r["size"] = "%sx%s" % (ins.get("width"), ins.get("height"))
        elif ct in ("KSampler", "KSamplerAdvanced"):
            ks = node
            r["sampler"] = {k: ins.get(k) for k in
                            ("seed", "noise_seed", "steps", "cfg", "sampler_name", "scheduler", "denoise")
                            if ins.get(k) is not None}

    # KSampler 의 positive/negative 링크를 따라가 실제 프롬프트 텍스트를 찾는다
    if ks:
        for slot in ("positive", "negative"):
            ref = ks["inputs"].get(slot)
            if isinstance(ref, list) and ref and str(ref[0]) in graph:
                r[slot] = graph[str(ref[0])].get("inputs", {}).get("text")
    return r


def report(path, raw=False, summary=False):
    ch = png_text_chunks(path)

    if "prompt" in ch or "workflow" in ch:
        try:
            graph = json.loads(ch.get("prompt") or ch["workflow"])
        except Exception as e:
            print("%s: 워크플로 JSON 파싱 실패 (%s)" % (path, e)); return
        if raw:
            print(json.dumps(graph, ensure_ascii=False, indent=2)); return
        d = parse_comfy(graph)
        if summary:
            s = d["sampler"]
            print("%s | %s | %s | seed=%s | %s" % (
                path, d["ckpt"],
                ",".join(l["name"] or "?" for l in d["loras"]) or "-",
                s.get("seed", s.get("noise_seed")), d["size"]))
            return
        print("=== %s  [ComfyUI]" % path)
        if d["ckpt"]:
            print("  checkpoint :", d["ckpt"])
        else:
            print("  (분리 파일 구성)")
            for k, lbl in (("unet", "unet"), ("clip", "text encoder"), ("vae", "vae")):
                if d[k]:
                    print("  %-10s : %s" % (lbl, d[k]))
        for l in d["loras"]:
            print("  lora       : %s  (model %s / clip %s)" % (l["name"], l["model"], l["clip"]))
        if not d["loras"]:
            print("  lora       : 없음")
        print("  size       :", d["size"])
        for k, v in d["sampler"].items():
            print("  %-10s : %s" % (k, v))
        for slot in ("positive", "negative"):
            t = d[slot]
            if t:
                print("  %-10s : %s" % (slot, t if len(t) < 300 else t[:300] + " …(%d자)" % len(t)))

    elif "parameters" in ch:
        if raw or not summary:
            print("=== %s  [A1111/Forge]" % path)
            print(ch["parameters"] if raw else ch["parameters"][:1200])
        else:
            print("%s | A1111 | %s" % (path, ch["parameters"].splitlines()[-1][:120]))
    else:
        print("%s: 생성 정보 없음 (청크: %s)" % (path, ", ".join(ch) or "없음"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+")
    p.add_argument("--raw", action="store_true", help="워크플로 JSON 전문 출력")
    p.add_argument("--summary", action="store_true", help="파일당 한 줄")
    a = p.parse_args()
    for f in a.files:
        try:
            report(f, a.raw, a.summary)
        except Exception as e:
            print("%s: %s" % (f, e), file=sys.stderr)


if __name__ == "__main__":
    main()
