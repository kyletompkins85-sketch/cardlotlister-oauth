# workflows/pull_comps_for_largest_listings/02_search_titles_and_store_term_search.py

from __future__ import annotations

import csv
import json
import os
import sys
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _env_bool(name: str, default: bool = False) -> bool:
    v = (os.getenv(name) or "").strip().lower()
    if not v:
        return default
    return v in ("1", "true", "yes", "y", "on")

def _should_skip_title(title: str) -> Optional[str]:
    t = (title or "").strip()
    if not t:
        return None

    # skip anything that looks like a "lot"
    # matches: "lot", "lot..", "lot,", "player lot", "card lot", etc.
    if re.search(r"\blot\b", t, flags=re.IGNORECASE):
        return "excluded_contains_lot"

    return None

def _find_step01_listings_csv(run_dir: Path) -> Path:
    # Prefer your known file name if present
    preferred = run_dir / "listings_all_sorted_top.csv"
    if preferred.exists():
        return preferred

    # Otherwise auto-detect: any csv containing 'listings' and 'sorted'
    candidates = sorted(run_dir.glob("*.csv"))
    for p in candidates:
        n = p.name.lower()
        if "listings" in n and "sorted" in n:
            return p
    raise RuntimeError(
        f"Could not find Step 01 listings CSV in {run_dir}. "
        f"Expected listings_all_sorted_top.csv or a filename containing 'listings' and 'sorted'."
    )


def _read_csv_as_dicts(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _worker_get_json(url: str, key: str, params: Dict[str, str]) -> Dict[str, Any]:
    resp = requests.get(url, headers={"x-internal-key": key}, params=params, timeout=60)
    text = resp.text
    try:
        data = resp.json()
    except Exception:
        data = {"raw": text}

    if not resp.ok:
        raise RuntimeError(f"Worker GET failed {resp.status_code}: {text}")
    return data


def _worker_post_json(url: str, key: str, body: Dict[str, Any]) -> Dict[str, Any]:
    max_retries_429 = int(os.getenv("MAX_RETRIES_429", "3"))
    backoffs_s = [2, 5, 10]  # retry delays for 429s

    attempt = 0
    while True:
        resp = requests.post(
            url,
            headers={"x-internal-key": key, "Content-Type": "application/json"},
            data=json.dumps(body),
            timeout=120,
        )

        text = resp.text
        try:
            data = resp.json()
        except Exception:
            data = {"raw": text}

        # If rate-limited, back off and retry a few times
        if resp.status_code == 429 and attempt < max_retries_429:
            wait_s = backoffs_s[min(attempt, len(backoffs_s) - 1)]
            time.sleep(wait_s)
            attempt += 1
            continue

        if not resp.ok:
            raise RuntimeError(f"Worker POST failed {resp.status_code}: {text}")
        return data

def main() -> None:
    base = _require_env("WORKER_BASE_URL").rstrip("/")
    key = _require_env("INTERNAL_API_KEY").strip()
    run_id = _require_env("RUN_ID")
    force_refresh = _env_bool("FORCE_REFRESH", default=False)
    pause_ms = int(os.getenv("EBAY_PAUSE_MS", "250"))  # pause after each cache-miss POST

    workflow_root = Path(__file__).resolve().parent
    run_dir = workflow_root / "data" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    listings_csv = _find_step01_listings_csv(run_dir)
    listings = _read_csv_as_dicts(listings_csv)

    # Output: summary of what we did (cache hit vs called eBay)
    out_summary = run_dir / "term_search_calls_summary.csv"

    # Endpoints
    lookup_url = f"{base}/internal/termSearchRuns/lookupToday"
    search_url = f"{base}/comps/searchTerm"

    fieldnames = [
    "ok",
    "cache_hit",
    "skipped",
    "skip_reason",
    "query",
    "run_id",
    "returned",
    "inserted_items",
    "total",
    "error",
    ]

    rows_out: List[Dict[str, Any]] = []

    for l in listings:
        query = (l.get("title") or "").strip()

        if not query:
            rows_out.append({
                "ok": "false",
                "cache_hit": "",
                "skipped": "false",
                "skip_reason": "",
                "query": "",
                "run_id": "",
                "returned": "",
                "inserted_items": "",
                "total": "",
                "error": "missing_title_in_listings_csv",
            })
            continue

        skip_reason = _should_skip_title(query)
        if skip_reason:
            rows_out.append({
                "ok": "true",
                "cache_hit": "",
                "skipped": "true",
                "skip_reason": skip_reason,
                "query": query,
                "run_id": "",
                "returned": "",
                "inserted_items": "",
                "total": "",
                "error": "",
            })
            continue

        try:
            # 1) lookup cache (unless force_refresh)
            existing_run_id: Optional[str] = None
            if not force_refresh:
                lookup = _worker_get_json(lookup_url, key, {"q": query})
                existing_run_id = lookup.get("run_id") or None

            if existing_run_id:
                # cache hit: DO NOT call eBay
                rows_out.append({
                    "ok": "true",
                    "cache_hit": "true",
                    "skipped": "false",
                    "skip_reason": "",
                    "query": query,
                    "run_id": existing_run_id,
                    "returned": "",
                    "inserted_items": "",
                    "total": "",
                    "error": "",
                })
                continue

            # 2) cache miss: call eBay through worker, which inserts into Supabase
            resp = _worker_post_json(search_url, key, {
                "query": query,
                "limit": 200,
                "offset": 0
            })
            time.sleep(pause_ms / 1000.0)

            if not resp.get("ok"):
                rows_out.append({
                    "ok": "false",
                    "cache_hit": "false",
                    "skipped": "false",
                    "skip_reason": "",
                    "query": query,
                    "run_id": "",
                    "returned": "",
                    "inserted_items": "",
                    "total": "",
                    "error": str(resp.get("error") or "unknown_worker_error"),
                })
                continue

            rows_out.append({
                "ok": "true",
                "cache_hit": "false",
                "skipped": "false",
                "skip_reason": "",
                "query": query,
                "run_id": str(resp.get("run_id") or ""),
                "returned": str(resp.get("returned") or ""),
                "inserted_items": str(resp.get("inserted_items") or ""),
                "total": str(resp.get("total") or ""),
                "error": "",
            })

        except Exception as e:
            rows_out.append({
                "ok": "false",
                "cache_hit": "",
                "skipped": "false",
                "skip_reason": "",
                "query": query,
                "run_id": "",
                "returned": "",
                "inserted_items": "",
                "total": "",
                "error": str(e),
            })

    with out_summary.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)

    print(f"Wrote Step 02 summary: {out_summary}")
    print(f"Force refresh: {force_refresh}")
    print(f"Used listings CSV: {listings_csv.name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
