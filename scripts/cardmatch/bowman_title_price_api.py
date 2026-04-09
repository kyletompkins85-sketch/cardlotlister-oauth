#!/usr/bin/env python3
"""
HTTP API: JSON body ``{"title": "..."}`` → player, card_type, predicted_price.

Requires env (or defaults relative to repo):

- ``BOWMAN_PLAYER_RANKINGS_CSV`` — ``bowman_pairwise_player_rankings_with_listings.csv``
- ``BOWMAN_CARD_TYPE_RANKINGS_CSV`` — ``bowman_pairwise_card_type_rankings_with_listings.csv``
- ``BOWMAN_AUTOGLUON_DIR`` — directory containing trained ``agModels`` (AutoGluon load path)

Optional: ``BOWMAN_CHECKLIST_CSV`` (Bowman Draft normalized checklist).

Install: ``pip install -r requirements.txt`` (repo root) or ``pip install fastapi uvicorn pydantic`` plus ``scripts/cardmatch/requirements-bowman-autogluon.txt``.

Railway: Nixpacks uses root ``requirements.txt`` and ``Procfile`` ``web`` process. ``PORT`` is set automatically; bind uses ``0.0.0.0``. Default ``agModels`` path is gitignored—set ``BOWMAN_AUTOGLUON_DIR`` (and CSV paths if needed) in the service variables.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

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


def main() -> None:
    try:
        from fastapi import FastAPI, HTTPException
        import uvicorn
    except ImportError as e:
        raise SystemExit(
            "Install fastapi uvicorn pydantic: pip install fastapi uvicorn pydantic\n" + str(e)
        ) from e

    from cardmatch.bowman_title_price_predict import predict_bowman_price_from_title

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
        ("BOWMAN_AUTOGLUON_DIR", ag_dir),
    ):
        p = Path(path)
        if not p.exists():
            raise SystemExit(f"Missing {label}: {path}")

    app = FastAPI(title="Bowman title price", version="1.0.0")

    # Cmd+F: GH_ANCHOR_BOWMAN_TITLE_PRICE_API_PREDICT
    @app.post("/predict")
    def predict(payload: PredictRequest) -> dict:
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
        return {
            "player": out.player,
            "card_type": out.card_type,
            "predicted_price": out.predicted_price,
            "confidence": {
                "player_score": out.player_score,
                "player_status": str(out.player_status),
            },
            "diagnostics": {
                "title": out.title,
                "excluded": out.excluded,
                "exclude_reason": out.exclude_reason,
                "matcher_version": out.matcher_version,
                "listing_price": payload.price,
                "year": payload.year,
                "set_name": payload.set_name,
            },
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
