#!/usr/bin/env python3
"""무결성 전수 검사 스크립트.

manifest.jsonl 대비 실제 파일의 SHA-256, safetensors 헤더,
HTML 오염 여부를 검사한다. 실패 파일은 quarantine/ 으로 이동.
"""
import hashlib
import json
import os
import shutil
import struct
import sys
from pathlib import Path

BASE = os.environ.get("CIVITAI_DIR", "/workspace/Civitai")
MANIFEST = os.path.join(BASE, "manifest.jsonl")
QUARANTINE = os.path.join(BASE, "quarantine")
REPORT = os.path.join(BASE, "integrity_report.md")

os.makedirs(QUARANTINE, exist_ok=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_safetensors_header(path):
    """safetensors 파일의 헤더 JSON을 파싱할 수 있는지 확인."""
    try:
        with open(path, "rb") as f:
            header_len = struct.unpack("<Q", f.read(8))[0]
            if header_len > 100_000_000:
                return False, "header too large"
            header_bytes = f.read(header_len)
            json.loads(header_bytes)
            return True, None
    except Exception as e:
        return False, str(e)


def check_html_contamination(path):
    """파일 시작이 HTML이 아닌지 확인."""
    with open(path, "rb") as f:
        head = f.read(20).lower()
    if b"<html" in head or b"<!doctype" in head:
        return False, "HTML content detected"
    return True, None


def load_manifest():
    entries = []
    if not os.path.exists(MANIFEST):
        print(f"WARNING: {MANIFEST} not found")
        return entries
    with open(MANIFEST) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def run_checks():
    manifest = load_manifest()
    results = {
        "total": len(manifest),
        "passed": 0,
        "failed": 0,
        "missing": 0,
        "failures": [],
    }

    for entry in manifest:
        filename = entry["filename"]
        expected_type = entry.get("type", "unknown")
        collection = entry.get("collection", "unknown")
        expected_hash = entry.get("sha256", "")

        subdir = "Lora" if expected_type == "Lora" else "Checkpoint"
        path = os.path.join(BASE, subdir, collection, filename)

        if not os.path.exists(path):
            results["missing"] += 1
            results["failures"].append({
                "file": filename, "reason": "MISSING", "collection": collection
            })
            continue

        errors = []

        if expected_hash:
            actual = sha256_file(path)
            if actual != expected_hash:
                errors.append(f"SHA-256 mismatch: expected {expected_hash[:16]}..., got {actual[:16]}...")

        if filename.endswith(".safetensors"):
            ok, err = check_safetensors_header(path)
            if not ok:
                errors.append(f"safetensors header: {err}")

        ok, err = check_html_contamination(path)
        if not ok:
            errors.append(err)

        if errors:
            results["failed"] += 1
            results["failures"].append({
                "file": filename, "reason": "; ".join(errors), "collection": collection
            })
            dest = os.path.join(QUARANTINE, filename)
            shutil.move(path, dest)
            print(f"QUARANTINE: {filename} -> {dest}")
        else:
            results["passed"] += 1

    write_report(results)
    return results


def write_report(results):
    total = results["total"]
    passed = results["passed"]
    failed = results["failed"]
    missing = results["missing"]
    rate = (passed / total * 100) if total > 0 else 0

    with open(REPORT, "w") as f:
        f.write("# Integrity Report\n\n")
        f.write(f"- Total: {total}\n")
        f.write(f"- Passed: {passed} ({rate:.1f}%)\n")
        f.write(f"- Failed: {failed}\n")
        f.write(f"- Missing: {missing}\n\n")
        if results["failures"]:
            f.write("## Failures\n\n")
            f.write("| File | Collection | Reason |\n")
            f.write("|---|---|---|\n")
            for item in results["failures"]:
                f.write(f"| {item['file']} | {item['collection']} | {item['reason']} |\n")

    print(f"\nReport written to {REPORT}")
    print(f"Pass rate: {rate:.1f}% ({passed}/{total})")


if __name__ == "__main__":
    results = run_checks()
    sys.exit(0 if results["failed"] == 0 and results["missing"] == 0 else 1)
