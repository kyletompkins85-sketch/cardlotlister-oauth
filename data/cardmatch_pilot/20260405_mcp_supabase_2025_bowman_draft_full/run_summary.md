# Pilot run 20260405_mcp_supabase_2025_bowman_draft_full

- **Input:** `data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/pilot_scored_full.csv`
- **Rows read:** 41357
- **Rows scored (after run filter):** 41357
- **Skipped by run_id filter:** 0
- **Checklist:** `/Users/kyletompkins/Documents/GitHub/cardlotlister-oauth/data/checklists/normalized/2025_Bowman_Draft_Normalized.csv`
- **Run allowlist size:** 0

## Counts

- **pilot_player_status:** {'matched': 28229, 'unknown': 13128}
- **is_likely_base yes:** 3565 / 41357
- **review_slice rows (BD-1..BD-10 players):** 3429
- **classification_focus (`review_targets.json`):** `unknown_player` → **28** rows in `review_focus.csv`
- **review_unclassified (unknown player):** 13128

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
| BDC Chrome Prospect · Refractor | 4742 |
| Base-Paper | 3569 |
| BDC Chrome Prospect · Base | 2783 |
| BDC Chrome Prospect · Auto | 2471 |
| BDC Chrome Prospect · Sky Blue /499 | 1036 |
| Prized Prospects | 971 |
| Bowman Axis · Base | 792 |
| BDC Chrome Prospect · Green /99 | 670 |
| BDC Chrome Prospect · Blue /150 | 574 |
| BDC Chrome Prospect · X-Fractor | 551 |
| BDC Chrome Prospect · Sky Blue /499 · Auto | 520 |
| Bowman Draft Night | 487 |
| Bowman In Action | 472 |
| BDC Chrome Prospect · Blue /150 · Auto | 424 |
| BDC Chrome Prospect · Purple /250 · Auto | 398 |
| BDC Chrome Prospect · Purple /250 | 391 |
| BDC Chrome Prospect · Yellow /75 | 324 |
| BDC Chrome Prospect · Aqua /125 | 302 |
| BDC Chrome Prospect · Green /99 · Auto | 290 |
| BDC Chrome Prospect · Fuchsia Reptilian /199 | 260 |
| BDC Chrome Prospect · Gold /50 · Auto | 234 |
| BDC Chrome Prospect · Gold /50 | 231 |
| Snack-Pack | 200 |
| BDC Chrome Prospect · Aqua /125 · Auto | 185 |
| BDC Chrome Prospect · Steel Metal /100 | 181 |
| BDC Chrome Prospect · Yellow /75 · Auto | 165 |
| BDC Chrome Prospect · Aqua Reptilian | 141 |
| BDC Chrome Prospect · Orange /25 | 134 |
| Etched in Glass | 116 |
| BDC Chrome Prospect · Red /5 | 110 |
| BDC Chrome Prospect · Logo Refractor /35 | 103 |
| BDC Chrome Prospect · Fuchsia Reptilian /199 · Auto | 89 |
| Final Draft | 81 |
| Image Variations | 77 |
| BDC Chrome Prospect · Sparkle | 73 |
| Bowman Spotlight | 67 |
| BDC Chrome Prospect · Orange /25 · Auto | 64 |
| BDC Chrome Prospect · Speckle Refractor | 61 |
| BDC Chrome Prospect · Parallel · Auto | 60 |
| BDC Chrome Prospect · Red /5 · Auto | 57 |
| BDC Chrome Prospect · Sparkle · Auto | 57 |
| BDC Chrome Prospect · Mini Diamond | 47 |
| BDC Chrome Prospect · Sapphire | 42 |
| BDC Chrome Prospect · X-Fractor · Auto | 42 |
| Bowman In Action · Mini Diamond | 35 |
| Crystallized | 34 |
| Bowman Axis · Parallel | 31 |
| Bowman In Action · Gold | 29 |
| Bowman In Action · Green | 27 |
| Bowman In Action · Red | 25 |
| Bowman Draft Night · Gold | 23 |
| BDC Chrome Prospect · Black /73 · Auto | 22 |
| Bowman Axis · Gold | 22 |
| BDC Chrome Prospect · True Black /10 | 21 |
| Bowman In Action · Auto | 21 |
| Prized Prospects · Green | 20 |
| BDC Chrome Prospect · Speckle Refractor · Auto | 19 |
| Bowman Axis · Mini Diamond | 18 |
| Bowman Axis · Green | 17 |
| Prized Prospects · Auto | 16 |
| Prized Prospects · Gold | 16 |
| Prized Prospects · Mini Diamond | 16 |
| Chrome Prospect College Variations | 15 |
| BDC Chrome Prospect · True Black /10 · Auto | 14 |
| Bowman In Action · Orange | 14 |
| Crystallized · Gold | 14 |
| Crystallized · Orange | 14 |
| Bowman Draft Night · Mini Diamond | 13 |
| BDC Chrome Prospect · Magenta Printing Plate | 12 |
| Bowman Draft Night · Auto | 12 |
| Prized Prospects · Orange | 12 |
| BDC Chrome Prospect · Black /73 | 11 |
| Bowman Axis · Orange | 10 |
| Bowman Spotlight · Red | 10 |
| BDC Chrome Prospect · Black Geometric /10 | 8 |
| BDC Chrome Prospect · Speckle · Auto | 8 |
| BDC Chrome Prospect · Printing Plate | 7 |
| BDC Chrome Prospect · Superfractor | 7 |
| Base-Paper · Black Border | 6 |
| Image Variations · Auto | 6 |
| BDC Chrome Prospect · Mini Diamond · Auto | 5 |
| Bowman Draft Night · Green | 5 |
| Bowman In Action · Blue | 5 |
| Chrome Prospect College Variations · Gold /50 | 5 |
| Image Variations · Green · Auto | 5 |
| Sapphire | 5 |
| BDC Chrome Prospect · Black Printing Plate | 4 |
| BDC Chrome Prospect · Parallel | 4 |
| BDC Chrome Prospect · Printing Plate · Auto | 4 |
| BDC Chrome Prospect · Superfractor · Auto | 4 |
| BDC Chrome Prospect · Yellow Printing Plate | 4 |
| Bowman In Action · Gold · Auto | 4 |
| Bowman In Action · Lava · Auto | 4 |
| Bowman In Action · Orange · Auto | 4 |
| Bowman In Action · Speckle | 4 |
| Bowman In Action · Wave · Auto | 4 |
| Chrome Prospect College Variations · Red /5 | 4 |
| Crystallized · Black | 4 |
| Image Variations · Orange | 4 |
| Bowman Draft Night · Gold · Mini Diamond · Auto | 3 |
| Bowman Draft Night · Orange | 3 |
| Chrome Prospect College Variations · Orange /25 | 3 |
| Crystallized · Red | 3 |
| BDC Chrome Prospect · Black Geometric /10 · Auto | 2 |
| BDC Chrome Prospect · Fuchsia Reptilian · Wave · Auto | 2 |
| BDC Chrome Prospect · Refractor · Auto | 2 |
| BDC Chrome Prospect · Steel Metal · Auto | 2 |
| BDC Chrome Prospect · Yellow Printing Plate · Auto | 2 |
| Bowman Axis · Superfractor | 2 |
| Bowman Draft Night · Purple | 2 |
| Bowman Draft Night · Superfractor · Auto | 2 |
| Bowman In Action · Black | 2 |
| Bowman In Action · Red · Auto | 2 |
| Bowman In Action · Superfractor | 2 |
| Chrome Prospect College Variations · Auto | 2 |
| Chrome Prospect College Variations · Black /73 | 2 |
| Final Draft · Red | 2 |
| Prized Prospects · Sparkle | 2 |
| BDC Chrome Prospect · Black Printing Plate · Auto | 1 |
| BDC Chrome Prospect · Fuchsia Reptilian | 1 |
| BDC Chrome Prospect · Wave · Auto | 1 |
| Bowman Axis · Red | 1 |
| Bowman Draft Night · Orange · Auto | 1 |
| Bowman Draft Night · Red | 1 |
| Bowman In Action · Purple | 1 |
| Chrome Prospect College Variations · Purple /250 | 1 |
| Image Variations · Purple · Auto | 1 |
| Prized Prospects · Blue | 1 |
| Prized Prospects · Green · Auto | 1 |
| Prized Prospects · Purple | 1 |
| Prized Prospects · Red | 1 |

