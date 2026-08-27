#!/usr/bin/env python3
"""Deploy a new on-demand RunPod pod via the RunPod GraphQL API.

Usage:
    export RUNPOD_API_KEY="rpa_xxx"
    python3 scripts/runpod_create_pod.py \\
        --name my-pod \\
        --gpu-type "NVIDIA GeForce RTX 4080 SUPER" \\
        --image-name "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04" \\
        --volume-gb 50

The API key is read from the RUNPOD_API_KEY environment variable
(or the --api-key flag) — never hardcode it in source.

Region is left unrestricted ("any") by default: no dataCenterId is sent,
so RunPod picks any datacenter that has the requested GPU available.
Pass --data-center-id to pin a specific region instead.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_ENDPOINT = "https://api.runpod.io/graphql"

DEPLOY_POD_MUTATION = """
mutation DeployPod($input: PodFindAndDeployOnDemandInput!) {
  podFindAndDeployOnDemand(input: $input) {
    id
    name
    desiredStatus
    imageName
    machineId
    machine {
      podHostId
      gpuDisplayName
    }
  }
}
"""


def run_query(api_key: str, query: str, variables: dict | None = None) -> dict:
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    request = urllib.request.Request(
        f"{API_ENDPOINT}?api_key={api_key}",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; runpod-create-pod-script/1.0)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"RunPod API request failed ({exc.code}): {detail}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach RunPod API: {exc.reason}")

    if "errors" in body:
        raise SystemExit(f"RunPod API returned errors: {json.dumps(body['errors'], indent=2)}")
    return body["data"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy an on-demand RunPod pod.")
    parser.add_argument("--name", default="translator-pod", help="Name to give the pod.")
    parser.add_argument(
        "--gpu-type",
        default="NVIDIA GeForce RTX 4080 SUPER",
        help="Exact RunPod gpuTypeId/displayName to request (default: RTX 4080 SUPER).",
    )
    parser.add_argument(
        "--image-name",
        required=True,
        help="Container image to deploy on the pod (e.g. a runpod/pytorch base image).",
    )
    parser.add_argument("--gpu-count", type=int, default=1, help="Number of GPUs to attach.")
    parser.add_argument("--volume-gb", type=int, default=50, help="Persistent volume size in GB.")
    parser.add_argument(
        "--container-disk-gb", type=int, default=20, help="Container (non-persistent) disk size in GB."
    )
    parser.add_argument("--volume-mount-path", default="/workspace", help="Mount path for the volume.")
    parser.add_argument(
        "--data-center-id",
        default=None,
        help="Pin deployment to a specific RunPod datacenter. Omit for 'any' region.",
    )
    parser.add_argument(
        "--cloud-type",
        default="ALL",
        choices=["ALL", "SECURE", "COMMUNITY"],
        help="Cloud type filter (default: ALL, i.e. no restriction).",
    )
    parser.add_argument(
        "--ports",
        default="8888/http,22/tcp",
        help="Comma-separated list of ports to expose, e.g. '8888/http,22/tcp'.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Environment variable to set on the pod. Can be passed multiple times.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("RUNPOD_API_KEY"),
        help="RunPod API key. Defaults to the RUNPOD_API_KEY environment variable.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the request payload without sending it.")
    args = parser.parse_args()

    if not args.api_key and not args.dry_run:
        sys.exit("Error: no API key provided. Set RUNPOD_API_KEY or pass --api-key.")

    env_vars = []
    for item in args.env:
        if "=" not in item:
            sys.exit(f"Invalid --env value '{item}', expected KEY=VALUE.")
        key, value = item.split("=", 1)
        env_vars.append({"key": key, "value": value})

    deploy_input: dict = {
        "name": args.name,
        "imageName": args.image_name,
        "gpuTypeId": args.gpu_type,
        "gpuCount": args.gpu_count,
        "volumeInGb": args.volume_gb,
        "containerDiskInGb": args.container_disk_gb,
        "volumeMountPath": args.volume_mount_path,
        "cloudType": args.cloud_type,
        "ports": args.ports,
        "env": env_vars,
    }
    if args.data_center_id:
        deploy_input["dataCenterId"] = args.data_center_id

    if args.dry_run:
        print(json.dumps({"query": DEPLOY_POD_MUTATION, "variables": {"input": deploy_input}}, indent=2))
        return

    data = run_query(args.api_key, DEPLOY_POD_MUTATION, {"input": deploy_input})
    pod = data.get("podFindAndDeployOnDemand")
    if pod is None:
        sys.exit("RunPod did not return a pod (no matching capacity?).")

    print(f"Pod created: {pod.get('name')} ({pod.get('id')})")
    print(f"  Status:   {pod.get('desiredStatus')}")
    print(f"  Image:    {pod.get('imageName')}")
    machine = pod.get("machine") or {}
    print(f"  GPU:      {machine.get('gpuDisplayName')}")


if __name__ == "__main__":
    main()
