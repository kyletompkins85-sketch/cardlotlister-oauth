# workflows/pull_comps_for_largest_listings/03_export_term_search_items_by_run.py
"""
Step 03 — Export *all* term_search_items for the run_ids created in Step 02.

Reads:
  workflows/pull_comps_for_largest_listings/data/<RUN_ID>/term_search_calls_summary.csv

Calls Worker:
  GET /internal/termSearchItems/byRun?run_id=...&limit=1000&offset=...

Writes:
  workflows/pull_comps_for_largest_listings/data/<RUN_ID>/term_search_items_export.csv

Env vars required:
  WORKER_BASE_URL
  INTERNAL_API_KEY
  RUN_ID
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlencode

import requests


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _get_json(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    resp = requests.get(url, headers=headers, timeout=90)
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


def main() -> None:
    base = _require_env("WORKER_BASE_URL")
    key = _require_env("INTERNAL_API_KEY")
    run_id = _require_env("RUN_ID")

    workflow_root = Path(__file__).resolve().parent
    run_dir = workflow_root / "data" / run_id
    summary_csv = run_dir / "term_search_calls_summary.csv"

    if not summary_csv.exists():
        raise RuntimeError(f"Missing Step 02 summary file: {summary_csv}")

    # Collect run_ids from Step 02 summary
    run_ids: List[str] = []
    with summary_csv.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rid = (row.get("run_id") or "").strip()
            ok = (row.get("ok") or "").strip().lower()
            if rid and ok in ("true", "1", "yes"):
                run_ids.append(rid)

    if not run_ids:
        raise RuntimeError("No run_id values found in term_search_calls_summary.csv (or all ok=false)")

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

    print(f"Exported term_search_items for {len(run_ids)} run_id(s) to: {out_csv}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
