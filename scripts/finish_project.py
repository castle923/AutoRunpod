#!/usr/bin/env python3
"""
프로젝트 완료 표준 처리 스크립트.
지정된 인덱스 범위의 이미지를 zip으로 압축하고, gdrive:<project>/ 에 업로드,
런포드 백업/압축파일/ 에도 미러링한 뒤 결과를 검증한다.

사용법:
    python3 finish_project.py <project_name> <date_folder> --start-idx 806 --end-idx 1609
    python3 finish_project.py <project_name> <date_folder> --start-idx 806
    python3 finish_project.py detect <date_folder>   # 배치 경계 자동 감지

예시:
    python3 finish_project.py 고차비_R_19 2026-09-15 --start-idx 806 --end-idx 1609
    python3 finish_project.py detect 2026-09-15
"""
import argparse
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path


OUTPUTS_DIR_DEFAULT = "/workspace/stable-diffusion-webui-forge/output/txt2img-images"


def remote_size(remote_path):
    r = subprocess.run(["rclone", "size", "--json", remote_path], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stdout + r.stderr
    try:
        return json.loads(r.stdout)["bytes"], r.stdout + r.stderr
    except (json.JSONDecodeError, KeyError):
        return None, r.stdout + r.stderr


def detect_batches(src_dir):
    """Detect batch boundaries by seed continuity and timestamp gaps.

    Returns a list of (start_idx, end_idx, image_count, time_start, time_end)
    tuples, one per detected batch.
    """
    from datetime import datetime

    files = sorted(src_dir.glob("*.png"))
    if not files:
        return []

    entries = []
    for f in files:
        m = re.match(r"^(\d+)-(\d+)\.png$", f.name)
        if not m:
            continue
        idx = int(m.group(1))
        seed = int(m.group(2))
        mtime = f.stat().st_mtime
        entries.append((idx, seed, mtime, f))

    if not entries:
        return []

    batches = []
    batch_start = 0

    for i in range(1, len(entries)):
        prev_idx, prev_seed, prev_mtime, _ = entries[i - 1]
        curr_idx, curr_seed, curr_mtime, _ = entries[i]

        time_gap = curr_mtime - prev_mtime
        seed_jump = abs(curr_seed - prev_seed) > 100

        if time_gap > 1200 and seed_jump:
            batches.append((
                entries[batch_start][0],
                entries[i - 1][0],
                i - batch_start,
                datetime.fromtimestamp(entries[batch_start][2]).strftime("%H:%M:%S"),
                datetime.fromtimestamp(entries[i - 1][2]).strftime("%H:%M:%S"),
            ))
            batch_start = i

    batches.append((
        entries[batch_start][0],
        entries[-1][0],
        len(entries) - batch_start,
        datetime.fromtimestamp(entries[batch_start][2]).strftime("%H:%M:%S"),
        datetime.fromtimestamp(entries[-1][2]).strftime("%H:%M:%S"),
    ))

    return batches


def cmd_detect(args):
    src_dir = Path(args.outputs_dir) / args.date_folder
    if not src_dir.is_dir():
        print(f"source folder not found: {src_dir}", file=sys.stderr)
        sys.exit(1)

    batches = detect_batches(src_dir)
    if not batches:
        print("no images found")
        sys.exit(0)

    print(f"Detected {len(batches)} batch(es) in {src_dir}:\n")
    for i, (start, end, count, t_start, t_end) in enumerate(batches):
        print(f"  Batch {i + 1}: idx {start:05d}~{end:05d}  ({count} images)  {t_start}~{t_end}")

    print(f"\nUsage example for each batch:")
    for i, (start, end, count, _, _) in enumerate(batches):
        print(f"  python3 finish_project.py <project_name> {args.date_folder} --start-idx {start} --end-idx {end}")


def cmd_finish(args):
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
        if idx < args.start_idx:
            continue
        if args.end_idx is not None and idx > args.end_idx:
            continue
        selected.append(f)

    if not selected:
        print("no files in specified range; nothing to do")
        sys.exit(0)

    first_idx = int(re.match(r"^(\d+)-", selected[0].name).group(1))
    last_idx = int(re.match(r"^(\d+)-", selected[-1].name).group(1))
    print(f"selected {len(selected)} images (idx {first_idx:05d}~{last_idx:05d}) out of {len(files)} in {src_dir}")

    zip_path = Path("/workspace") / f"{args.project_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for f in selected:
            zf.write(f, arcname=f.name)
    print(f"zipped -> {zip_path} ({zip_path.stat().st_size} bytes)")

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

    r2 = subprocess.run(
        ["rclone", "copy", str(zip_path), "gdrive:런포드 백업/압축파일/",
         "--transfers", str(args.transfers), "-v"],
        capture_output=True, text=True,
    )
    print(r2.stdout, r2.stderr)
    if r2.returncode != 0:
        print("mirror to 런포드 백업/압축파일/ failed", file=sys.stderr)
        sys.exit(1)

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
    print(f"done: {args.project_name} ({len(selected)} images, idx {first_idx:05d}~{last_idx:05d})")


def main():
    ap = argparse.ArgumentParser(description="프로젝트 완료 후처리 (zip + gdrive upload + verify)")
    ap.add_argument("project_name", help="프로젝트명 (예: 고차비_R_19) 또는 'detect' (배치 경계 감지)")
    ap.add_argument("date_folder", help="날짜 폴더명 (예: 2026-09-15)")
    ap.add_argument("--start-idx", type=int, default=0, help="시작 인덱스 (포함)")
    ap.add_argument("--end-idx", type=int, default=None, help="끝 인덱스 (포함, 미지정 시 끝까지)")
    ap.add_argument("--outputs-dir", default=OUTPUTS_DIR_DEFAULT)
    ap.add_argument("--transfers", type=int, default=4)

    # backward compat: positional baseline_index
    ap.add_argument("baseline_index", nargs="?", type=int, default=None,
                    help=argparse.SUPPRESS)

    args = ap.parse_args()

    if args.project_name == "detect":
        cmd_detect(args)
        return

    # backward compat: if baseline_index given positionally, use it as start-idx
    if args.baseline_index is not None and args.start_idx == 0:
        args.start_idx = args.baseline_index + 1

    cmd_finish(args)


if __name__ == "__main__":
    main()
