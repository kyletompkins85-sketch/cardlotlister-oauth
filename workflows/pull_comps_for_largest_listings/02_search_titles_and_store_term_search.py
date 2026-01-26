# workflows/pull_comps_for_largest_listings/02_search_titles_and_store_term_search.py
"""
Step 02 — For each listing row produced by Step 01, take the listing title and:
  - call Worker POST /comps/searchTerm
  - request top 200 results (limit=200, offset=0)
  - let the Worker store results into Supabase:
      term_search_runs + term_search_items

Outputs written to:
  workflows/pull_comps_for_largest_listings/data/<RUN_ID>/
    - term_search_calls_summary.csv
    - term_search_calls_summary.json

Env vars required:
  WORKER_BASE_URL
  INTERNAL_API_KEY
  RUN_ID  (must match Step 01)
Optional:
  EBAY_LIMIT  (default 200)
  EBAY_OFFSET (default 0)
  SLEEP_MS    (default 250)
"""

from __future__ import annotations

import csv
import glob
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _int_env(name: str, default: int) -> int:
    v = (os.getenv(name) or "").strip()
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        return default


def _find_step01_sorted_json(run_dir: Path) -> Path:
    # Step 01 writes: listings_<something>_sorted.json
    matches = sorted(run_dir.glob("listings_*_sorted.json"))
    if not matches:
        raise RuntimeError(f"No Step 01 sorted JSON found in: {run_dir}")
    if len(matches) > 1:
        # pick the newest by mtime
        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def _post_with_retry(url: str, headers: Dict[str, str], payload: Dict[str, Any], max_tries: int = 5) -> Dict[str, Any]:
    last_err: Optional[str] = None
    for attempt in range(1, max_tries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=90)
            text = resp.text
            try:
                data = resp.json()
            except Exception:
                data = {"raw": text}

            if resp.status_code in (429, 500, 502, 503, 504):
                last_err = f"retryable_status={resp.status_code} body={text[:300]}"
                # backoff
                time.sleep(min(2 ** attempt, 10))
                continue

            if not resp.ok:
                raise RuntimeError(f"Worker POST failed {resp.status_code}: {text}")

            if not isinstance(data, dict):
                raise RuntimeError(f"Unexpected JSON type: {type(data)}")

            return data

        except Exception as e:
            last_err = str(e)
            time.sleep(min(2 ** attempt, 10))

    raise RuntimeError(f"POST failed after retries: {last_err}")


def main() -> None:
    base = _require_env("WORKER_BASE_URL")
    key = _require_env("INTERNAL_API_KEY")
    run_id = _require_env("RUN_ID")

    ebay_limit = max(1, min(200, _int_env("EBAY_LIMIT", 200)))  # your Worker caps at 200 already
    ebay_offset = max(0, _int_env("EBAY_OFFSET", 0))
    sleep_ms = max(0, _int_env("SLEEP_MS", 250))

    workflow_root = Path(__file__).resolve().parent  # .../workflows/pull_comps_for_largest_listings
    run_dir = workflow_root / "data" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    step01_json_path = _find_step01_sorted_json(run_dir)
    step01 = json.loads(step01_json_path.read_text(encoding="utf-8"))

    rows = step01.get("rows") or []
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("Step 01 JSON had no rows")

    endpoint = urljoin(base.rstrip("/") + "/", "comps/searchTerm")
    headers = {"x-internal-key": key, "Content-Type": "application/json"}

    summaries: List[Dict[str, Any]] = []

    for idx, r in enumerate(rows, start=1):
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or "").strip()
        ebay_listing_id = (r.get("ebay_listing_id") or "").strip()

        if not title:
            summaries.append({
                "idx": idx,
                "ebay_listing_id": ebay_listing_id or None,
                "query": None,
                "ok": False,
                "error": "missing_title",
            })
            continue

        payload = {
            "query": title,
            "limit": ebay_limit,
            "offset": ebay_offset,
        }

        data = _post_with_retry(endpoint, headers, payload)

        summaries.append({
            "idx": idx,
            "ebay_listing_id": ebay_listing_id or None,
            "query": title,
            "ok": bool(data.get("ok")),
            "run_id": data.get("run_id"),
            "returned": data.get("returned"),
            "inserted_items": data.get("inserted_items"),
            "total": data.get("total"),
        })

        if sleep_ms:
            time.sleep(sleep_ms / 1000.0)

    # Write summary outputs
    out_csv = run_dir / "term_search_calls_summary.csv"
    out_json = run_dir / "term_search_calls_summary.json"

    out_json.write_text(json.dumps({
        "run_id": run_id,
        "count": len(summaries),
        "summaries": summaries
    }, indent=2), encoding="utf-8")

    fieldnames = ["idx", "ebay_listing_id", "query", "ok", "run_id", "returned", "inserted_items", "total"]
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for s in summaries:
            w.writerow({k: s.get(k) for k in fieldnames})

    print(f"Loaded Step 01 file: {step01_json_path}")
    print(f"Called /comps/searchTerm for {len(summaries)} listings")
    print(f"Wrote summary CSV: {out_csv}")
    print(f"Wrote summary JSON: {out_json}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
