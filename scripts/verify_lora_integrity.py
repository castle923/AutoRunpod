#!/usr/bin/env python3
"""
LoRA/체크포인트 safetensors 파일 무결성 검증 스크립트.
헤더(JSON 메타데이터)를 파싱해서 파일 크기가 헤더가 가리키는 텐서 데이터 범위를
전부 포함하는지 확인한다. 다운로드 도중 잘리거나 손상된 파일을 찾아낸다.

사용법:
    python3 verify_lora_integrity.py /workspace/stable-diffusion-webui-forge/models/Lora
"""
import os
import sys
import json
import struct


def verify_dir(root_dir):
    files = []
    for root, dirs, fs in os.walk(root_dir):
        for f in fs:
            if f.endswith(".safetensors"):
                files.append(os.path.join(root, f))

    print("total files to check:", len(files))

    bad = []
    for path in files:
        f = os.path.relpath(path, root_dir)
        try:
            size = os.path.getsize(path)
            if size < 16:
                bad.append((f, size, "too small"))
                continue
            with open(path, "rb") as fh:
                header_len = struct.unpack("<Q", fh.read(8))[0]
                if header_len <= 0 or header_len > size:
                    bad.append((f, size, f"invalid header_len={header_len}"))
                    continue
                header_json = fh.read(header_len)
                try:
                    header = json.loads(header_json)
                except Exception as e:
                    bad.append((f, size, f"header JSON parse failed: {e}"))
                    continue
                max_end = 0
                for k, v in header.items():
                    if k == "__metadata__":
                        continue
                    if isinstance(v, dict) and "data_offsets" in v:
                        max_end = max(max_end, v["data_offsets"][1])
                expected_min_size = 8 + header_len + max_end
                if size < expected_min_size:
                    bad.append((f, size, f"truncated: expected>={expected_min_size}, got={size}"))
        except Exception as e:
            bad.append((f, -1, f"error: {e}"))

    print("corrupted/suspicious files:", len(bad))
    for f, s, reason in bad:
        print(f"{f} ({s} bytes): {reason}")

    return bad


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    bad = verify_dir(target)
    sys.exit(1 if bad else 0)
