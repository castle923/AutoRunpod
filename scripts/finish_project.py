#!/usr/bin/env python3
"""
프로젝트 완료 표준 처리 스크립트.
baseline 이후 생성된 이미지를 zip으로 압축하고, gdrive:<project>/ 에 업로드,
런포드 백업/압축파일/ 에도 미러링한 뒤 결과를 검증한다.

사용법:
    python3 finish_project.py <project_name> <date_folder> <baseline_index> \
        [--outputs-dir /workspace/stable-diffusion-webui-forge/output/txt2img-images] \
        [--transfers 4]

예시:
    python3 finish_project.py 후야_r_18 2026-09-03 0
"""
import argparse
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path


def remote_size(remote_path):
    r = subprocess.run(["rclone", "size", "--json", remote_path], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stdout + r.stderr
    try:
        return json.loads(r.stdout)["bytes"], r.stdout + r.stderr
    except (json.JSONDecodeError, KeyError):
        return None, r.stdout + r.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_name")
    ap.add_argument("date_folder")
    ap.add_argument("baseline_index", type=int)
    ap.add_argument("--outputs-dir", default="/workspace/stable-diffusion-webui-forge/output/txt2img-images")
    ap.add_argument("--transfers", type=int, default=4)
    args = ap.parse_args()

    src_dir = Path(args.outputs_dir) / args.date_folder
    if not src_dir.is_dir():
        print(f"source folder not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    files = sorted(src_dir.glob("*.png"))
    selected = []
    for f in files:
        m = re.match(r"^(\d+)-", f.name)
        if not m:
            continue
        idx = int(m.group(1))
        if idx > args.baseline_index:
            selected.append(f)

    if not selected:
        print("no files past baseline; nothing to do")
        sys.exit(0)

    print(f"selected {len(selected)} images (index > {args.baseline_index}) out of {len(files)} in {src_dir}")

    zip_path = Path("/workspace") / f"{args.project_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for f in selected:
            zf.write(f, arcname=f.name)
    print(f"zipped -> {zip_path} ({zip_path.stat().st_size} bytes)")

    # upload to gdrive:<project>/
    dest_project = f"gdrive:{args.project_name}/"
    r = subprocess.run(
        ["rclone", "copyto", str(zip_path), f"{dest_project}{zip_path.name}",
         "--transfers", str(args.transfers), "-v"],
        capture_output=True, text=True,
    )
    print(r.stdout, r.stderr)
    if r.returncode != 0:
        print("upload to project folder failed", file=sys.stderr)
        sys.exit(1)

    # mirror to 런포드 백업/압축파일/
    r2 = subprocess.run(
        ["rclone", "copy", str(zip_path), "gdrive:런포드 백업/압축파일/",
         "--transfers", str(args.transfers), "-v"],
        capture_output=True, text=True,
    )
    print(r2.stdout, r2.stderr)
    if r2.returncode != 0:
        print("mirror to 런포드 백업/압축파일/ failed", file=sys.stderr)
        sys.exit(1)

    # verify: local zip size must match both remote copies exactly
    local_size = zip_path.stat().st_size

    project_size, project_raw = remote_size(f"{dest_project}{zip_path.name}")
    print("project folder check:", project_raw)

    mirror_size, mirror_raw = remote_size(f"gdrive:런포드 백업/압축파일/{zip_path.name}")
    print("backup mirror check:", mirror_raw)

    if project_size != local_size:
        print(f"VERIFY FAILED: project folder size {project_size} != local zip size {local_size}", file=sys.stderr)
        sys.exit(1)
    if mirror_size != local_size:
        print(f"VERIFY FAILED: backup mirror size {mirror_size} != local zip size {local_size}", file=sys.stderr)
        sys.exit(1)

    print(f"verified: local {local_size} bytes == project folder == backup mirror")
    print(f"done: {args.project_name} ({len(selected)} images)")


if __name__ == "__main__":
    main()
