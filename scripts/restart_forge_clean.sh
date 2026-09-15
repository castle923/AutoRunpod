#!/usr/bin/env bash
cd /workspace/stable-diffusion-webui-forge
VENV_PATH=$(cat /workspace/stable-diffusion-webui-forge/venv_path)
exec env -i \
  PATH="${VENV_PATH}/bin:/usr/local/nvidia/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
  HOME=/root \
  PYTHONUNBUFFERED=1 \
  HF_HOME=/workspace \
  MPLBACKEND=agg \
  VENV_PATH="${VENV_PATH}" \
  LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64 \
  LIBRARY_PATH=/usr/local/cuda/lib64/stubs \
  COMMANDLINE_ARGS="--port 3001 --listen --api --xformers --enable-insecure-extension-access --no-half-vae" \
  "${VENV_PATH}/bin/python3" launch.py -f
