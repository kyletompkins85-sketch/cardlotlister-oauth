# Cmd+F: GH_ANCHOR_PRODUCT_PLAYER_RANKINGS_STEP03_PLACEHOLDER_51D0A7C2
"""
Step 03 — PRODUCT player price rankings (placeholder).

Current placeholder methodology:
- group comps by term_search run_id (which maps to: prefix + playerName query)
- compute median comp price (ignores missing prices)
- rank highest median -> lowest

We will replace this methodology when you provide the real one.

Inputs (under workflows/product_player_price_rankings/data/<RUN_ID>/):
  - product_players_search_summary_*.csv
  - term_search_items_export.csv

Output:
  - report_product_player_price_rankings_placeholder.csv
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _median(nums: List[float]) -> Optional[float]:
    if not nums:
        return None
    xs = sorted(nums)
    n = len(xs)
    mid = n // 2
    if n % 2 == 1:
        return xs[mid]
    return (xs[mid - 1] + xs[mid]) / 2.0


def _find_step01_summary_csv(run_dir: Path) -> Path:
    # Cmd+F: GH_ANCHOR_FIND_PRODUCT_SUMMARY_CSV_9F1C0D2A
    hits = sorted(run_dir.glob("product_players_search_summary_*.csv"))
    if hits:
        return hits[0]
    fallback = run_dir / "product_players_search_summary.csv"
    if fallback.exists():
        return fallback
    raise RuntimeError(f"Could not find Step 01 summary CSV in {run_dir}")


def main() -> None:
    run_id = _require_env("RUN_ID")

    workflow_root = Path(__file__).resolve().parent
    run_dir = workflow_root / "data" / run_id

    summary_csv = _find_step01_summary_csv(run_dir)
    export_csv = run_dir / "term_search_items_export.csv"

    if not export_csv.exists():
        raise RuntimeError(f"Missing Step 02 export CSV: {export_csv}")

    searches = _read_csv(summary_csv)
    comps = _read_csv(export_csv)

    run_to_player: Dict[str, Dict[str, Any]] = {}
    for s in searches:
        rid = (s.get("run_id") or "").strip()
        if rid:
            run_to_player[rid] = s

    run_to_prices: Dict[str, List[float]] = {}
    for c in comps:
        rid = (c.get("source_run_id") or c.get("run_id") or "").strip()
        if not rid:
            continue
        p = _to_float(c.get("price"))
        if p is None:
            continue
        run_to_prices.setdefault(rid, []).append(p)

    ranked: List[Dict[str, Any]] = []
    for rid, player_row in run_to_player.items():
        prices = run_to_prices.get(rid, [])
        med = _median(prices)
        ranked.append({
            "playerName": (player_row.get("playerName") or "").strip() or None,
            "cardNumber": (player_row.get("cardNumber") or "").strip() or None,
            "team": (player_row.get("team") or "").strip() or None,
            "query": (player_row.get("query") or "").strip() or None,
            "run_id": rid,
            "comps_with_price_count": len(prices),
            "median_comp_price_placeholder": med,
        })

    ranked = sorted(
        ranked,
        key=lambda r: (r["median_comp_price_placeholder"] is None, -(r["median_comp_price_placeholder"] or 0.0))
    )

    out_csv = run_dir / "report_product_player_price_rankings_placeholder.csv"
    fieldnames = [
        "playerName",
        "cardNumber",
        "team",
        "query",
        "run_id",
        "comps_with_price_count",
        "median_comp_price_placeholder",
    ]

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in ranked:
            w.writerow(r)

    print(f"Used Step 01 summary CSV: {summary_csv.name}")
    print(f"Wrote placeholder rankings report: {out_csv}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
