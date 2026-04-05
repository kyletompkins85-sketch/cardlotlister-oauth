# cardmatch (Bowman Draft — pilot)

Phase-1 **pilot** over eBay listing titles: guess **player** (from the 2025 Bowman Draft checklist allowlist) and **likely base** vs insert/parallel/auto/serial cues, using the existing `z10_bowman_listing_classifier` regex family.

This is **not** full “one checklist row” resolution yet.

## What you actually run (no CSV export needed)

From the repo root, set the same secrets your other scripts use (`WORKER_BASE_URL`, `INTERNAL_API_KEY`), plus the **Supabase `term_search` run_id** for **2025 Bowman Draft** (one or more UUIDs — *not* Topps Update):

```bash
cd /path/to/cardlotlister-oauth

export WORKER_BASE_URL="https://your-worker.workers.dev"
export INTERNAL_API_KEY="your-key"

python3 -m cardmatch --from-worker --term-search-run-id "PASTE-BOWMAN-DRAFT-RUN-UUID-HERE"
```

Or multiple runs:

```bash
python3 -m cardmatch --from-worker \
  --term-search-run-id "uuid-1" \
  --term-search-run-id "uuid-2"
```

You can also set `TERM_SEARCH_RUN_IDS=uuid1,uuid2` instead of flags.

**Then open** the printed path — start with **`run_summary.md`**, then **`review_slice.csv`**. They are written under `cardmatch/runs/<timestamp>/` (gitignored by default — copy into `data/cardmatch_pilot/` if you want the CSVs committed).

**Committed review folder (example):** see [`data/cardmatch_pilot/`](../data/cardmatch_pilot/) for a Supabase-backed sample run with `run_summary.md`, `review_slice.csv`, and `pilot_scored_full.csv`.

## Optional: batch on a CSV

If you already have `term_search_items_export.csv`:

```bash
python3 -m cardmatch --input path/to/term_search_items_export.csv \
  --run-ids "uuid-for-bowman-draft-run"
```

- `--no-run-filter` — only if the CSV is already Bowman-only or has no `run_id` column.
- `--baseline` previous `pilot_scored_full.csv` — writes `changes_since_previous.csv`.

## API

```python
from cardmatch import match_pilot
from cardmatch.player_index import load_bowman_draft_players

names, last_index = load_bowman_draft_players()
r = match_pilot("your title", names, last_index)
# r.player_guess, r.is_likely_base, r.reason_codes, ...
```

## Tests

```bash
python3 -m unittest discover -s cardmatch/tests -v
```
