# 2025 Topps Update — term search and market artifacts

Committed snapshots and outputs for the **Topps Update** listing classifier, player matching, comp simulations, and price-model workflows. Producers are scripts under `scripts/topps_update_2025/` and workflows under `.github/workflows/`.

## Monte Carlo pairwise price duels

This folder’s **`*_ct_sim_*`** and **`*_player_sim_*`** outputs come from two related simulations. Both treat the classified market table as a bag of listings (each row: `player_guess`, `CT_list`, `all_in_price`, …). They **do not** model a full joint distribution of prices; they **repeatedly sample two listings**, compare **all-in price**, and aggregate **wins** and **margins** so you can see **which card types tend to price above others** (holding player fixed) and **which players tend to price above others** (holding card type fixed).

**Shared rules**

- Default **50,000** pairwise comparisons per run (`--iterations`), with a fixed **RNG seed** (`--seed`, default `42`) for reproducibility.
- Rows whose `CT_list` contains a **comma** (multi-type) are **skipped** so each row is one card type.
- **Ties** (equal price) are skipped; they do not count as wins or losses.
- Each duel credits one side with a **win**, the other with a **loss**. **`win_rate`** = wins / (wins + losses) for that entity in duels where it appeared. **`avg_win_margin`** = average (winner price − loser price) over **wins only** (how big the wins tend to be).

**Simulation A — rank card types (same player, different `CT_list`)**

- **Script:** [`scripts/topps_update_2025/simulate_ct_price_rankings.py`](../../scripts/topps_update_2025/simulate_ct_price_rankings.py)
- **Workflow:** [`.github/workflows/simulate_ct_price_rankings.yml`](../../.github/workflows/simulate_ct_price_rankings.yml)
- **Idea:** Pick a random listing A, then pick a **second listing for the same player** with a **different** `CT_list`, compare prices. The **more expensive** listing’s **card type** gets the win. Repeat many times.
- **Eligibility:** Only players who appear with **at least two distinct** `CT_list` values in the table can generate a duel.
- **Read the summary:** Higher **`win_rate`** for a `CT_list` means that type **wins head-to-head price comparisons more often** against another type for the **same** player (a rough “expensive vs cheap” spectrum **across card types**, mixed over players according to who shows up in the data).

**Simulation B — rank players (same `CT_list`, different players)**

- **Script:** [`scripts/topps_update_2025/simulate_player_price_rankings_same_ct.py`](../../scripts/topps_update_2025/simulate_player_price_rankings_same_ct.py)
- **Workflow:** [`.github/workflows/simulate_player_price_rankings_same_ct.yml`](../../.github/workflows/simulate_player_price_rankings_same_ct.yml)
- **Idea:** Pick a random listing A, **keep its `CT_list`**, pick a **different player** who also has that card type, choose a listing for that pair, compare prices. The **more expensive** listing’s **player** gets the win.
- **Eligibility:** Only `CT_list` values that appear with **at least two different** players can generate a duel.
- **Read the summary:** Higher **`win_rate`** for a player means that player **wins head-to-head price comparisons more often** against another player for the **same** card type (a rough “expensive vs cheap” spectrum **across players** for comparable types).

**Caveats**

- Win rates depend on **how often** each player or type is sampled (listing frequency and eligibility), not on a balanced experimental design.
- This is a **descriptive** market exercise, not a causal statement about intrinsic card value.

**Library implementation:** The same algorithms live in [`cardmatch/pairwise_price_rankings.py`](../../cardmatch/pairwise_price_rankings.py) (`run_monte_carlo_card_type_rankings_same_player`, `run_monte_carlo_player_rankings_same_card_type`, `run_pairwise_monte_carlo_rankings`). The Topps CLIs load CSV and call those functions. For **Bowman Draft** pilot rows, build `(player, card_type, price+shipping)` triples with [`cardmatch/bowman_pilot_triples.py`](../../cardmatch/bowman_pilot_triples.py) before ranking.

## Exports and tables

| Files | Description |
|-------|-------------|
| `term_search_items_2025_topps_update.jsonl` (+ `.meta.json`) | Raw term-search JSONL export. |
| `term_search_items_table.csv` | Flattened table (e.g. `jsonl_to_table.py`, `convert_term_search_items_to_csv.yml`). |
| `term_search_items_table_classified.csv` | After Bowman/Topps classifier + player column (`classify_term_search_items_csv.py`). |
| `term_search_items_table_classified_1000.csv` | First-1000-row classification pass (`append_flags_first_1000.py`). |

## Simulations and trimming

| Files | Description |
|-------|-------------|
| `term_search_items_table_classified_ct_sim_*.csv` | **Same-player, different card type** Monte Carlo rankings ([`simulate_ct_price_rankings.yml`](../../.github/workflows/simulate_ct_price_rankings.yml)). |
| `term_search_items_table_classified_player_sim_*.csv` | **Same card type, different player** Monte Carlo rankings ([`simulate_player_price_rankings_same_ct.yml`](../../.github/workflows/simulate_player_price_rankings_same_ct.yml)). |
| `term_search_items_table_classified_pairwise_*_rankings_with_listings.csv` | **Topps Update term-search table only:** combined pairwise rankings plus **listing_count** and **avg_listing_price** ([`export_pairwise_ranking_tables.py`](../../scripts/topps_update_2025/export_pairwise_ranking_tables.py)). For **Bowman Draft** pilot data, use [`export_bowman_pairwise_ranking_tables.py`](../../scripts/cardmatch/export_bowman_pairwise_ranking_tables.py) under `data/cardmatch_pilot/`. |
| `term_search_items_table_classified_lowest_vs_second_ratio.csv` | Cheapest vs second ratio (`.github/workflows/find_cheapest_vs_second_ratio.yml`). |
| `term_search_items_table_classified_trimmed_to_dad.csv` | Trimmed to DAD pairs (`.github/workflows/trim_market_to_dad_pairs.yml`). |

## Price model

| Path | Description |
|------|-------------|
| `term_search_items_table_classified_trimmed_to_dad_ag_price_model/` | AutoGluon training output (`train_price_model_autogluon.yml`). |
| `term_search_items_table_classified_underpriced_vs_model.csv` (+ `_meta.json`) | Underpriced vs model (`score_market_underpriced.yml`). |

## Listings dataset (non–term-search)

| Files | Description |
|-------|-------------|
| `listings_2025_topps_update.jsonl` (+ `.meta.json`) | Listings export. |
| `listings_2025_topps_update_jsonl_classified.csv` | Classified listings (`classify_existing_listings_json.py`). |

## Supporting CSVs

| File | Description |
|------|-------------|
| `2025_Topps_Update_player_list.csv` | Default player list for classifiers (`--players-csv`). |
| `common_words_*.csv` / `.meta.json` | Common-word analysis (`title_common_words.py`, `analyze_common_words.yml`). |
| `lot_player_guesses_*.csv` | Lot title guesses (`extract_player_guesses_from_lots.yml`). |
| `player_guesses_*.csv` | Fuzzy player guesses (`fuzzy_match_player_names.yml`). |
| `unclassified_titles_all.csv` | Keyword pull of unclassified titles (`pull_unclassified_titles_by_keyword.yml`). |

New workflow outputs for this pipeline should land under **`data/topps_update_2025/`** (see workflow defaults).
