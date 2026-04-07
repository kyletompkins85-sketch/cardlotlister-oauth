# `scripts/` layout

| Path | Purpose |
|------|---------|
| **`topps_update_2025/`** | 2025 Topps Update market pipeline: term-search pulls, JSONL→CSV, classifiers, **Monte Carlo pairwise ranking CLIs** (`simulate_ct_price_rankings.py`, `simulate_player_price_rankings_same_ct.py`, `export_pairwise_ranking_tables.py` — core logic in `cardmatch/pairwise_price_rankings.py`), DAD trim, AutoGluon training, underpriced scoring, `pull_listings.mjs`. Invoked by `.github/workflows/`. |
| **`cardmatch/`** | Cardmatch pilots: rescore committed outputs, full worker search, refresh `review_focus.csv`, **Bowman pairwise ranking export** (`export_bowman_pairwise_ranking_tables.py`), **AutoGluon rank→price** (`train_bowman_rank_price_autogluon.py`, optional `requirements-bowman-autogluon.txt`). |
| **`checklists/`** | Checklist normalization and derived player tables. |

Example (from repo root):

```bash
python3 scripts/topps_update_2025/title_common_words.py --help
bash scripts/cardmatch/rescore_cardmatch_committed_pilot.sh
```
