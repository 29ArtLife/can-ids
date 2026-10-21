#!/usr/bin/env bash
# 下载 Car-Hacking Dataset（HCRL）到 data/raw/
# 用法：bash scripts/download_data.sh
set -euo pipefail

DEST="$(cd "$(dirname "$0")/.." && pwd)/data/raw"
mkdir -p "$DEST"

URL="https://www.dropbox.com/scl/fo/9rwsf9pclhvv9xxloojom/AF7JeRW893grZkigkulkAHk?rlkey=3h6zamu3kc262lrnipu5qden8&st=3g52q9hd&dl=1"
OUT="$DEST/car-hacking-full.zip"

if [ -f "$OUT" ] && [ "$(stat -c%s "$OUT" 2>/dev/null || stat -f%z "$OUT")" -gt 900000000 ]; then
  echo "已存在完整文件：$OUT"
else
  echo "下载中（约 953 MB，视网络 5-15 分钟）..."
  curl -L --progress-bar -o "$OUT" "$URL"
fi

echo "解压到 $DEST ..."
unzip -o -q "$OUT" -d "$DEST"

echo "完成。文件列表："
find "$DEST" -maxdepth 2 -type f ! -name "*.zip" -printf "%10s  %p\n" 2>/dev/null \
  || ls -lh "$DEST"
