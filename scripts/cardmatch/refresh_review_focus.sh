#!/usr/bin/env bash
# Fast: regenerate only review_focus.csv from existing pilot_scored_full.csv (no player matching).
# Uses cardmatch/review_targets.json for BD slice, focus mode, sort.
# Example:
#   bash scripts/cardmatch/refresh_review_focus.sh \
#     data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
DIR="${1:?usage: refresh_review_focus.sh <pilot_dir_with_pilot_scored_full.csv>}"
python3 -m cardmatch \
  --input "$DIR/pilot_scored_full.csv" \
  --review-focus-only \
  --output-dir "$DIR"
