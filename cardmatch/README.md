# cardmatch (Bowman Draft — pilot)

Phase-1 **pilot** over eBay listing titles: guess **player** (from the 2025 Bowman Draft checklist allowlist) and **likely base** meaning **paper BD-*** only (non-Chrome). Any **Chrome** in the title (`WF_chrome`), **BDC-#** chrome stock, graded slabs, lots, or inserts/parallels (Axis / Draft Night / Final Draft / In Action / Prized Prospects / Image Variation / Bowman Spotlight(s) / Chrome Prospect Autographs / Etched in Glass / Sapphire / Crystallized, **X-Fractor**, etc.) are not this “base”. See `pilot_is_chrome` on scored CSVs.

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

### Full Supabase slice (all matching titles, not just one `run_id`)

To pull **every** `term_search_items` row whose title matches a search string (paginates through `GET /internal/termSearchItems/search`), then score the pilot on that full set:

```bash
export WORKER_BASE_URL="https://your-worker.workers.dev"
export INTERNAL_API_KEY="your-key"

python3 -m cardmatch --from-worker-search
```

If Worker env vars are **not** set, the same command uses **Supabase REST** instead (`SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`), matching titles with `ILIKE` (same idea as the Worker search endpoint).

Defaults: search query **`2025 bowman draft`** (override with `--search-q` or `CARDMATCH_SEARCH_Q`), drop titles containing **`2024`** (disable with `--no-title-exclude`), and write under **`data/cardmatch_pilot/<UTC>_supabase_2025_bowman_draft_full/`** unless you pass `--output-dir`.

**Then open** the printed path — start with **`run_summary.md`**, then **`review_slice.csv`** (`player`, dollar-rounded `price`, **`card_type`** (primary taxonomy, e.g. Axis subtypes as **Axis Plain** / **Axis Refractor** / …), abridged `title`; sort per `review_targets.json`). Also written: **`review_focus.csv`** (rows matching **`classification_focus`**, pool from **`review_focus_scope`**; Axis focus sorts by **#A-…** then price), and **`review_unclassified.csv`** (unknown player). They are written under `cardmatch/runs/<timestamp>/` (gitignored by default — copy into `data/cardmatch_pilot/` if you want the CSVs committed).

**Committed review folder (example):** see [`data/cardmatch_pilot/`](../data/cardmatch_pilot/) for a Supabase-backed sample run with `run_summary.md`, `review_slice.csv`, `review_focus.csv`, `review_unclassified.csv`, and `pilot_scored_full.csv`.

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
