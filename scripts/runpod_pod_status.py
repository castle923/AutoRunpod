#!/usr/bin/env python3
"""Check RunPod pod status via the RunPod GraphQL API.

Usage:
    export RUNPOD_API_KEY="rpa_xxx"
    python3 scripts/runpod_pod_status.py            # list all pods
    python3 scripts/runpod_pod_status.py <pod_id>    # show one pod

The API key is read from the RUNPOD_API_KEY environment variable
(or the --api-key flag) — never hardcode it in source.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_ENDPOINT = "https://api.runpod.io/graphql"

LIST_PODS_QUERY = """
query Pods {
  myself {
    pods {
      id
      name
      desiredStatus
      lastStatusChange
      machine {
        gpuDisplayName
        podHostId
      }
      runtime {
        uptimeInSeconds
        gpus {
          id
          gpuUtilPercent
          memoryUtilPercent
        }
      }
    }
  }
}
"""

POD_QUERY = """
query Pod($podId: String!) {
  pod(input: { podId: $podId }) {
    id
    name
    desiredStatus
    lastStatusChange
    machine {
      gpuDisplayName
      podHostId
    }
    runtime {
      uptimeInSeconds
      gpus {
        id
        gpuUtilPercent
        memoryUtilPercent
      }
    }
  }
}
"""


def run_query(api_key: str, query: str, variables: dict | None = None) -> dict:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    request = urllib.request.Request(
        f"{API_ENDPOINT}?api_key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"RunPod API request failed ({exc.code}): {detail}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach RunPod API: {exc.reason}")

    if "errors" in body:
        raise SystemExit(f"RunPod API returned errors: {json.dumps(body['errors'], indent=2)}")
    return body["data"]


def format_pod(pod: dict) -> str:
    runtime = pod.get("runtime") or {}
    uptime = runtime.get("uptimeInSeconds")
    gpus = runtime.get("gpus") or []
    machine = pod.get("machine") or {}

    lines = [
        f"Pod: {pod.get('name')} ({pod.get('id')})",
        f"  Status:        {pod.get('desiredStatus')}",
        f"  Last change:   {pod.get('lastStatusChange')}",
        f"  GPU type:      {machine.get('gpuDisplayName')}",
        f"  Uptime (sec):  {uptime if uptime is not None else 'n/a (not running)'}",
    ]
    for gpu in gpus:
        lines.append(
            f"  GPU {gpu.get('id')}: util={gpu.get('gpuUtilPercent')}% "
            f"mem={gpu.get('memoryUtilPercent')}%"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check RunPod pod status.")
    parser.add_argument("pod_id", nargs="?", help="Specific pod ID to check. Omit to list all pods.")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("RUNPOD_API_KEY"),
        help="RunPod API key. Defaults to the RUNPOD_API_KEY environment variable.",
    )
    parser.add_argument("--json", action="store_true", help="Print raw JSON instead of a summary.")
    args = parser.parse_args()

    if not args.api_key:
        sys.exit("Error: no API key provided. Set RUNPOD_API_KEY or pass --api-key.")

    if args.pod_id:
        data = run_query(args.api_key, POD_QUERY, {"podId": args.pod_id})
        pod = data.get("pod")
        if pod is None:
            sys.exit(f"No pod found with id '{args.pod_id}'.")
        pods = [pod]
    else:
        data = run_query(args.api_key, LIST_PODS_QUERY)
        pods = (data.get("myself") or {}).get("pods") or []

    if args.json:
        print(json.dumps(pods, indent=2))
        return

    if not pods:
        print("No pods found.")
        return

    print("\n\n".join(format_pod(pod) for pod in pods))


if __name__ == "__main__":
    main()
