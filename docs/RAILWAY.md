<!-- Cmd+F: GH_ANCHOR_DOCS_RAILWAY -->

# Bowman FastAPI on Railway

Deploys the **`web`** process from the repo root [`Procfile`](../Procfile): `python scripts/cardmatch/bowman_title_price_api.py`.

## Endpoints

| Method | Path | Notes |
|--------|------|--------|
| GET | `/health` | No model required; returns `{"status":"ok"}`. |
| POST | `/predict` | JSON body: `title` (required), optional `price`, `year`, `set_name`. Needs AutoGluon model dir on disk or 503. |
| POST | `/predict/batch` | JSON body: `items` — array of the same objects as `/predict` (min 1). Max length defaults to 200 (`BOWMAN_PREDICT_BATCH_MAX`). Response: `{"results":[...]}` with the same shape as `/predict` per element. 422 if over max. |
| POST | `/batch/observed-flags` | JSON body: `items` — each object requires `title` and **`price`** (observed listing price). Optional `id`, `player_key`, `year`, `set_name`. **No AutoGluon**; uses pairwise card-type ranks only. Response: `{"results":[...]}` per item with `card_type` (short labels, e.g. **Chrome · …** → shorter **Chrome …**, **Base-Paper** → **base**), `spread_ratio` (2nd-cheapest / cheapest for that `card_type`; only when this row’s price is the **player-cohort minimum** for that `card_type`; otherwise ``null``), `spread_ratio_third` (3rd-cheapest / cheapest; same min-price rule; ``null`` if fewer than three listings for that type in the same player cohort), `cheaper_than_worse_tier` (``null`` when not serial — uses classifier flags plus title heuristics for ``/N`` and ``a/b`` serials), `confidence`, `diagnostics` (includes `is_serial_listing`). Listing comparisons are computed within each player cohort in the payload (`player_key` when provided, otherwise title-derived player). Max length defaults to 200 (`BOWMAN_OBSERVED_BATCH_MAX`). |

## Environment variables

| Variable | Purpose |
|----------|---------|
| `PORT` | Set by Railway; app listens on `0.0.0.0`. |
| `BOWMAN_AUTOGLUON_DIR` | Path to trained **`agModels`** directory (AutoGluon `TabularPredictor.load`). Default under `data/cardmatch_pilot/.../bowman_rank_price_autogluon/agModels`. |
| `BOWMAN_PLAYER_RANKINGS_CSV` | Optional override for pairwise player ranks CSV. |
| `BOWMAN_CARD_TYPE_RANKINGS_CSV` | Optional override for pairwise card-type ranks CSV. |
| `BOWMAN_CHECKLIST_CSV` | Optional Bowman checklist CSV for `classify_listing` / matcher. |
| `BOWMAN_PREDICT_BATCH_MAX` | Max length of `items` for `POST /predict/batch` (default **200**). |
| `BOWMAN_OBSERVED_BATCH_MAX` | Max length of `items` for `POST /batch/observed-flags` (default **200**). |

**Startup:** If the two default pairwise CSVs are missing, the process exits (configure paths or commit [`data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/`](../data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/) files). If **`agModels`** is missing, the server still starts; **`POST /predict`** and **`POST /predict/batch`** return **503** with `autogluon_model_unavailable` until the model exists. **`POST /batch/observed-flags`** does not load AutoGluon and does not return 503 for a missing model.

## GitHub deploy vs model files

`agModels/` is **gitignored** (see [`.gitignore`](../.gitignore)). Pushes from GitHub **do not** include the model; use **Railway CLI** upload (below) or Git LFS / volume / object storage for production models.

## Fastest path: CLI deploy with local `agModels`

From the repo root (interactive `railway login` required):

```bash
railway login
railway link    # select project + `web` service
railway up --service web --no-gitignore --detach
```

