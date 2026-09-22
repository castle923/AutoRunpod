#!/usr/bin/env python3
"""여러 날짜 폴더에 걸친 하나의 배치를 묶어서 zip → Google Drive 업로드.

Forge는 UTC 자정을 넘기면 새 날짜 폴더를 만들고 파일 인덱스를 0부터 다시 시작한다.
그래서 배치 하나가 두 개 이상의 날짜 폴더로 쪼개지고, 날짜 폴더 하나만 받는
finish_project.py로는 뒷부분이 통째로 누락된다. 이 스크립트는 그 경우를 위한 것이다.

핵심 안전장치: 인덱스 범위만 믿지 않고, PNG 메타데이터의 <lora:...> 를 읽어
지정한 캐릭터 LoRA가 실제로 들어있는 파일만 담는다. 범위 안에 다른 프로젝트
이미지가 섞여 있어도 걸러진다.

사용법:
  python3 finish_multiday.py 리코_R_1 --lora 리코3dxl2.0 \
      --spec 2026-09-15:2423 --spec 2026-09-16:0

  --spec 날짜:시작인덱스   (여러 번 지정 가능, 끝 인덱스는 폴더 끝까지)
  --spec 날짜:시작:끝      (끝 인덱스까지만)
  --ext png,jpg            (기본 png — jpg는 같은 이미지의 압축 사본이라 기본 제외)
  --dry-run                실제 zip/업로드 없이 선택 결과만 출력
"""
import argparse
import json
import os
import re
import subprocess
import sys
import zipfile

OUTPUTS_ROOT = "/workspace/stable-diffusion-webui-forge/output/txt2img-images"
RCLONE_CONFIG = "/root/.config/rclone/rclone.conf"
RCLONE_REMOTE = "gdrive:"
MIRROR_DIR = "런포드 백업/압축파일/"


def parse_spec(spec):
    parts = spec.split(":")
    if len(parts) == 2:
        return parts[0], int(parts[1]), None
    if len(parts) == 3:
        return parts[0], int(parts[1]), int(parts[2])
    raise ValueError("--spec 형식은 날짜:시작 또는 날짜:시작:끝 이어야 함: %s" % spec)


def png_loras(path):
    from PIL import Image
    try:
        params = Image.open(path).info.get("parameters", "") or ""
    except Exception:
        return None
    return re.findall(r"<lora:([^:>]+)", params)


def collect(specs, lora, exts):
    """(day, idx, filename) 목록과 거부된 파일 목록을 돌려준다."""
    selected = []
    rejected = []
    for day, start, end in specs:
        day_dir = os.path.join(OUTPUTS_ROOT, day)
        if not os.path.isdir(day_dir):
            print("경고: 폴더 없음 — %s" % day_dir)
            continue
        # 스냅샷: 배치가 아직 돌고 있을 수 있으므로 목록을 한 번만 읽는다
        names = sorted(os.listdir(day_dir))
        ok_idx = set()
        for name in names:
            base, ext = os.path.splitext(name)
            if ext.lower() != ".png":
                continue
            idx_s = base.split("-", 1)[0]
            if not idx_s.isdigit():
                continue
            idx = int(idx_s)
            if idx < start or (end is not None and idx > end):
                continue
            loras = png_loras(os.path.join(day_dir, name))
            if loras is None:
                rejected.append((day, name, "읽기 실패"))
            elif lora in loras:
                ok_idx.add(idx)
            else:
                rejected.append((day, name, ",".join(loras) or "LoRA 없음"))

        for name in names:
            base, ext = os.path.splitext(name)
            if ext.lower().lstrip(".") not in exts:
                continue
            idx_s = base.split("-", 1)[0]
            if not idx_s.isdigit() or int(idx_s) not in ok_idx:
                continue
            selected.append((day, int(idx_s), name))
    return selected, rejected


def build_zip(project_name, selected):
    """arcname 충돌이 있으면 날짜 폴더를 앞에 붙인다."""
    basenames = [n for _, _, n in selected]
    collide = len(set(basenames)) != len(basenames)
    zip_path = "/workspace/%s.zip" % project_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for day, _, name in selected:
            src = os.path.join(OUTPUTS_ROOT, day, name)
            arc = os.path.join(day, name) if collide else name
            zf.write(src, arcname=arc)
    return zip_path, collide


def upload(zip_path, project_name):
    local_size = os.path.getsize(zip_path)
    zip_basename = os.path.basename(zip_path)
    results = {}
    for dest in ["%s%s/" % (RCLONE_REMOTE, project_name), RCLONE_REMOTE + MIRROR_DIR]:
        r = subprocess.run(
            ["rclone", "--config", RCLONE_CONFIG, "copy", zip_path, dest],
            capture_output=True, text=True, timeout=7200,
        )
        if r.returncode != 0:
            results[dest] = {"ok": False, "error": r.stderr[-800:]}
            continue
        s = subprocess.run(
            ["rclone", "--config", RCLONE_CONFIG, "size", dest + zip_basename, "--json"],
            capture_output=True, text=True, timeout=300,
        )
        remote_size = None
        if s.returncode == 0:
            try:
                remote_size = json.loads(s.stdout).get("bytes")
            except Exception:
                pass
        results[dest] = {
            "ok": remote_size == local_size,
            "remote_size": remote_size,
            "local_size": local_size,
        }
    return all(v.get("ok") for v in results.values()), local_size, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_name")
    ap.add_argument("--lora", required=True, help="메타데이터에서 찾을 캐릭터 LoRA 이름")
    ap.add_argument("--spec", action="append", required=True, help="날짜:시작 또는 날짜:시작:끝")
    ap.add_argument("--ext", default="png", help="담을 확장자 (쉼표 구분, 기본 png)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    specs = [parse_spec(s) for s in args.spec]
    exts = {e.strip().lower().lstrip(".") for e in args.ext.split(",") if e.strip()}

    selected, rejected = collect(specs, args.lora, exts)
    per_day = {}
    for day, idx, _ in selected:
        d = per_day.setdefault(day, {"count": 0, "min": idx, "max": idx})
        d["count"] += 1
        d["min"] = min(d["min"], idx)
        d["max"] = max(d["max"], idx)

    print("프로젝트: %s   LoRA: %s   확장자: %s" % (args.project_name, args.lora, ",".join(sorted(exts))))
    for day in sorted(per_day):
        d = per_day[day]
        print("  %s  %d개  idx %05d~%05d" % (day, d["count"], d["min"], d["max"]))
    print("  선택 합계: %d개 / 제외: %d개" % (len(selected), len(rejected)))
    for day, name, why in rejected[:10]:
        print("    제외 %s/%s — %s" % (day, name, why))

    if not selected:
        print("담을 파일이 없음. 중단.")
        return 1
    if args.dry_run:
        return 0

    zip_path, collide = build_zip(args.project_name, selected)
    print("zip 생성: %s (%.2f GB, 날짜폴더 접두사=%s)"
          % (zip_path, os.path.getsize(zip_path) / 1e9, collide))

    ok, size, results = upload(zip_path, args.project_name)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print("업로드 검증: %s" % ("성공 — 원격/로컬 용량 일치" if ok else "실패"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
