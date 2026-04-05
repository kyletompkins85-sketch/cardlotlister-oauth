# Pilot run 20260405_supabase_2025_bowman_draft_sample8000

- **Input:** Supabase MCP pull: 2025 Bowman Draft only (8000 most recent rows, ~41k total in DB)
- **Rows read:** 8000
- **Rows scored (after run filter):** 8000
- **Skipped by run_id filter:** 0
- **Checklist:** `data/checklists/normalized/2025_Bowman_Draft_Normalized.csv`
- **Run allowlist size:** 0

## Counts

- **pilot_player_status:** {'matched': 5723, 'unknown': 2277}
- **is_likely_base yes:** 1387 / 8000
- **review_slice rows (BD-1..10 players):** 1494

## Outputs

- `pilot_scored_full.csv` — full scored CSV
- `review_slice.csv` — BD-1..10 player slice, newest-first

