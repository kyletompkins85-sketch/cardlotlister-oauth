# Cardmatch pilot outputs (committed for review)

These files are produced by scoring **2025 Bowman Draft** `term_search_items` titles against the checklist pilot (player guess + likely base).

- **`20260405_supabase_2025_bowman_draft_sample8000/`** — first automated run in-repo.
  - **`run_summary.md`** — start here.
  - **`review_slice.csv`** — listings whose pilot player matches BD-1…BD-10 checklist names (~1.5k rows in this sample).
  - **`pilot_scored_full.csv`** — all scored rows in this batch (8000-row sample).

**Scope:** SQL filter `term_search_runs.query` matches `%2025%bowman%draft%` and excludes `%2024%`. Sample = **8000 most recent** rows (≈42k total in DB). Re-run later for full table or a different slice.
