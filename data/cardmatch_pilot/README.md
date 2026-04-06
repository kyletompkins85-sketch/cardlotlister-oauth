# Cardmatch pilot outputs (committed for review)

These files are produced by scoring **2025 Bowman Draft** `term_search_items` titles against the checklist pilot (player guess + likely base).

- **`20260405_mcp_supabase_2025_bowman_draft_full/`** — **full** Bowman Draft pilot run (~41k `term_search_items` from Supabase REST: title `ILIKE '%2025%bowman%draft%'`, titles containing `2024` dropped). See `run_summary.md`.
- **`20260405_supabase_2025_bowman_draft_sample8000/`** — earlier 8000-row sample in-repo.
  - **`run_summary.md`** — start here.
  - **`review_slice.csv`** — compact review: **`player`**, **`price`** (rounded to nearest dollar), **`card_type`**, **`title`** (abridged). Only rows whose pilot player matches the checklist names in `cardmatch/review_targets.json` (see that file for the current card-number band). **Sorted by checklist card number (BD-1, BD-2, …), then price ascending** (missing price last), unless `review_slice_sort` overrides.
  - **`review_focus.csv`** — same columns as `review_slice.csv`, filtered by **`classification_focus`** in `cardmatch/review_targets.json` (e.g. **`axis`** = Axis insert). **`review_focus_scope`**: `all` = every scored listing; `slice` = only players in `card_numbers`. Filename is always `review_focus.csv`; edit JSON to change the review pass.
  - **`review_unclassified.csv`** — rows where the pilot could not match a checklist player (**`pilot_player_status` = unknown**). Sorted by price, then title.
  - **`pilot_scored_full.csv`** — all scored rows in this batch (8000-row sample).

**Scope (8000-row folder only):** SQL filter `term_search_runs.query` matches `%2025%bowman%draft%` and excludes `%2024%`. That export was **8000 most recent** rows (≈42k total in DB at the time).

**Full Supabase-backed run:** From the repo root, with `WORKER_BASE_URL` and `INTERNAL_API_KEY` set (or in a gitignored `.env`), run:

`scripts/run_cardmatch_full_bowman_search.sh`

or `python3 -m cardmatch --from-worker-search` (see [`cardmatch/README.md`](../../cardmatch/README.md)). That paginates `GET /internal/termSearchItems/search` for the default query `2025 bowman draft`, drops titles containing `2024` unless you pass `--no-title-exclude`, and writes a new folder under `data/cardmatch_pilot/<UTC>_supabase_2025_bowman_draft_full/`.
