# Pilot run 20260405_mcp_supabase_2025_bowman_draft_full

- **Input:** `data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/pilot_scored_full.csv`
- **Rows read:** 41357
- **Rows scored (after run filter):** 41357
- **Skipped by run_id filter:** 0
- **Checklist:** `/Users/kyletompkins/Documents/GitHub/cardlotlister-oauth/data/checklists/normalized/2025_Bowman_Draft_Normalized.csv`
- **Run allowlist size:** 0

## Counts

- **pilot_player_status:** {'matched': 28013, 'unknown': 13344}
- **is_likely_base yes:** 4104 / 41357
- **review_slice rows (BD-1..BD-10 players):** 3464
- **classification_focus (`review_targets.json`):** `refractor` → **731** rows in `review_focus.csv`
- **review_unclassified (unknown player):** 13344

## Outputs

- `pilot_scored_full.csv` — full scored CSV
- `review_slice.csv` — BD-1..BD-10 player slice (BD# ascending, then price ascending (missing price last)); **excludes** lot listings (`WF_lot`)
- `review_focus.csv` — rows matching **classification_focus** (`refractor` = primary type **Refractor**, **axis refractor**, or **Chrome** parallel refractor family (`Chrome x-Fractor`, `Chrome Refractor …`); not **Chrome Base**); pool from `review_focus_scope` / defaults (see `review_targets.json`); **sort:** BD# ascending (checklist order), then price ascending (missing price last); **excludes** lot listings (`WF_lot`)
- `review_unclassified.csv` — rows with **unknown** player (could not match checklist)
- `listing_counts_by_card_type.csv` — **sum of listings by card type** (mutually exclusive primary type)
- `listing_counts_by_player_and_card_type.csv` — **listings by player and card type** (matrix)

## Listings by card type

Mutually exclusive **primary** type per listing (`cardmatch/card_type.py`). Bowman Chrome BDC parallels use refined labels when possible (e.g. Chrome Refractor Sky Blue, Chrome x-Fractor); otherwise non-base rows use the most specific `nb_*` classifier hit (last reason code).

| card_type | listings |
|-----------|----------|
| Numbered / serial | 7168 |
| Complete set | 4632 |
| Chrome Refractor Plain | 4540 |
| Base-Paper | 4104 |
| Pick / set builder | 2822 |
| Presale | 2536 |
| Chrome Base | 2238 |
| Lot / multi-card | 2233 |
| Chrome Prospect Autographs | 1822 |
| Refractor | 1743 |
| axis plain | 1051 |
| Prized Prospect | 1002 |
| BDC / Chrome stock | 841 |
| Autograph | 782 |
| Draft Night | 534 |
| Chrome (non-base) | 528 |
| Bowman In Action | 405 |
| Chrome x-Fractor | 390 |
| Chrome Refractor Sky Blue | 360 |
| Chrome Refractor Green | 212 |
| Chrome Refractor Purple | 172 |
| Snack-Pack | 167 |
| Chrome Refractor Yellow | 109 |
| Etched In Glass | 109 |
| X-Fractor | 109 |
| Mojo | 107 |
| Final Draft | 87 |
| Bowman Spotlight | 70 |
| Base-Orange | 52 |
| Image Variation | 45 |
| axis refractor | 45 |
| Chrome Refractor Red | 40 |
| Chrome Refractor Gold | 39 |
| Crystallized | 31 |
| Sapphire | 31 |
| Speckle | 29 |
| Chrome Refractor Orange | 28 |
| Graded | 24 |
| axis gold | 24 |
| College Variation | 19 |
| Chrome Refractor Black | 18 |
| axis mini-diamond | 18 |
| axis green | 17 |
| axis orange | 10 |
| Sky Blue | 4 |
| Printing Plate | 3 |
| Wave | 3 |
| axis superfractor | 2 |
| Sparkle | 1 |
| axis red | 1 |

