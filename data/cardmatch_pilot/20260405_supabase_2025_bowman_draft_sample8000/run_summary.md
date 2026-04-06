# Pilot run 20260405_supabase_2025_bowman_draft_sample8000

- **Input:** `data/cardmatch_pilot/20260405_supabase_2025_bowman_draft_sample8000/pilot_scored_full.csv`
- **Rows read:** 8000
- **Rows scored (after run filter):** 8000
- **Skipped by run_id filter:** 0
- **Checklist:** `/Users/kyletompkins/Documents/GitHub/cardlotlister-oauth/data/checklists/normalized/2025_Bowman_Draft_Normalized.csv`
- **Run allowlist size:** 0

## Counts

- **pilot_player_status:** {'matched': 5687, 'unknown': 2313}
- **is_likely_base yes:** 493 / 8000
- **review_slice rows (BD-1..BD-10 players):** 1208
- **classification_focus (`review_targets.json`):** `refractor` → **268** rows in `review_focus.csv`
- **review_unclassified (unknown player):** 2313

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
| Lot / multi-card | 1453 |
| Numbered / serial | 1375 |
| Chrome Refractor Plain | 872 |
| Refractor | 545 |
| Complete set | 538 |
| Base-Paper | 493 |
| Pick / set builder | 385 |
| Chrome Base | 362 |
| Chrome Prospect Autographs | 342 |
| BDC / Chrome stock | 219 |
| Presale | 201 |
| axis plain | 173 |
| Prized Prospect | 133 |
| Autograph | 129 |
| Mojo | 112 |
| Draft Night | 97 |
| Chrome Refractor Sky Blue | 84 |
| Chrome x-Fractor | 76 |
| Chrome (non-base) | 69 |
| Bowman In Action | 38 |
| Etched In Glass | 34 |
| Snack-Pack | 32 |
| Chrome Refractor Green | 30 |
| Chrome Refractor Purple | 27 |
| Final Draft | 26 |
| Sapphire | 23 |
| Chrome Refractor Yellow | 20 |
| X-Fractor | 17 |
| axis refractor | 14 |
| Base-Orange | 13 |
| Chrome Refractor Gold | 11 |
| Bowman Spotlight | 10 |
| Speckle | 9 |
| Image Variation | 7 |
| College Variation | 6 |
| Graded | 4 |
| axis gold | 4 |
| axis orange | 4 |
| Chrome Refractor Orange | 3 |
| Crystallized | 3 |
| axis mini-diamond | 3 |
| axis green | 2 |
| Chrome Refractor Black | 1 |
| axis red | 1 |

