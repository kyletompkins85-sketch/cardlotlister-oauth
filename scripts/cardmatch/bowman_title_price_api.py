#!/usr/bin/env python3
"""
HTTP API: JSON body ``{"title": "..."}`` → player, card_type, predicted_price.

Requires env (or defaults relative to repo):

- ``BOWMAN_PLAYER_RANKINGS_CSV`` — ``bowman_pairwise_player_rankings_with_listings.csv``
- ``BOWMAN_CARD_TYPE_RANKINGS_CSV`` — ``bowman_pairwise_card_type_rankings_with_listings.csv``
- ``BOWMAN_AUTOGLUON_DIR`` — directory containing trained ``agModels`` (AutoGluon load path)

Optional: ``BOWMAN_CHECKLIST_CSV`` (Bowman Draft normalized checklist).

Install: ``pip install fastapi uvicorn`` plus ``scripts/cardmatch/requirements-bowman-autogluon.txt``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_DEFAULT_PILOT = _ROOT / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full"


def main() -> None:
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, Field
        import uvicorn
    except ImportError as e:
        raise SystemExit(
            "Install fastapi uvicorn pydantic: pip install fastapi uvicorn\n" + str(e)
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

    class Body(BaseModel):
        title: str = Field(..., min_length=1, description="eBay listing title")

    app = FastAPI(title="Bowman title price", version="1.0.0")

    @app.post("/predict")
    def predict(body: Body) -> dict:
        try:
            out = predict_bowman_price_from_title(
                body.title,
                player_rankings_csv=pl_csv,
                card_type_rankings_csv=ct_csv,
                autogluon_model_dir=ag_dir,
                checklist=checklist,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        return {
            "title": out.title,
            "player": out.player,
            "card_type": out.card_type,
            "predicted_price": out.predicted_price,
            "excluded": out.excluded,
            "exclude_reason": out.exclude_reason,
            "player_status": str(out.player_status),
            "player_score": out.player_score,
            "matcher_version": out.matcher_version,
        }

    host = os.environ.get("BOWMAN_API_HOST", "127.0.0.1")
    port = int(os.environ.get("BOWMAN_API_PORT", "8765"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
