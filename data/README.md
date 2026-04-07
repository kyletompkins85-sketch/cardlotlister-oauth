# `data/` layout

| Path | Purpose |
|------|---------|
| **`checklists/`** | Normalized checklists, raw Topps text, player mapping / linked tables, presence-wide exports. |
| **`cardmatch_pilot/`** | Committed Cardmatch (Bowman Draft) pilot runs: `pilot_scored_full.csv`, review CSVs, `run_summary.md`. See [`cardmatch_pilot/README.md`](cardmatch_pilot/README.md). |
| **`topps_update_2025/`** | Legacy **2025 Topps Update** market pipeline: `term_search_items` exports, classified tables, simulations, DAD trim, AutoGluon model, underpriced scoring. See [`topps_update_2025/README.md`](topps_update_2025/README.md). |

Add new one-off datasets under a **named subfolder** under `data/` (avoid dropping large CSVs at `data/` root).
