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
| Chrome · Refractor | 4742 |
| Base-Paper | 3569 |
| Chrome · Base | 2783 |
| Chrome · Auto | 2468 |
| Chrome · Sky Blue /499 | 1036 |
| Prized Prospects | 908 |
| Bowman Axis · Base | 792 |
| Chrome · Green /99 | 670 |
| Chrome · Blue /150 | 574 |
| Chrome · X-Fractor | 551 |
| Chrome · Sky Blue /499 · Auto | 520 |
| Bowman Draft Night | 463 |
| Bowman In Action | 454 |
| Chrome · Blue /150 · Auto | 424 |
| Chrome · Purple /250 · Auto | 398 |
| Chrome · Purple /250 | 391 |
| Chrome · Yellow /75 | 324 |
| Chrome · Aqua /125 | 302 |
| Chrome · Green /99 · Auto | 290 |
| Chrome · Fuchsia Reptilian /199 | 261 |
| Chrome · Gold /50 · Auto | 234 |
| Chrome · Gold /50 | 231 |
| Snack-Pack | 200 |
| Chrome · Aqua /125 · Auto | 185 |
| Chrome · Steel Metal /100 | 181 |
| Chrome · Yellow /75 · Auto | 165 |
| Chrome · Aqua Reptilian | 141 |
| Chrome · Orange /25 | 134 |
| Etched in Glass | 116 |
| Chrome · Red /5 | 110 |
| Chrome · Logo Refractor /35 | 103 |
| Chrome · Fuchsia Reptilian /199 · Auto | 89 |
| Final Draft | 81 |
| Image Variations | 77 |
| Chrome · Sparkle | 73 |
| Bowman Spotlight | 65 |
| Chrome · Orange /25 · Auto | 64 |
| Chrome · Speckle Refractor | 61 |
| Chrome · Parallel · Auto | 60 |
| Chrome · Red /5 · Auto | 57 |
| Chrome · Sparkle · Auto | 56 |
| Chrome · Mini Diamond | 47 |
| Prized Prospects /250 | 47 |
| Chrome · Sapphire | 42 |
| Chrome · X-Fractor · Auto | 42 |
| Bowman In Action · Mini Diamond /150 | 34 |
| Bowman Axis · Parallel | 31 |
| Crystallized | 31 |
| Bowman In Action · Gold /50 | 29 |
| Bowman In Action · Green /99 | 27 |
| Bowman In Action · Red /5 | 25 |
| Bowman Draft Night · Gold /50 | 23 |
| Bowman Axis · Gold | 22 |
| Chrome · Black /73 · Auto | 22 |
| Chrome · True Black /10 | 21 |
| Prized Prospects · Green /99 | 20 |
| Bowman Draft Night /250 | 19 |
| Chrome · Speckle Refractor · Auto | 19 |
| Bowman Axis · Mini Diamond | 18 |
| Bowman Axis · Green | 17 |
| Prized Prospects · Gold /50 | 16 |
| Chrome Prospect College Variations | 15 |
| Bowman In Action · Orange /25 | 14 |
| Chrome · True Black /10 · Auto | 14 |
| Crystallized · Gold /50 | 14 |
| Crystallized · Orange /25 | 14 |
| Prized Prospects · Mini Diamond /150 | 14 |
| Bowman Draft Night · Mini Diamond /150 | 13 |
| Bowman Draft Night /99 · Auto | 12 |
| Bowman In Action /150 | 12 |
| Chrome · Magenta Printing Plate | 12 |
| Prized Prospects · Orange /25 | 12 |
| Bowman In Action /75 · Auto | 11 |
| Chrome · Black /73 | 11 |
| Bowman Axis · Orange | 10 |
| Bowman In Action /99 · Auto | 10 |
| Bowman Spotlight · Red /5 | 10 |
| Chrome · Black Geometric /10 | 8 |
| Chrome · Speckle /71 · Auto | 8 |
| Prized Prospects /99 · Auto | 8 |
| Chrome · Printing Plate | 7 |
| Chrome · Superfractor | 7 |
| Prized Prospects /99 | 7 |
| Base-Paper · Black Border | 6 |
| Image Variations · Auto | 6 |
| Bowman Draft Night · Green /99 | 5 |
| Bowman In Action · Blue /150 | 5 |
| Chrome Prospect College Variations · Gold /50 | 5 |
| Image Variations · Green · Auto | 5 |
| Sapphire | 5 |
| Bowman In Action · Gold /50 · Auto | 4 |
| Bowman In Action · Lava /75 · Auto | 4 |
| Bowman In Action · Orange /25 · Auto | 4 |
| Bowman In Action · Speckle /150 | 4 |
| Bowman In Action · Wave /75 · Auto | 4 |
| Chrome Prospect College Variations · Red /5 | 4 |
| Chrome · Black Printing Plate | 4 |
| Chrome · Mini Diamond /71 · Auto | 4 |
| Chrome · Parallel | 4 |
| Chrome · Superfractor · Auto | 4 |
| Chrome · Yellow Printing Plate | 4 |
| Crystallized · Black /73 | 4 |
| Image Variations · Orange | 4 |
| Prized Prospects /5 · Auto | 4 |
| Prized Prospects · Auto | 4 |
| Bowman Draft Night · Gold /50 · Mini Diamond · Auto | 3 |
| Bowman Draft Night · Orange /25 | 3 |
| Bowman In Action /99 | 3 |
| Chrome Prospect College Variations · Orange /25 | 3 |
| Chrome · Printing Plate · Auto | 3 |
| Crystallized /25 | 3 |
| Crystallized · Red /5 | 3 |
| Prized Prospects /150 | 3 |
| Prized Prospects /50 | 3 |
| Bowman Axis · Superfractor | 2 |
| Bowman Draft Night /150 | 2 |
| Bowman Draft Night /99 | 2 |
| Bowman Draft Night · Purple /250 | 2 |
| Bowman Draft Night · Superfractor /1 · Auto | 2 |
| Bowman In Action /10 | 2 |
| Bowman In Action · Black /73 | 2 |
| Bowman In Action · Red /5 · Auto | 2 |
| Bowman In Action · Superfractor /1 | 2 |
| Bowman Spotlight /5 | 2 |
| Chrome /10 · Auto | 2 |
| Chrome Prospect College Variations · Auto | 2 |
| Chrome Prospect College Variations · Black /73 | 2 |
| Chrome · Black Geometric /10 · Auto | 2 |
| Chrome · Fuchsia Reptilian · Wave /199 · Auto | 2 |
| Chrome · Refractor · Auto | 2 |
| Chrome · Steel Metal /100 · Auto | 2 |
| Chrome · Yellow Printing Plate · Auto | 2 |
| Final Draft · Red /5 | 2 |
| Prized Prospects /199 | 2 |
| Prized Prospects · Mini Diamond | 2 |
| Prized Prospects · Sparkle /150 | 2 |
| Bowman Axis · Red | 1 |
| Bowman Draft Night /25 | 1 |
| Bowman Draft Night · Orange /25 · Auto | 1 |
| Bowman Draft Night · Red /5 | 1 |
| Bowman In Action /199 | 1 |
| Bowman In Action · Mini Diamond | 1 |
| Bowman In Action · Purple /250 | 1 |
| Chrome /1 · Auto | 1 |
| Chrome Prospect College Variations · Purple /250 | 1 |
| Chrome · Black Printing Plate · Auto | 1 |
| Chrome · Mini Diamond · Auto | 1 |
| Chrome · Printing Plate /1 · Auto | 1 |
| Chrome · Sparkle /71 · Auto | 1 |
| Chrome · Wave · Auto | 1 |
| Image Variations · Purple · Auto | 1 |
| Prized Prospects /25 | 1 |
| Prized Prospects · Blue /150 | 1 |
| Prized Prospects · Green /99 · Auto | 1 |
| Prized Prospects · Purple /250 | 1 |
| Prized Prospects · Red /5 | 1 |

