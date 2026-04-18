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
| Chrome · Refractor | 819 |
| Chrome · Auto | 430 |
| Chrome · Base | 429 |
| Base-Paper | 426 |
| Chrome · Sky Blue /499 | 206 |
| Prized Prospects | 143 |
| Bowman Axis · Base | 130 |
| Chrome · Blue /150 | 118 |
| Chrome · Green /99 | 113 |
| Chrome · X-Fractor | 96 |
| Chrome · Auto · Sky Blue /499 | 94 |
| Chrome · Auto · Blue /150 | 78 |
| Chrome · Auto · Purple /250 | 77 |
| Chrome · Aqua /125 | 74 |
| Chrome · Auto · Green /99 | 69 |
| Chrome · Purple /250 | 68 |
| Chrome · Yellow /75 | 64 |
| Bowman Draft Night | 58 |
| Chrome · Fuchsia Reptilian /199 | 57 |
| Bowman In Action | 55 |
| Chrome · Gold /50 | 39 |
| Snack-Pack | 36 |
| Chrome · Steel Metal /100 | 34 |
| Etched in Glass | 34 |
| Chrome · Sapphire | 30 |
| Chrome · Auto · Aqua /125 | 27 |
| Chrome · Auto · Gold /50 | 27 |
| Chrome · Logo Refractor /35 | 25 |
| Image Variations | 25 |
| Chrome · Auto · Yellow /75 | 23 |
| Chrome · Orange /25 | 17 |
| Chrome · Auto · Fuchsia Reptilian /199 | 16 |
| Chrome · Auto · Orange /25 | 16 |
| Final Draft | 16 |
| Chrome · Sparkle | 15 |
| Chrome · Aqua Reptilian | 13 |
| Prized Prospects · Purple /250 | 12 |
| Bowman Spotlight | 10 |
| Chrome · Speckle Refractor | 10 |
| Chrome · Auto · Parallel | 9 |
| Bowman Draft Night · Gold /50 | 8 |
| Chrome · Auto · Sparkle | 8 |
| Chrome · Red /5 | 7 |
| Bowman Draft Night · Purple /250 | 5 |
| Bowman In Action · Gold /50 | 5 |
| Bowman In Action · Mini Diamond /150 | 5 |
| Bowman In Action · Orange /25 | 5 |
| Chrome · Auto · Black /73 | 5 |
| Chrome · Auto · Speckle Refractor | 5 |
| Chrome · Mini Diamond | 5 |
| Sapphire | 5 |
| Bowman Axis · Gold | 4 |
| Bowman Axis · Orange | 4 |
| Bowman Draft Night · Green /99 | 4 |
| Bowman In Action · Green /99 | 4 |
| Prized Prospects · Gold /50 | 4 |
| Prized Prospects · Green /99 | 4 |
| Prized Prospects · Mini Diamond /150 | 4 |
| Prized Prospects · Orange /25 | 4 |
| Base-Paper · Black Border | 3 |
| Bowman Axis · Mini Diamond | 3 |
| Bowman Axis · Parallel | 3 |
| Bowman Draft Night · Mini Diamond /150 | 3 |
| Bowman In Action · Auto · Yellow /75 | 3 |
| Bowman In Action · Blue /150 | 3 |
| Chrome · Auto · Red /5 | 3 |
| Chrome · Auto · X-Fractor | 3 |
| Crystallized | 3 |
| Image Variations · Auto · Green | 3 |
| Prized Prospects · Auto · Green /99 | 3 |
| Bowman Axis · Green | 2 |
| Bowman Draft Night · Auto · Gold /50 · Mini Diamond | 2 |
| Bowman Draft Night · Auto · Green /99 | 2 |
| Chrome Prospect College Variations | 2 |
| Chrome · Magenta Printing Plate | 2 |
| Chrome · Parallel | 2 |
| Chrome · True Black /10 | 2 |
| Crystallized · Gold /50 | 2 |
| Crystallized · Orange /25 | 2 |
| Prized Prospects · Fuchsia Reptilian /199 | 2 |
| Bowman Axis · Red | 1 |
| Bowman Draft Night · Auto · Orange /25 | 1 |
| Bowman In Action · Fuchsia Reptilian /199 | 1 |
| Bowman In Action · Purple /250 | 1 |
| Bowman In Action · Red /5 | 1 |
| Bowman Spotlight · Red /5 | 1 |
| Chrome Prospect College Variations · Red /5 | 1 |
| Chrome · Auto · Printing Plate /1 | 1 |
| Chrome · Auto · Refractor | 1 |
| Chrome · Auto · Speckle /71 | 1 |
| Chrome · Auto · Superfractor | 1 |
| Chrome · Auto · True Black /10 | 1 |
| Chrome · Black /73 | 1 |
| Crystallized · Red /5 | 1 |
| Image Variations · Auto | 1 |
| Image Variations · Auto · Purple | 1 |
| Prized Prospects · Auto | 1 |
| Prized Prospects · Blue /150 | 1 |
| Prized Prospects · Red /5 | 1 |

