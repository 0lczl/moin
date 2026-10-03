#!/bin/bash
# Runs Biome (lint + format) on the file Claude just edited.
set -euo pipefail

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

if [ -z "$file_path" ] || [ ! -f "$file_path" ]; then
  exit 0
fi

case "$file_path" in
  *.js|*.jsx|*.ts|*.tsx|*.mjs|*.cjs|*.json|*.jsonc|*.css)
    ;;
  *)
    exit 0
    ;;
esac

# Find the nearest ancestor directory containing a biome.json config.
dir=$(dirname "$file_path")
project_dir=""
while [ "$dir" != "/" ]; do
  if [ -f "$dir/biome.json" ]; then
    project_dir="$dir"
    break
  fi
  dir=$(dirname "$dir")
done

if [ -z "$project_dir" ]; then
  exit 0
fi

(cd "$project_dir" && bunx biome check --write --no-errors-on-unmatched "$file_path") || true

exit 0
