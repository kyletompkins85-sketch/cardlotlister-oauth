#!/usr/bin/env python3
"""
HTTP API: JSON body ``{"title": "..."}`` → player, card_type, predicted_price.

Requires env (or defaults relative to repo):

- ``BOWMAN_PLAYER_RANKINGS_CSV`` — ``bowman_pairwise_player_rankings_with_listings.csv``
- ``BOWMAN_CARD_TYPE_RANKINGS_CSV`` — ``bowman_pairwise_card_type_rankings_with_listings.csv``
- ``BOWMAN_AUTOGLUON_DIR`` — directory containing trained ``agModels`` (AutoGluon load path)

Optional: ``BOWMAN_CHECKLIST_CSV`` (Bowman Draft normalized checklist).

Install: ``pip install -r requirements.txt`` (repo root) or ``pip install fastapi uvicorn pydantic`` plus ``scripts/cardmatch/requirements-bowman-autogluon.txt``.

Railway: Nixpacks uses root ``requirements.txt`` and ``Procfile`` ``web`` process. ``PORT`` is set automatically; bind uses ``0.0.0.0``. If ``agModels`` is missing, the process still starts; ``GET /health`` succeeds and ``POST /predict`` / ``POST /predict/batch`` return 503 until ``BOWMAN_AUTOGLUON_DIR`` points at a valid directory.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_DEFAULT_PILOT = _ROOT / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full"


# Cmd+F: GH_ANCHOR_BOWMAN_TITLE_PRICE_API_BODY
class PredictRequest(BaseModel):
    title: str = Field(..., min_length=1, description="eBay listing title")
    price: Optional[float] = Field(default=None, description="Optional listing price (not used by rank model)")
    year: Optional[int] = Field(default=None, description="Optional product year, e.g. 2025")
    set_name: Optional[str] = Field(
        default=None,
        description="Optional product set name, e.g. Bowman Draft",
    )


class PredictBatchRequest(BaseModel):
    items: list[PredictRequest] = Field(..., min_length=1, description="Batch of listing payloads (same fields as /predict)")

    @field_validator("items")
    @classmethod
    def _max_items(cls, v: list[PredictRequest]) -> list[PredictRequest]:
        mx = int(os.environ.get("BOWMAN_PREDICT_BATCH_MAX", "200"))
        if len(v) > mx:
            raise ValueError(f"at most {mx} items (set BOWMAN_PREDICT_BATCH_MAX)")
        return v


def main() -> None:
    try:
        from fastapi import FastAPI, HTTPException
        import uvicorn
    except ImportError as e:
        raise SystemExit(
            "Install fastapi uvicorn pydantic: pip install fastapi uvicorn pydantic\n" + str(e)
        ) from e

    from cardmatch.bowman_title_price_predict import (
        BowmanTitlePricePrediction,
        predict_bowman_price_from_title,
        predict_bowman_prices_from_titles,
    )

    pl_csv = os.environ.get(
        "BOWMAN_PLAYER_RANKINGS_CSV",
        str(_DEFAULT_PILOT / "bowman_pairwise_player_rankings_with_listings.csv"),
    )
    ct_csv = os.environ.get(
        "BOWMAN_CARD_TYPE_RANKINGS_CSV",
        str(_DEFAULT_PILOT / "bowman_pairwise_card_type_rankings_with_listings.csv"),
    )
    ag_dir = os.environ.get(
        "BOWMAN_AUTOGLUON_DIR",
        str(_DEFAULT_PILOT / "bowman_rank_price_autogluon/agModels"),
    )
    checklist = os.environ.get("BOWMAN_CHECKLIST_CSV") or None

    for label, path in (
        ("BOWMAN_PLAYER_RANKINGS_CSV", pl_csv),
        ("BOWMAN_CARD_TYPE_RANKINGS_CSV", ct_csv),
    ):
        p = Path(path)
        if not p.exists():
            raise SystemExit(f"Missing {label}: {path}")

    # Cmd+F: GH_ANCHOR_BOWMAN_TITLE_PRICE_API_STARTUP_MODEL
    ag_models_available = Path(ag_dir).is_dir()

    app = FastAPI(title="Bowman title price", version="1.0.0")

    def _predict_response_body(out: BowmanTitlePricePrediction, req: PredictRequest) -> dict:
        diag: dict = {
            "title": out.title,
            "excluded": out.excluded,
            "exclude_reason": out.exclude_reason,
            "matcher_version": out.matcher_version,
            "listing_price": req.price,
            "year": req.year,
            "set_name": req.set_name,
        }
        if out.batch_item_error:
            diag["batch_item_error"] = out.batch_item_error
        return {
            "player": out.player,
            "card_type": out.card_type,
            "predicted_price": out.predicted_price,
            "confidence": {
                "player_score": out.player_score,
                "player_status": str(out.player_status),
            },
            "diagnostics": diag,
        }

    # Cmd+F: GH_ANCHOR_BOWMAN_TITLE_PRICE_API_HEALTH
    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    # Cmd+F: GH_ANCHOR_BOWMAN_TITLE_PRICE_API_PREDICT
    @app.post("/predict")
    def predict(payload: PredictRequest) -> dict:
        if not ag_models_available:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "autogluon_model_unavailable",
                    "message": "AutoGluon model directory is missing or not a directory.",
                    "path": ag_dir,
                },
            )
        try:
            out = predict_bowman_price_from_title(
                payload.title,
                player_rankings_csv=pl_csv,
                card_type_rankings_csv=ct_csv,
                autogluon_model_dir=ag_dir,
                checklist=checklist,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        return _predict_response_body(out, payload)

    # Cmd+F: GH_ANCHOR_BOWMAN_TITLE_PRICE_API_PREDICT_BATCH
    @app.post("/predict/batch")
    def predict_batch(payload: PredictBatchRequest) -> dict:
        if not ag_models_available:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "autogluon_model_unavailable",
                    "message": "AutoGluon model directory is missing or not a directory.",
                    "path": ag_dir,
                },
            )
        titles = [it.title for it in payload.items]
        try:
            outs = predict_bowman_prices_from_titles(
                titles,
                player_rankings_csv=pl_csv,
                card_type_rankings_csv=ct_csv,
                autogluon_model_dir=ag_dir,
                checklist=checklist,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        return {
            "results": [
                _predict_response_body(o, req) for o, req in zip(outs, payload.items)
            ],
        }

    # Cmd+F: GH_ANCHOR_BOWMAN_TITLE_PRICE_API_UVICORN_BIND
    # Railway sets PORT; bind 0.0.0.0 unless BOWMAN_API_HOST overrides.
    port = int(os.environ.get("BOWMAN_API_PORT") or os.environ.get("PORT", "8765"))
    host = os.environ.get("BOWMAN_API_HOST")
    if host is None:
        host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
