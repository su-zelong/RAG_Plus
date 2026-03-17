#!/usr/bin/env bash
set -euo pipefail

# document_parser.sh (纯 Shell 实现，严格不嵌入 Python 源码)
# 要求：系统中必须提供 mineru 的 CLI 接口，或可通过 `python3 -m mineru` 提供 CLI 支持
# 功能：扫描源目录（默认 ./data），查找过去 6 小时内新增/修改的文件并解析为 Markdown
# 输出：默认写入 ./output/chunks/parsed_markdown/parsed_document，尽力保存 data-URI 图片与表格块
# 用法：
#   bash test/document_parser.sh [src_dir] [out_dir] [since_hours]

SRC_DIR="${1:-./data}"
OUT_DIR="${2:-./output/chunks/parsed_markdown/parsed_document}"
SINCE_HOURS="${3:-6}"

mkdir -p "$OUT_DIR"

MINUTES=$((SINCE_HOURS * 60))

echo "Scanning '$SRC_DIR' for files modified in the last $SINCE_HOURS hours..."

# Determine mineru CLI command: prefer 'mineru', fallback to 'python3 -m mineru'
CMD=""
if command -v mineru >/dev/null 2>&1; then
  CMD="mineru"
elif command -v python3 >/dev/null 2>&1 && python3 -m mineru -h >/dev/null 2>&1; then
  CMD="python3 -m mineru"
else
  echo "Error: neither 'mineru' nor 'python3 -m mineru' CLI is available in PATH." >&2
  echo "Please install mineru and ensure it exposes a CLI (e.g. pip install mineru)." >&2
  exit 2
fi

found=0

extract_images_and_tables() {
  # $1 = markdown file, $2 = output dir, $3 = base name
  local mdfile="$1" outdir="$2" basename="$3"
  mkdir -p "$outdir/images/$basename"
  mkdir -p "$outdir/tables"

  # 1) data-URI 图片: pattern data:image/<type>;base64,BASE64
  # 使用 grep -oE 捕获 data:image... ) 内容
  grep -oE "!\[[^]]*\]\(data:image/[^)]+\)" "$mdfile" 2>/dev/null | while read -r imgref; do
    uri=$(echo "$imgref" | sed -n "s/.*(\(data:image[^)]*\)).*/\1/p")
    if [[ $uri == data:image/*;base64,* ]]; then
      meta=${uri%%,*}
      b64=${uri#*,}
      ext="png"
      if [[ $meta =~ data:image/([^;]+) ]]; then
        ext=${BASH_REMATCH[1]}
      fi
      idx=$(printf "%03d" $(ls "$outdir/images/$basename" 2>/dev/null | wc -l))
      echo "$b64" | base64 --decode > "$outdir/images/$basename/image_$idx.$ext" 2>/dev/null || true
    fi
  done

  # 2) HTTP/HTTPS 图片，尝试下载
  grep -oE "!\[[^]]*\]\((https?://[^)]+)\)" "$mdfile" 2>/dev/null | while read -r imgref; do
    url=$(echo "$imgref" | sed -n "s/.*(\(https\?://[^)]*\)).*/\1/p")
    idx=$(printf "%03d" $(ls "$outdir/images/$basename" 2>/dev/null | wc -l))
    curl -sSfL "$url" -o "$outdir/images/$basename/image_$idx" || true
  done

  # 3) 简单的 Markdown 表格块检测（启发式）：连续包含 '|' 的行块
  awk '
    /\|/ { if (!in) { in=1; buf=$0 "\n" } else { buf=buf $0 "\n" } next }
    { if (in) { print buf; buf=""; in=0 } }
    END{ if (in) print buf }
  ' "$mdfile" | awk 'NF>0{print > "/tmp/md_table_block" NR".txt"}'

  for f in /tmp/md_table_block*.txt 2>/dev/null; do
    [ -e "$f" ] || continue
    bn=$(basename "$f")
    mv "$f" "$outdir/tables/${basename}_$bn"
  done
}

process_file() {
  local file="$1"
  local outdir="$2"
  local base
  base=$(basename "$file")
  name="${base%.*}"
  out_md="$outdir/$name.md"

  echo "Parsing: $file -> $out_md"

  # 多种常见 CLI 变体尝试（按优先级）
  set +e
  parsed=1
  if $CMD parse_to_markdown "$file" > "$out_md" 2>/dev/null; then
    parsed=0
  elif $CMD parse "$file" --format markdown > "$out_md" 2>/dev/null; then
    parsed=0
  elif $CMD "$file" > "$out_md" 2>/dev/null; then
    parsed=0
  elif $CMD parse "$file" > "$out_md" 2>/dev/null; then
    parsed=0
  else
    parsed=1
  fi
  set -e

  if [ "$parsed" -ne 0 ]; then
    echo "Warning: mineru CLI failed to produce markdown for $file" >&2
    return 1
  fi

  echo "Wrote: $out_md"

  extract_images_and_tables "$out_md" "$outdir" "$name" || true
  return 0
}

while IFS= read -r -d '' file; do
  found=1
  process_file "$file" "$OUT_DIR" || true
done < <(find "$SRC_DIR" -type f -mmin -$MINUTES -print0)

if [ "$found" -eq 0 ]; then
  echo "No new files found in $SRC_DIR (last $SINCE_HOURS hours)."
fi

exit 0
