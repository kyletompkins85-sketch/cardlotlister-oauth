#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_CT_COUNTS_FROM_TERM_SEARCH_EXPORT_4B7D1C90
"""
Counts CT_* hits by applying your topps_listing_classifier to titles pulled from Supabase
through your Cloudflare Worker (NO eBay calls).

Calls Worker:
  GET /internal/termSearchItems/search?q=...&limit=1000&offset=...

Env vars:
  WORKER_BASE_URL
  INTERNAL_API_KEY
  RUN_ID (optional; used only for output folder naming)

Usage (recommended in GH Actions):
  python workflows/product_player_price_rankings/90_ct_counts_from_term_search_export.py --q "2025 Bowman Draft"
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin

import requests
import importlib.util


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "y", "t", "on")
    return bool(v)


def _load_topps_classifier() -> Any:
    """
    Robust loader: finds topps_listing_classifier.py anywhere in the repo and loads it.
    Avoids brittle PYTHONPATH issues in GitHub Actions.
    """
    # Cmd+F: GH_ANCHOR_DYNAMIC_LOAD_TOPPS_CLASSIFIER_7C2A1D11
    here = Path(__file__).resolve()
    repo_root = here.parents[3] if len(here.parents) >= 4 else here.parents[-1]

    candidates = list(repo_root.rglob("topps_listing_classifier.py"))
    if not candidates:
        raise RuntimeError(
            "Could not find topps_listing_classifier.py anywhere in the repo. "
            "Add it to the repo (any folder) and re-run."
        )

    # Prefer one inside workflows/ if there are multiple
    candidates.sort(key=lambda p: (0 if "workflows" in str(p).lower() else 1, len(str(p))))
    path = candidates[0]

    spec = importlib.util.spec_from_file_location("topps_listing_classifier", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to create import spec for {path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    if not hasattr(mod, "classify_title"):
        raise RuntimeError(f"{path} loaded but has no classify_title()")
    return mod


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _worker_get_json(url: str, key: str) -> Dict[str, Any]:
    resp = requests.get(url, headers={"x-internal-key": key}, timeout=90)
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
    # Cmd+F: GH_ANCHOR_CT_COUNTS_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", default="", help="Search string for /internal/termSearchItems/search?q= (default: env PREFIX or PRODUCT_NAME)")
    ap.add_argument("--max-rows", type=int, default=0, help="If >0, stop after classifying this many rows total")
    ap.add_argument("--title-col", default="title", help="Title column key from Worker rows (default: title)")
    ap.add_argument("--out", default="", help="Optional output CSV path override")
    args = ap.parse_args()

    base = _require_env("WORKER_BASE_URL")
    key = _require_env("INTERNAL_API_KEY")
    run_id = (os.getenv("RUN_ID") or "run").strip()

    q = (args.q or os.getenv("PREFIX") or os.getenv("PRODUCT_NAME") or "").strip()
    if not q:
        raise SystemExit("Missing --q (and env PREFIX/PRODUCT_NAME not set)")

    # load classifier
    mod = _load_topps_classifier()
    classify_title = getattr(mod, "classify_title")

    # discover CT_* keys
    tmpl: Dict[str, object] = classify_title("")
    ct_keys: List[str] = sorted([k for k, v in tmpl.items() if k.startswith("CT_") and isinstance(v, bool)])

    # output path
    if args.out.strip():
        out_path = Path(args.out.strip())
        out_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_path = Path(__file__).resolve().parent / "data" / run_id / "ct_counts_by_topps_classifier.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)

    counts = Counter()
    scanned = 0
    empty_title = 0

    limit = 1000
    offset = 0

    # Cmd+F: GH_ANCHOR_PAGINATE_TERM_SEARCH_ITEMS_9D2A1C90
    while True:
        params = {"q": q, "limit": str(limit), "offset": str(offset)}
        endpoint = urljoin(base.rstrip("/") + "/", "internal/termSearchItems/search")
        url = f"{endpoint}?{urlencode(params)}"

        data = _worker_get_json(url, key)
        rows = data.get("rows") or []
        if not isinstance(rows, list):
            raise RuntimeError("Worker returned rows that were not a list")

        for row in rows:
            scanned += 1
            title = (row.get(args.title_col) or "").strip() if isinstance(row, dict) else ""
            if not title:
                empty_title += 1
                continue

            flags = classify_title(title)
            for k in ct_keys:
                if _truthy(flags.get(k, False)):
                    counts[k] += 1

            if args.max_rows and scanned >= int(args.max_rows):
                rows = []
                break

        next_offset = data.get("next_offset")
        if not next_offset or not rows:
            break
        offset = int(next_offset)

    # write counts
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ct_key", "count"])
        for k, c in counts.most_common():
            w.writerow([k, c])

    print(f"Q={q}")
    print(f"OUTPUT={out_path}")
    print(f"ROWS_SCANNED={scanned}")
    print(f"EMPTY_TITLE_ROWS={empty_title}")
    print(f"CT_KEYS_DISCOVERED={len(ct_keys)}")
    print("TOP_20_CTS=")
    for k, c in counts.most_common(20):
        print(f"  {k}={c}")


if __name__ == "__main__":
    main()
