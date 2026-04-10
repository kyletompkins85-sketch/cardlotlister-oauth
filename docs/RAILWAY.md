<!-- Cmd+F: GH_ANCHOR_DOCS_RAILWAY -->

# Bowman FastAPI on Railway

Deploys the **`web`** process from the repo root [`Procfile`](../Procfile): `python scripts/cardmatch/bowman_title_price_api.py`.

## Endpoints

| Method | Path | Notes |
|--------|------|--------|
| GET | `/health` | No model required; returns `{"status":"ok"}`. |
| POST | `/predict` | JSON body: `title` (required), optional `price`, `year`, `set_name`. Needs AutoGluon model dir on disk or 503. |
| POST | `/predict/batch` | JSON body: `items` — array of the same objects as `/predict` (min 1). Max length defaults to 200 (`BOWMAN_PREDICT_BATCH_MAX`). Response: `{"results":[...]}` with the same shape as `/predict` per element. 422 if over max. |

## Environment variables

| Variable | Purpose |
|----------|---------|
| `PORT` | Set by Railway; app listens on `0.0.0.0`. |
| `BOWMAN_AUTOGLUON_DIR` | Path to trained **`agModels`** directory (AutoGluon `TabularPredictor.load`). Default under `data/cardmatch_pilot/.../bowman_rank_price_autogluon/agModels`. |
| `BOWMAN_PLAYER_RANKINGS_CSV` | Optional override for pairwise player ranks CSV. |
| `BOWMAN_CARD_TYPE_RANKINGS_CSV` | Optional override for pairwise card-type ranks CSV. |
| `BOWMAN_CHECKLIST_CSV` | Optional Bowman checklist CSV for `classify_listing` / matcher. |
| `BOWMAN_PREDICT_BATCH_MAX` | Max length of `items` for `POST /predict/batch` (default **200**). |

**Startup:** If the two default pairwise CSVs are missing, the process exits (configure paths or commit [`data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/`](../data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/) files). If **`agModels`** is missing, the server still starts; **`POST /predict`** and **`POST /predict/batch`** return **503** with `autogluon_model_unavailable` until the model exists.

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
