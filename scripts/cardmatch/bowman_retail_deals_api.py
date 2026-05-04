#!/usr/bin/env python3
"""
HTTP API: 2025 Bowman **retail** listings → cohort grouping, combo ``sort_order``, and spread vs
2nd/3rd cheapest within each (player, card_type, serial) bucket.

No AutoGluon or pairwise rank CSVs. Mirrors :file:`bowman_title_price_api.py` shape: ``GET /health``,
batch POST with env ``PORT`` / ``BOWMAN_RETAIL_API_HOST``.

Env:

- ``BOWMAN_RETAIL_CHECKLIST_CSV`` — default ``data/checklists/normalized/2025_Bowman_card_number_lookup.csv``
- ``BOWMAN_RETAIL_COMBO_SORT_CSV`` — default ``data/checklists/normalized/2025_Bowman_retail_card_type_serial_combos_observed.csv``
- ``BOWMAN_RETAIL_BATCH_MAX`` — max ``items`` length (default **200**)
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

_DEFAULT_CHECKLIST = _ROOT / "data/checklists/normalized/2025_Bowman_card_number_lookup.csv"
_DEFAULT_COMBO = _ROOT / "data/checklists/normalized/2025_Bowman_retail_card_type_serial_combos_observed.csv"


class RetailDealItemRequest(BaseModel):
    title: str = Field(..., min_length=1, description="eBay listing title")
    price: float = Field(..., description="Observed listing price (required for spread stats)")
    id: Optional[str] = Field(default=None, description="Optional client id echoed in the response")
    player_key: Optional[str] = Field(
        default=None,
        description="Optional explicit player grouping key for cohort splits",
    )


class RetailDealsBatchRequest(BaseModel):
    items: list[RetailDealItemRequest] = Field(
        ..., min_length=1, description="Batch of listings (same player or mixed with player_key)"
    )

    @field_validator("items")
    @classmethod
    def _max_items(cls, v: list[RetailDealItemRequest]) -> list[RetailDealItemRequest]:
        mx = int(os.environ.get("BOWMAN_RETAIL_BATCH_MAX", "200"))
        if len(v) > mx:
            raise ValueError(f"at most {mx} items (set BOWMAN_RETAIL_BATCH_MAX)")
        return v


def main() -> None:
    try:
        from fastapi import FastAPI, HTTPException
        import uvicorn
    except ImportError as e:
        raise SystemExit(
            "Install fastapi uvicorn pydantic: pip install fastapi uvicorn pydantic\n" + str(e)
        ) from e

    from cardmatch.bowman_2025_retail_combo_catalog import load_combo_sort_index
    from cardmatch.bowman_2025_retail_batch_deals import RetailBatchInputItem, analyze_retail_batch_deals
    from cardmatch.bowman_2025_retail_steps import load_retail_api_context

    checklist = Path(
        os.environ.get("BOWMAN_RETAIL_CHECKLIST_CSV", str(_DEFAULT_CHECKLIST))
    ).resolve()
    combo_csv = Path(
        os.environ.get("BOWMAN_RETAIL_COMBO_SORT_CSV", str(_DEFAULT_COMBO))
    ).resolve()

    if not checklist.is_file():
        raise SystemExit(f"Missing checklist: {checklist}")
    if not combo_csv.is_file():
        raise SystemExit(f"Missing combo sort CSV: {combo_csv}")

    ctx = load_retail_api_context(checklist)
    combo_index = load_combo_sort_index(combo_csv)

    app = FastAPI(title="Bowman retail deals", version="0.1.0")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/batch/deals")
    def batch_deals(payload: RetailDealsBatchRequest) -> dict:
        items = [
            RetailBatchInputItem(
                title=it.title,
                price=float(it.price),
                id=it.id,
                player_key=it.player_key,
            )
            for it in payload.items
        ]
        try:
            results, groups = analyze_retail_batch_deals(items, ctx, combo_index)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        return {"results": results, "groups": groups}

    port = int(os.environ.get("BOWMAN_RETAIL_API_PORT") or os.environ.get("PORT", "8766"))
    host = os.environ.get("BOWMAN_RETAIL_API_HOST")
    if host is None:
        host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
