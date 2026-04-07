# Pilot run 20260405_supabase_2025_bowman_draft_sample8000

- **Input:** `data/cardmatch_pilot/20260405_supabase_2025_bowman_draft_sample8000/pilot_scored_full.csv`
- **Rows read:** 8000
- **Rows scored (after run filter):** 8000
- **Skipped by run_id filter:** 0
- **Checklist:** `/Users/kyletompkins/Documents/GitHub/cardlotlister-oauth/data/checklists/normalized/2025_Bowman_Draft_Normalized.csv`
- **Run allowlist size:** 0

## Counts

- **pilot_player_status:** {'matched': 5769, 'unknown': 2231}
- **is_likely_base yes:** 424 / 8000
- **review_slice rows (BD-1..BD-10 players):** 1176
- **classification_focus (`review_targets.json`):** `unknown_player` → **4** rows in `review_focus.csv`
- **review_unclassified (unknown player):** 2231

## Outputs

- `pilot_scored_full.csv` — full scored CSV
- `review_slice.csv` — BD-1..BD-10 player slice (BD# ascending, then price ascending (missing price last)); **excludes** lot listings (`WF_lot`) and graded slabs (`WF_graded` / `pilot_is_graded`)
- `review_focus.csv` — rows matching **classification_focus** (`unknown_player` = `pilot_player_status` is **unknown** (or guess is literal **(unknown player)**); non-card junk excluded via same rules as listing counts (lot/pick/set/complete/presale/graded)); pool from `review_focus_scope` / defaults (see `review_targets.json`); **sort:** price ascending (missing price last), then title A–Z (same order as review_unclassified); **excludes** same non-card listings as listing counts: lot / pick / set builder / complete set / presale (`WF_lot`, `WF_pick`, `WF_set_builder`, `WF_complete_set`, `WF_presale`) plus graded slabs
- `review_unclassified.csv` — rows with **unknown** player (could not match checklist)
- `listing_counts_by_card_type.csv` — **sum of listings by card type** (mutually exclusive primary type)
- `listing_counts_by_player_and_card_type.csv` — **listings by player and card type** (matrix)
- `listing_counts_by_player_bdc_order.csv` — **listings per player**, sorted by **BDC#** (1–200 checklist order); unmapped players last

## Listings by card type

Mutually exclusive **primary** type per listing (`cardmatch/card_type.py`). Bowman Chrome BDC parallels use refined labels when possible (e.g. Chrome Refractor Sky Blue, Chrome x-Fractor); otherwise non-base rows use the most specific `nb_*` classifier hit (last reason code).

| card_type | listings |
|-----------|----------|
| BDC Chrome Prospect · Refractor | 819 |
| BDC Chrome Prospect · Auto | 427 |
| Base-Paper | 426 |
| BDC Chrome Prospect · Base | 424 |
| BDC Chrome Prospect · Sky Blue /499 | 206 |
| Prized Prospects | 156 |
| Bowman Axis · Base | 130 |
| BDC Chrome Prospect · Blue /150 | 123 |
| BDC Chrome Prospect · Green /99 | 113 |
| BDC Chrome Prospect · X-Fractor | 96 |
| BDC Chrome Prospect · Sky Blue /499 · Auto | 94 |
| BDC Chrome Prospect · Blue /150 · Auto | 81 |
| BDC Chrome Prospect · Purple /250 · Auto | 77 |
| BDC Chrome Prospect · Aqua /125 | 74 |
| BDC Chrome Prospect · Green /99 · Auto | 69 |
| BDC Chrome Prospect · Purple /250 | 68 |
| BDC Chrome Prospect · Yellow /75 | 64 |
| Bowman Draft Night | 63 |
| Bowman In Action | 59 |
| BDC Chrome Prospect · Fuchsia Reptilian /199 | 57 |
| BDC Chrome Prospect · Gold /50 | 39 |
| Snack-Pack | 36 |
| BDC Chrome Prospect · Steel Metal /100 | 34 |
| Etched in Glass | 34 |
| BDC Chrome Prospect · Sapphire | 30 |
| BDC Chrome Prospect · Aqua /125 · Auto | 27 |
| BDC Chrome Prospect · Gold /50 · Auto | 27 |
| BDC Chrome Prospect · Logo Refractor /35 | 25 |
| Image Variations | 25 |
| BDC Chrome Prospect · Yellow /75 · Auto | 23 |
| BDC Chrome Prospect · Orange /25 | 17 |
| BDC Chrome Prospect · Fuchsia Reptilian /199 · Auto | 16 |
| BDC Chrome Prospect · Orange /25 · Auto | 16 |
| Final Draft | 16 |
| BDC Chrome Prospect · Sparkle | 15 |
| BDC Chrome Prospect · Aqua Reptilian | 13 |
| BDC Chrome Prospect · Speckle Refractor | 10 |
| Bowman Spotlight | 10 |
| BDC Chrome Prospect · Parallel · Auto | 9 |
| BDC Chrome Prospect · Sparkle · Auto | 8 |
| Bowman Draft Night · Gold | 8 |
| BDC Chrome Prospect · Red /5 | 7 |
| BDC Chrome Prospect · Black /73 · Auto | 5 |
| BDC Chrome Prospect · Mini Diamond | 5 |
| BDC Chrome Prospect · Speckle Refractor · Auto | 5 |
| Bowman In Action · Gold | 5 |
| Bowman In Action · Orange | 5 |
| Sapphire | 5 |
| Bowman Axis · Gold | 4 |
| Bowman Axis · Orange | 4 |
| Prized Prospects · Auto | 4 |
| Prized Prospects · Gold | 4 |
| Prized Prospects · Green | 4 |
| Prized Prospects · Mini Diamond | 4 |
| Prized Prospects · Orange | 4 |
| BDC Chrome Prospect · Red /5 · Auto | 3 |
| BDC Chrome Prospect · X-Fractor · Auto | 3 |
| Base-Paper · Black Border | 3 |
| Bowman Axis · Mini Diamond | 3 |
| Bowman Axis · Parallel | 3 |
| Bowman Draft Night · Green | 3 |
| Bowman Draft Night · Mini Diamond | 3 |
| Bowman In Action · Auto | 3 |
| Bowman In Action · Blue | 3 |
| Bowman In Action · Green | 3 |
| Bowman In Action · Mini Diamond | 3 |
| Crystallized | 3 |
| Image Variations · Green · Auto | 3 |
| BDC Chrome Prospect · Magenta Printing Plate | 2 |
| BDC Chrome Prospect · Parallel | 2 |
| BDC Chrome Prospect · True Black /10 | 2 |
| Bowman Axis · Green | 2 |
| Bowman Draft Night · Auto | 2 |
| Bowman Draft Night · Gold · Mini Diamond · Auto | 2 |
| Chrome Prospect College Variations | 2 |
| Crystallized · Gold | 2 |
| Crystallized · Orange | 2 |
| BDC Chrome Prospect · Black /73 | 1 |
| BDC Chrome Prospect · Printing Plate · Auto | 1 |
| BDC Chrome Prospect · Refractor · Auto | 1 |
| BDC Chrome Prospect · Speckle · Auto | 1 |
| BDC Chrome Prospect · Superfractor · Auto | 1 |
| BDC Chrome Prospect · True Black /10 · Auto | 1 |
| Bowman Axis · Red | 1 |
| Bowman Draft Night · Orange · Auto | 1 |
| Bowman Draft Night · Purple | 1 |
| Bowman In Action · Purple | 1 |
| Bowman In Action · Red | 1 |
| Bowman Spotlight · Red | 1 |
| Chrome Prospect College Variations · Red /5 | 1 |
| Crystallized · Red | 1 |
| Image Variations · Auto | 1 |
| Image Variations · Purple · Auto | 1 |
| Prized Prospects · Blue | 1 |
| Prized Prospects · Purple | 1 |
| Prized Prospects · Red | 1 |

