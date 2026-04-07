#!/usr/bin/env bash
# Full Bowman Draft pilot over every term_search_items row matching Worker search (paginated).
# Requires WORKER_BASE_URL and INTERNAL_API_KEY (export or put in repo-root .env).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
exec python3 -m cardmatch --from-worker-search "$@"
