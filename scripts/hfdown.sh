#!/bin/bash
# 원본 데이터 소스: Hugging Face 저장소에서 체크포인트/LoRA/업스케일러를 다운로드하는 스크립트.
#
# 보안 참고: 실제 사용하던 버전에는 Hugging Face access token이 하드코딩되어 있었으나,
# 이 GitHub 저장소에는 토큰을 노출하지 않기 위해 <YOUR_HF_TOKEN> 플레이스홀더로 대체함.
# 실제 토큰이 필요하면 구글드라이브 `런포드 자동화/hfdown.sh`(비공개 백업)를 참조할 것.

set -e

# === Step 0: Always install required tools ===
apt-get update
apt-get install -y wget unzip grep file

# === Step 0.5: Ensure Hugging Face CLI is installed ===
if ! command -v huggingface-cli &> /dev/null; then
  echo "Installing huggingface_hub..."
  pip install --upgrade huggingface_hub
fi

# === Step 1: Set credentials and repo info ===
TOKEN="<YOUR_HF_TOKEN>"
REPO="Agnus6728/wai"

# === Step 2: Define files to download, in priority order ===
# Priority: checkpoint > part3 (user-flagged most important) > LoRA > everything else (upscale, etc.)
FILES=(
  "waiNSFWIllustrious_v140.safetensors"
  "part3.zip"
  "styleil.zip"
  "lilpa.zip"
  "part1.zip"
  "part2.zip"
  "part4.zip"
  "part5.zip"
  "part6.zip"
  "part7.zip"
)

# === Step 3: Create required directories ===
mkdir -p downloads extracted_files ../Stable-diffusion ../ESRGAN ../Lora

# === Step 4: Function to download + process ===
process_file() {
  local FILE="$1"
  local URL="https://huggingface.co/$REPO/resolve/main/$FILE"
  local TARGET="downloads/$FILE"

  echo "Downloading $FILE..."
  wget --header="Authorization: Bearer $TOKEN" "$URL" -O "$TARGET"

  # Post-process immediately
  if file "$TARGET" | grep -q "Zip archive data"; then
    echo "Unzipping $FILE..."
    unzip -o "$TARGET" -d extracted_files/
    echo "Deleting $FILE..."
    rm -f "$TARGET"
  elif [[ "$FILE" == *.safetensors ]]; then
    echo "Moving $FILE to ../Stable-diffusion/"
    mv "$TARGET" ../Stable-diffusion/
  elif [[ "$FILE" == *.pth ]]; then
    echo "Moving $FILE to ../ESRGAN/"
    mv "$TARGET" ../ESRGAN/
  fi
}

export -f process_file
export TOKEN REPO

# === Step 5: Launch jobs with concurrency limit (4 max), in priority order ===
# Files are launched in the FILES array order above, so higher-priority items
# (checkpoint, then part3, then LoRA) start downloading before lower-priority ones.
MAX_JOBS=4
echo "Starting parallel downloads (up to $MAX_JOBS at a time)..."

for FILE in "${FILES[@]}"; do
  bash -c "process_file \"$FILE\"" &

  # If we already have $MAX_JOBS running, wait for one to finish
  while (( $(jobs -r | wc -l) >= MAX_JOBS )); do
    sleep 1
  done
done

wait
echo "All downloads and processing completed."

# === Step 6: Sort extracted files into the right model folders ===
echo "Scanning extracted_files/ for .pth (upscalers) and .safetensors (LoRA) files..."
find extracted_files/ -type f -name "*.pth" -exec mv {} ../ESRGAN/ \;
find extracted_files/ -type f -name "*.safetensors" -exec mv {} ../Lora/ \;

echo "Everything done."
