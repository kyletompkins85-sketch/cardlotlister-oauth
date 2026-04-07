#!/usr/bin/env bash
# Re-score committed pilot folders from each folder's pilot_scored_full.csv (no network).
# Regenerates pilot_scored_full.csv, review_slice.csv, review_focus.csv,
# review_unclassified.csv, run_summary.md, listing_counts_by_card_type.csv,
# listing_counts_by_player_and_card_type.csv, listing_counts_by_player_bdc_order.csv
# using current cardmatch + review_targets.json.
# Run this after ANY change to: cardmatch code, workflows/.../z10_bowman_listing_classifier.py,
# or cardmatch/review_targets.json (or matcher version bump).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

FULL="data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full"
SAMPLE="data/cardmatch_pilot/20260405_supabase_2025_bowman_draft_sample8000"

for dir in "$FULL" "$SAMPLE"; do
  echo "=== Rescoring $dir ==="
  python3 -m cardmatch \
    --input "$dir/pilot_scored_full.csv" \
    --no-run-filter \
    --output-dir "$dir"
done

echo ""
echo "Done. Open each run_summary.md; confirm review_focus.csv row counts match the summary."
