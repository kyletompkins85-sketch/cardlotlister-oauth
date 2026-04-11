# cardmatch (Bowman Draft — pilot)

Phase-1 **pilot** over eBay listing titles: guess **player** (from the 2025 Bowman Draft checklist allowlist) and **likely base** meaning **paper BD-*** only (non-Chrome). Any **Chrome** in the title (`WF_chrome`), **BDC-#** chrome stock, graded slabs, lots, or inserts/parallels (Axis / Draft Night / Final Draft / In Action / Prized Prospects / Image Variation / Bowman Spotlight(s) / Chrome Prospect Autographs / Etched in Glass / Sapphire / Crystallized, **X-Fractor**, etc.) are not this “base”. See `pilot_is_chrome` on scored CSVs.

This is **not** full “one checklist row” resolution yet.

### Ingestion / scoring from eBay listing titles (programmatic API)

**Intent (for later work):** When you **ingest listings** (Worker, Supabase, or any pipeline) and need to **classify each row from the listing title alone**, use the **`classify_listing`** / **`classify_listings`** API in [`listing_classification.py`](listing_classification.py). It takes the **same string you would show as the eBay listing title** and returns a **`player`** guess plus a canonical **`card_type`** string (e.g. `Chrome · Green /99`), using the **same** `match_pilot` + scored-row logic as batch CSV scoring in [`pipeline.py`](pipeline.py). That keeps online classification aligned with `pilot_scored_full.csv` / `review_slice.csv` labels.

**When to use:** Production or batch jobs that have **titles** and need **player + card type** without writing a full pilot run directory. **When not to use:** If you only need fuzzy player flags without taxonomy, call **`match_pilot`** directly.

**Entry points:** `from cardmatch import classify_listing, classify_listings, ListingClassification` — see [API](#api) below. Tests: [`tests/test_listing_classification.py`](tests/test_listing_classification.py).

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

**Player + primary card type** — intended for **eBay-style listing titles** as you ingest or score listings. Output matches pilot CSV columns (`pilot_player_guess`–derived player and `card_type` from [`card_type.py`](card_type.py)). Default checklist: `data/checklists/normalized/2025_Bowman_Draft_Normalized.csv` (override with `checklist=` or preload via `load_bowman_draft_players` and pass `names` + `last_index`).

```python
from cardmatch import classify_listing, classify_listings

# One title (loads default Bowman Draft checklist once)
out = classify_listing("2025 Bowman Draft #BDC-1 Green Refractor Eli Willits")
# out.player, out.card_type, out.player_status, out.reason_codes, ...

# Many titles — loads checklist once
rows = classify_listings(["title one", "title two"])
```

For large batches, prefer `classify_listings(...)` or call `load_bowman_draft_players()` once and pass `names` / `last_index` so the checklist is not re-read per row.

**Title → player + card type + predicted all-in price (AutoGluon on pairwise ranks):** after training with [`scripts/cardmatch/train_bowman_rank_price_autogluon.py`](../scripts/cardmatch/train_bowman_rank_price_autogluon.py), call [`predict_bowman_price_from_title`](bowman_title_price_predict.py) with paths to `bowman_pairwise_player_rankings_with_listings.csv`, `bowman_pairwise_card_type_rankings_with_listings.csv`, and the `agModels` directory. Input is **only** the listing title; excluded listings (lot, pick, graded, etc.) return `predicted_price=None`. Optional HTTP: [`scripts/cardmatch/bowman_title_price_api.py`](../scripts/cardmatch/bowman_title_price_api.py) (`POST /predict` with `{"title":"..."}`). Requires `autogluon.tabular` and pandas (see `scripts/cardmatch/requirements-bowman-autogluon.txt`). **Railway:** [`docs/RAILWAY.md`](../docs/RAILWAY.md).

**Monte Carlo pairwise price rankings (same logic as Topps `simulate_*` scripts):**

```python
from cardmatch.pairwise_price_rankings import run_pairwise_monte_carlo_rankings

triples = [("PlayerA", "Chrome · Refractor", 25.0), ...]  # (player, card_type, all_in_price)
bundle = run_pairwise_monte_carlo_rankings(triples, iterations=50_000, seed=42)
# bundle.same_player_card_types.stats — card types by win_rate
# bundle.same_card_type_players.stats — players by win_rate
```

From Bowman `pilot_scored_full` dict-rows: `bowman_pilot_rows_to_ranking_triples(rows)` in [`bowman_pilot_triples.py`](bowman_pilot_triples.py) (all-in = `price` + `shipping_cost`; card type from `row_primary_card_type`; **same exclusions as listing counts** — lot, pick/set builder, complete set, presale, graded, etc., via `row_excluded_from_listing_counts`). To write ranked CSVs with **listing_count** and **avg_listing_price** into a pilot folder, run [`scripts/cardmatch/export_bowman_pairwise_ranking_tables.py`](../scripts/cardmatch/export_bowman_pairwise_ranking_tables.py).

**Lower-level pilot match only:**

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
