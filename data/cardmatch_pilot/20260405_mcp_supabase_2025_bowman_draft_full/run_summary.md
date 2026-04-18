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
| Chrome · Auto · Sky Blue /499 | 520 |
| Bowman Draft Night | 463 |
| Bowman In Action | 454 |
| Chrome · Auto · Blue /150 | 424 |
| Chrome · Auto · Purple /250 | 398 |
| Chrome · Purple /250 | 391 |
| Chrome · Yellow /75 | 324 |
| Chrome · Aqua /125 | 302 |
| Chrome · Auto · Green /99 | 290 |
| Chrome · Fuchsia Reptilian /199 | 261 |
| Chrome · Auto · Gold /50 | 234 |
| Chrome · Gold /50 | 231 |
| Snack-Pack | 200 |
| Chrome · Auto · Aqua /125 | 185 |
| Chrome · Steel Metal /100 | 181 |
| Chrome · Auto · Yellow /75 | 165 |
| Chrome · Aqua Reptilian | 141 |
| Chrome · Orange /25 | 134 |
| Etched in Glass | 116 |
| Chrome · Red /5 | 110 |
| Chrome · Logo Refractor /35 | 103 |
| Chrome · Auto · Fuchsia Reptilian /199 | 89 |
| Final Draft | 81 |
| Image Variations | 77 |
| Chrome · Sparkle | 73 |
| Bowman Spotlight | 65 |
| Chrome · Auto · Orange /25 | 64 |
| Chrome · Speckle Refractor | 61 |
| Chrome · Auto · Parallel | 60 |
| Chrome · Auto · Red /5 | 57 |
| Chrome · Auto · Sparkle | 56 |
| Prized Prospects · Purple /250 | 48 |
| Bowman In Action · Mini Diamond /150 | 47 |
| Chrome · Mini Diamond | 47 |
| Chrome · Auto · X-Fractor | 42 |
| Chrome · Sapphire | 42 |
| Bowman Axis · Parallel | 31 |
| Crystallized | 31 |
| Bowman In Action · Green /99 | 30 |
| Bowman In Action · Gold /50 | 29 |
| Prized Prospects · Green /99 | 27 |
| Bowman In Action · Red /5 | 25 |
| Bowman Draft Night · Gold /50 | 23 |
| Bowman Axis · Gold | 22 |
| Chrome · Auto · Black /73 | 22 |
| Bowman Draft Night · Purple /250 | 21 |
| Chrome · True Black /10 | 21 |
| Prized Prospects · Mini Diamond /150 | 21 |
| Bowman In Action · Auto · Yellow /75 | 19 |
| Chrome · Auto · Speckle Refractor | 19 |
| Prized Prospects · Gold /50 | 19 |
| Bowman Axis · Mini Diamond | 18 |
| Bowman Axis · Green | 17 |
| Bowman Draft Night · Mini Diamond /150 | 15 |
| Chrome Prospect College Variations | 15 |
| Bowman In Action · Orange /25 | 14 |
| Chrome · Auto · True Black /10 | 14 |
| Crystallized · Gold /50 | 14 |
| Crystallized · Orange /25 | 14 |
| Prized Prospects · Orange /25 | 13 |
| Bowman Draft Night · Auto · Green /99 | 12 |
| Chrome · Magenta Printing Plate | 12 |
| Chrome · Black /73 | 11 |
| Bowman Axis · Orange | 10 |
| Bowman In Action · Auto · Green /99 | 10 |
| Bowman Spotlight · Red /5 | 10 |
| Prized Prospects · Auto · Green /99 | 9 |
| Chrome · Auto · Speckle /71 | 8 |
| Chrome · Black Geometric /10 | 8 |
| Bowman Draft Night · Green /99 | 7 |
| Chrome · Printing Plate | 7 |
| Chrome · Superfractor | 7 |
| Base-Paper · Black Border | 6 |
| Image Variations · Auto | 6 |
| Bowman In Action · Blue /150 | 5 |
| Chrome Prospect College Variations · Gold /50 | 5 |
| Image Variations · Auto · Green | 5 |
| Sapphire | 5 |
| Bowman Draft Night · Orange /25 | 4 |
| Bowman In Action · Auto · Gold /50 | 4 |
| Bowman In Action · Auto · Orange /25 | 4 |
| Bowman In Action · Mini Diamond /150 · Speckle | 4 |
| Chrome Prospect College Variations · Red /5 | 4 |
| Chrome · Auto · Mini Diamond /71 | 4 |
| Chrome · Auto · Superfractor | 4 |
| Chrome · Black Printing Plate | 4 |
| Chrome · Parallel | 4 |
| Chrome · Yellow Printing Plate | 4 |
| Crystallized · Black /73 | 4 |
| Image Variations · Orange | 4 |
| Prized Prospects · Auto | 4 |
| Prized Prospects · Auto · Red /5 | 4 |
| Bowman Draft Night · Auto · Gold /50 · Mini Diamond | 3 |
| Chrome Prospect College Variations · Orange /25 | 3 |
| Chrome · Auto · Printing Plate | 3 |
| Crystallized /25 | 3 |
| Crystallized · Red /5 | 3 |
| Bowman Axis · Superfractor | 2 |
| Bowman Draft Night · Auto · Superfractor /1 | 2 |
| Bowman In Action /10 | 2 |
| Bowman In Action · Auto · Red /5 | 2 |
| Bowman In Action · Black /73 | 2 |
| Bowman In Action · Superfractor /1 | 2 |
| Bowman Spotlight /5 | 2 |
| Chrome /10 · Auto | 2 |
| Chrome Prospect College Variations · Auto | 2 |
| Chrome Prospect College Variations · Black /73 | 2 |
| Chrome · Auto · Black Geometric /10 | 2 |
| Chrome · Auto · Fuchsia Reptilian · Wave /199 | 2 |
| Chrome · Auto · Refractor | 2 |
| Chrome · Auto · Steel Metal /100 | 2 |
| Chrome · Auto · Yellow Printing Plate | 2 |
| Final Draft · Red /5 | 2 |
| Prized Prospects · Fuchsia Reptilian /199 | 2 |
| Bowman Axis · Red | 1 |
| Bowman Draft Night · Auto · Orange /25 | 1 |
| Bowman Draft Night · Red /5 | 1 |
| Bowman In Action · Fuchsia Reptilian /199 | 1 |
| Bowman In Action · Purple /250 | 1 |
| Chrome /1 · Auto | 1 |
| Chrome Prospect College Variations · Purple /250 | 1 |
| Chrome · Auto · Black Printing Plate | 1 |
| Chrome · Auto · Mini Diamond | 1 |
| Chrome · Auto · Printing Plate /1 | 1 |
| Chrome · Auto · Sparkle /71 | 1 |
| Chrome · Auto · Wave | 1 |
| Image Variations · Auto · Purple | 1 |
| Prized Prospects · Blue /150 | 1 |
| Prized Prospects · Red /5 | 1 |

