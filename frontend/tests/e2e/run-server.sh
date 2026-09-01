#!/usr/bin/env bash
# Build the client first: FastAPI, rather than Vite, serves this output.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
python_bin="${PYTHON_BIN:-/home/saber/projects/flashcard/.venv/bin/python}"
if ! command -v "$python_bin" >/dev/null 2>&1; then
  python_bin=python3
fi
(cd "$repo/frontend" && npm run build)
exec "$python_bin" "$here/serve.py" "$@"
