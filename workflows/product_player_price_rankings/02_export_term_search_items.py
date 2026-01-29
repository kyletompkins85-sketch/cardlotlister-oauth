# Cmd+F: GH_ANCHOR_PRODUCT_PLAYER_RANKINGS_STEP02_7A2C1D90
"""
Step 02 — Export *all* term_search_items for the run_ids created in Step 01.

Reads:
  workflows/product_player_price_rankings/data/<RUN_ID>/
    - product_players_search_summary_<product>.json   (auto-detected)

Calls Worker:
  GET /internal/termSearchItems/byRun?run_id=...&limit=1000&offset=...

Writes:
  workflows/product_player_price_rankings/data/<RUN_ID>/
    - term_search_items_export.csv

Env vars required:
  WORKER_BASE_URL
  INTERNAL_API_KEY
  RUN_ID
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode, urljoin

import requests


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _get_json(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    resp = requests.get(url, headers=headers, timeout=120)
    text = resp.text
    try:
        data = resp.json()
    except Exception:
        data = {"raw": text}
    if not resp.ok:
        raise RuntimeError(f"Worker GET failed {resp.status_code}: {text}")
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response type: {type(data)}")
    return data


def _find_step01_summary_json(run_dir: Path) -> Path:
    # Cmd+F: GH_ANCHOR_FIND_PRODUCT_SUMMARY_JSON_1A0B2C3D
    hits = sorted(run_dir.glob("product_players_search_summary_*.json"))
    if hits:
        return hits[0]
    fallback = run_dir / "product_players_search_summary.json"
    if fallback.exists():
        return fallback
    raise RuntimeError(f"Could not find Step 01 summary JSON in {run_dir}")


def main() -> None:
    base = _require_env("WORKER_BASE_URL")
    key = _require_env("INTERNAL_API_KEY")
    run_id = _require_env("RUN_ID")

    workflow_root = Path(__file__).resolve().parent
    run_dir = workflow_root / "data" / run_id

    summary_json = _find_step01_summary_json(run_dir)
    summary = json.loads(summary_json.read_text(encoding="utf-8"))

    run_ids: List[str] = list(summary.get("unique_term_search_run_ids") or [])
    if not run_ids:
        raise RuntimeError("No run_ids found in Step 01 summary JSON (unique_term_search_run_ids empty)")

    out_csv = run_dir / "term_search_items_export.csv"

    fieldnames = [
        "source_run_id",
        "run_id",
        "item_id",
        "legacy_item_id",
        "title",
        "price",
        "currency",
        "condition",
        "condition_id",
        "leaf_category_id",
        "item_web_url",
        "seller_username",
        "shipping_cost",
        "shipping_cost_type",
        "fetched_at",
    ]

    headers = {"x-internal-key": key}

    with out_csv.open("w", newline="", encoding="utf-8") as f_out:
        w = csv.DictWriter(f_out, fieldnames=fieldnames)
        w.writeheader()

        for rid in run_ids:
            offset = 0
            while True:
                params = {"run_id": rid, "limit": "1000", "offset": str(offset)}
                endpoint = urljoin(base.rstrip("/") + "/", "internal/termSearchItems/byRun")
                url = f"{endpoint}?{urlencode(params)}"

                data = _get_json(url, headers=headers)

                rows = data.get("rows") or []
                if not isinstance(rows, list):
                    raise RuntimeError("Unexpected rows type")

                for it in rows:
                    if not isinstance(it, dict):
                        continue
                    w.writerow({
                        "source_run_id": rid,
                        "run_id": it.get("run_id"),
                        "item_id": it.get("item_id"),
                        "legacy_item_id": it.get("legacy_item_id"),
                        "title": it.get("title"),
                        "price": it.get("price"),
                        "currency": it.get("currency"),
                        "condition": it.get("condition"),
                        "condition_id": it.get("condition_id"),
                        "leaf_category_id": it.get("leaf_category_id"),
                        "item_web_url": it.get("item_web_url"),
                        "seller_username": it.get("seller_username"),
                        "shipping_cost": it.get("shipping_cost"),
                        "shipping_cost_type": it.get("shipping_cost_type"),
                        "fetched_at": it.get("fetched_at"),
                    })

                next_offset = data.get("next_offset")
                if not next_offset:
                    break
                offset = int(next_offset)

    print(f"Used Step 01 summary JSON: {summary_json.name}")
    print(f"Exported term_search_items for {len(run_ids)} run_id(s) to: {out_csv}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
