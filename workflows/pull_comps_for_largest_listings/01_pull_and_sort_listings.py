# workflows/pull_comps_for_largest_listings/01_pull_and_sort_listings.py
"""
Step 01 — Pull listings from your Worker endpoint (/internal/listings/search),
sort largest->smallest by all-in price (price + shipping_cost),
and write BOTH JSON + CSV into:

  workflows/pull_comps_for_largest_listings/data/<run_id>/

Env vars:
  WORKER_BASE_URL    e.g. https://...workers.dev
  INTERNAL_API_KEY   secret key for x-internal-key
  QUERY              optional; default "2025 Topps Update"
  LIMIT              optional; default 1000
  RUN_ID             optional; default utc timestamp like 20260126_193012Z
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode, urljoin

import requests


@dataclass
class Config:
    base_url: str
    api_key: str
    query: str
    limit: int
    run_id: str


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _safe_slug(s: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (s or "all").lower())
    slug = re.sub(r"^_+|_+$", "", slug)
    return slug or "all"


def _to_number(x: Any) -> float:
    """Convert numbers / numeric strings / '$12.34' to float."""
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return 0.0
        s = s.replace(",", "")
        s = re.sub(r"[^0-9.\-]", "", s)
        try:
            return float(s)
        except ValueError:
            return 0.0
    return 0.0


def fetch_page(cfg: Config, offset: int) -> Dict[str, Any]:
    params = {"limit": str(cfg.limit), "offset": str(offset)}
    if cfg.query and cfg.query.strip():
        params["q"] = cfg.query.strip()

    url = urljoin(cfg.base_url.rstrip("/") + "/", "internal/listings/search")
    url = f"{url}?{urlencode(params)}"

    resp = requests.get(url, headers={"x-internal-key": cfg.api_key}, timeout=60)

    text = resp.text
    try:
        data = resp.json()
    except Exception:
        data = {"raw": text}

    if not resp.ok:
        raise RuntimeError(f"Worker request failed {resp.status_code}: {text}")

    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response type: {type(data)}")

    return data


def compute_all_in(row: Dict[str, Any]) -> float:
    return _to_number(row.get("price")) + _to_number(row.get("shipping_cost"))


def _collect_all_keys(rows: List[Dict[str, Any]]) -> List[str]:
    keys = set()
    for r in rows:
        keys.update(r.keys())
    # Put common fields first if they exist
    preferred = [
        "item_id",
        "title",
        "price",
        "shipping_cost",
        "all_in",
        "shipping_cost_type",
        "item_web_url",
        "condition",
        "category_id",
        "listing_type",
    ]
    ordered = [k for k in preferred if k in keys]
    remaining = sorted([k for k in keys if k not in ordered])
    return ordered + remaining


def main() -> None:
    base = _require_env("WORKER_BASE_URL")
    key = _require_env("INTERNAL_API_KEY")
    query = os.getenv("QUERY", "2025 Topps Update")
    limit = int(os.getenv("LIMIT", "1000"))

    default_run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    run_id = (os.getenv("RUN_ID") or default_run_id).strip()

    cfg = Config(base_url=base, api_key=key, query=query, limit=limit, run_id=run_id)

    offset = 0
    rows: List[Dict[str, Any]] = []

    while True:
        page = fetch_page(cfg, offset)
        page_rows = page.get("rows") or []
        if not isinstance(page_rows, list):
            raise RuntimeError("Response 'rows' was not a list")

        for r in page_rows:
            if isinstance(r, dict):
                rows.append(r)

        next_offset = page.get("next_offset")
        if not next_offset:
            break
        offset = int(next_offset)

    # compute + sort descending
    for r in rows:
        r["all_in"] = compute_all_in(r)

    rows_sorted = sorted(rows, key=lambda r: _to_number(r.get("all_in")), reverse=True)

    workflow_root = Path(__file__).resolve().parent  # .../workflows/pull_comps_for_largest_listings
    out_dir = workflow_root / "data" / cfg.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_q = _safe_slug(query)

    # Write JSON
    json_path = out_dir / f"listings_{safe_q}_sorted.json"
    payload = {
        "run_id": cfg.run_id,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "count": len(rows_sorted),
        "rows": rows_sorted,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Write CSV (all rows, all columns discovered)
    csv_path = out_dir / f"listings_{safe_q}_sorted.csv"
    fieldnames = _collect_all_keys(rows_sorted)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows_sorted:
            w.writerow(r)

    print(f"Wrote {len(rows_sorted)} rows")
    print(f"- JSON: {json_path}")
    print(f"- CSV:  {csv_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