[`--no-gitignore`](https://docs.railway.com/cli/up) includes gitignored files (including **`agModels/`**). [`.railwayignore`](../.railwayignore) still excludes `.env`, `.venv_ag/`, etc.

## Build

Root [`requirements.txt`](../requirements.txt) installs FastAPI, uvicorn, pandas, and **`autogluon.tabular==1.4.0`** (must match the version used when `agModels` was trained; mismatch causes load errors). Python **3.9** is set via [`.python-version`](../.python-version) and [`nixpacks.toml`](../nixpacks.toml) to match the environment used when `agModels` was trained.

## Related code

- API: [`scripts/cardmatch/bowman_title_price_api.py`](../scripts/cardmatch/bowman_title_price_api.py)
- Predict logic: [`cardmatch/bowman_title_price_predict.py`](../cardmatch/bowman_title_price_predict.py)
- Batch observed flags (spread ratio + inversion vs worse card types): [`cardmatch/bowman_batch_listing_flags.py`](../cardmatch/bowman_batch_listing_flags.py)

---

## 2025 Bowman retail POC (no AutoGluon / no pairwise ranks)

Separate FastAPI app: [`scripts/cardmatch/bowman_retail_deals_api.py`](../scripts/cardmatch/bowman_retail_deals_api.py). Use a **second Railway service** (or override the service **Start Command**) so the Draft `Procfile` `web` process stays unchanged.

**Install (slim):** [`requirements-bowman-retail-api.txt`](../requirements-bowman-retail-api.txt) — `fastapi`, `uvicorn`, `pydantic` only. Set Nixpacks/custom install to `pip install -r requirements-bowman-retail-api.txt` for this service.

**Start command:**

```bash
python scripts/cardmatch/bowman_retail_deals_api.py
```

### Endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | `{"status":"ok"}`. |
| POST | `/batch/deals` | JSON `{"items":[{"title","price","id"?,"player_key"?}, ...]}` (min 1 item). **Price required.** Response: `results` and `groups`. **Draft parity:** each row/cluster includes **`card_type`** (client groups by this string — append ` /{serial}` when `serial != -1`, e.g. `Paper` vs `Paper /399`) and **`card_type_display_order`** (same value as combo `sort_order` when known). Also: classification fields, `spread_ratio` / `spread_ratio_third` on bucket-min rows (same min-price gate as Draft observed-flags). |

### Environment variables

| Variable | Purpose |
|----------|---------|
| `PORT` | Railway sets this; app listens on `0.0.0.0` when `PORT` is set. |
| `BOWMAN_RETAIL_API_HOST` | Optional bind host override (default `0.0.0.0` if `PORT` set). |
| `BOWMAN_RETAIL_API_PORT` | Local override if `PORT` unset (default **8766**). |
| `BOWMAN_RETAIL_CHECKLIST_CSV` | Default [`data/checklists/normalized/2025_Bowman_card_number_lookup.csv`](../data/checklists/normalized/2025_Bowman_card_number_lookup.csv). |
| `BOWMAN_RETAIL_COMBO_SORT_CSV` | Default [`data/checklists/normalized/2025_Bowman_retail_card_type_serial_combos_observed.csv`](../data/checklists/normalized/2025_Bowman_retail_card_type_serial_combos_observed.csv). |
| `BOWMAN_RETAIL_BATCH_MAX` | Max `items` length (default **200**). |

### Related code

- Retail classification (shared with CSV runner): [`cardmatch/bowman_2025_retail_steps.py`](../cardmatch/bowman_2025_retail_steps.py) (`load_retail_api_context`, `retail_steps_row_extensions`)
- Batch deals + grouping: [`cardmatch/bowman_2025_retail_batch_deals.py`](../cardmatch/bowman_2025_retail_batch_deals.py)
- Combo sort / display map: [`cardmatch/bowman_2025_retail_combo_catalog.py`](../cardmatch/bowman_2025_retail_combo_catalog.py)
