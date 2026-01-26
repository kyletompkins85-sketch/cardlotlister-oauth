# workflows/pull_comps_for_largest_listings/04_build_listing_vs_comps_report.py
"""
Step 04 — Build a report that joins YOUR listings (Step 01) to eBay comps (Step 03).

Inputs (under workflows/pull_comps_for_largest_listings/data/<RUN_ID>/):
  - term_search_calls_summary.csv           (from Step 02)
  - term_search_items_export.csv            (from Step 03)
  - listings_sorted_top.csv  (or similar)   (from Step 01)  <-- we auto-detect

Output:
  - report_listing_vs_comps.csv
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _find_step01_listings_csv(run_dir: Path) -> Path:
    """
    Auto-detect the Step 01 'sorted listings' CSV.
    We look for any CSV in run_dir with 'listings' and 'sorted' in the filename.
    """
    candidates = sorted(run_dir.glob("*.csv"))
    hits = []
    for p in candidates:
        n = p.name.lower()
        if "listings" in n and "sorted" in n:
            hits.append(p)
    if hits:
        return hits[0]
    raise RuntimeError(
        f"Could not find Step 01 listings CSV in {run_dir}. "
        f"Expected a file name containing 'listings' and 'sorted'."
    )


def _read_csv_as_dicts(path: Path) -> List[Dict[str, Any]]:
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


def main() -> None:
    run_id = _require_env("RUN_ID")

    workflow_root = Path(__file__).resolve().parent
    run_dir = workflow_root / "data" / run_id

    if not run_dir.exists():
        raise RuntimeError(f"Run folder not found: {run_dir}")

    # Step 02 summary: has run_id per search
    calls_csv = run_dir / "term_search_calls_summary.csv"
    if not calls_csv.exists():
        raise RuntimeError(f"Missing Step 02 file: {calls_csv}")

    # Step 03 export: all comps
    comps_csv = run_dir / "term_search_items_export.csv"
    if not comps_csv.exists():
        raise RuntimeError(f"Missing Step 03 file: {comps_csv}")

    # Step 01 listings: auto-detect
    listings_csv = _find_step01_listings_csv(run_dir)

    calls = _read_csv_as_dicts(calls_csv)
    comps = _read_csv_as_dicts(comps_csv)
    listings = _read_csv_as_dicts(listings_csv)

    # Sort dad listings: most expensive -> cheapest (blank/invalid prices go last)
    listings = sorted(
        listings,
        key=lambda r: (_to_float(r.get("price")) is None, _to_float(r.get("price")) or 0.0, (r.get("title") or "").strip()),
        reverse=True
    )


      # Build: listing_title -> run_id
    # Step 02 uses listing title as the search query
    title_to_run_id: Dict[str, str] = {}

    for row in calls:
        ok = (row.get("ok") or "").strip().lower()
        if ok not in ("true", "1", "yes"):
            continue

        query = (row.get("query") or "").strip()
        rid = (row.get("run_id") or "").strip()

        if query and rid:
            title_to_run_id[query] = rid

    if not title_to_run_id:
        raise RuntimeError(
            "No (title -> run_id) mappings found in term_search_calls_summary.csv. "
            "Expected columns: query, run_id, ok."
        )

    # Build: run_id -> list of comps
    run_to_comps: Dict[str, List[Dict[str, Any]]] = {}
    for c in comps:
        rid = str(c.get("source_run_id") or c.get("run_id") or "").strip()
        if not rid:
            continue
        run_to_comps.setdefault(rid, []).append(c)

    # Output report
    out_csv = run_dir / "report_listing_vs_comps.csv"

    fieldnames = [
        "my_title",
        "my_price",
        "comp_title",
        "comp_price",
        "comp_seller_username",
        "comp_item_web_url",
    ]

    with out_csv.open("w", newline="", encoding="utf-8") as f_out:
        w = csv.DictWriter(f_out, fieldnames=fieldnames)
        w.writeheader()

        # listings CSV should include at least 'title' and 'price'.
        # We also try to pick up 'ebay_listing_id' if present.
        for i, l in enumerate(listings):
            # Step 01 should have listing_idx; if not, fall back to row index

            my_title = (l.get("title") or "").strip()
            my_price = _to_float(l.get("price"))
            my_ebay_id = (l.get("ebay_listing_id") or "").strip()
    
            # Join on title == query
            rid = title_to_run_id.get(my_title)
            if not rid:
                continue

            comp_rows = run_to_comps.get(rid, [])
            # Sort comps: cheapest -> most expensive (blank/invalid prices go last)
            comp_rows = sorted(
                comp_rows,
                key=lambda r: (_to_float(r.get("price")) is None, _to_float(r.get("price")) if _to_float(r.get("price")) is not None else 1e18, (r.get("title") or "").strip())
            )

            for c in comp_rows:
                w.writerow({
                    "my_title": my_title or None,
                    "my_price": my_price,
                    "comp_title": (c.get("title") or "").strip() or None,
                    "comp_price": _to_float(c.get("price")),
                    "comp_seller_username": (c.get("seller_username") or "").strip() or None,
                    "comp_item_web_url": (c.get("item_web_url") or "").strip() or None,
                })


    print(f"Wrote report CSV: {out_csv}")
    print(f"Used Step 01 listings CSV: {listings_csv.name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
