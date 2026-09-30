#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
"${PYTHON:-python3.10}" download_model.py
exec llama-server \
  -m "$PWD/models/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf" \
  --no-mmproj --jinja --reasoning off \
  --host 127.0.0.1 --port "${PORT:-8080}" \
  --path "$PWD/web" \
  --alias gemma4 -c "${CTX_SIZE:-8192}" -np 1 -ngl 99 "$@"
