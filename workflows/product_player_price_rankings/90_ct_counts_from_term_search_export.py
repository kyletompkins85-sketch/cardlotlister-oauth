#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_CT_COUNTS_FROM_TERM_SEARCH_EXPORT_4B7D1C90
"""
Apply BOWMAN classifier to existing titles and count CT_* hits (INCLUDING zeros).

Sources (in order):
  1) If present: workflows/product_player_price_rankings/data/<RUN_ID>/term_search_items_export.csv
  2) Fallback: Worker -> GET /internal/termSearchItems/search?q=... (NO EBAY)

Outputs (to workflows/product_player_price_rankings/data/<RUN_ID>/):
  - ct_counts_by_bowman_classifier.csv      (ALL CT_* keys, including zeros)
  - ct_samples_by_bowman_classifier.csv     (sample titles per CT for validation)

NO EBAY CALLS.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Iterable, Optional
from urllib.parse import urlencode, urljoin

import requests


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "y", "t", "on")
    return bool(v)


def _passes_require_all(title: str, require_all_csv: str) -> bool:
    # Cmd+F: GH_ANCHOR_PASSES_REQUIRE_ALL_2B7D1C90
    words = [w.strip().lower() for w in (require_all_csv or "").split(",") if w.strip()]
    if not words:
        return True
    t = (title or "").lower()
    return all(w in t for w in words)

def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _load_bowman_classifier():
    # Cmd+F: GH_ANCHOR_IMPORT_BOWMAN_CLASSIFIER_91C2A0B1
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))

    try:
        from z10_bowman_listing_classifier import classify_title  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Could not import z10_bowman_listing_classifier.py from "
            "workflows/product_player_price_rankings/. Make sure it exists and is committed.\n"
            f"IMPORT_ERROR={e}"
        )
    return classify_title


def _iter_titles_from_export_csv(csv_path: Path, title_col: str) -> Iterable[str]:
    # Cmd+F: GH_ANCHOR_ITER_TITLES_FROM_EXPORT_CSV_7A1B2C3D
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            return
        for row in r:
            t = (row.get(title_col) or "").strip()
            if t:
                yield t


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


def _iter_titles_from_worker(base_url: str, api_key: str, q: str, title_key: str = "title") -> Iterable[str]:
    # Cmd+F: GH_ANCHOR_ITER_TITLES_FROM_WORKER_0C7E4A21
    limit = 1000
    offset = 0

    while True:
        params = {"q": q, "limit": str(limit), "offset": str(offset)}
        endpoint = urljoin(base_url.rstrip("/") + "/", "internal/termSearchItems/search")
        url = f"{endpoint}?{urlencode(params)}"

        data = _worker_get_json(url, api_key)
        rows = data.get("rows") or []
        if not isinstance(rows, list):
            raise RuntimeError("Worker returned rows that were not a list")

        for row in rows:
            if not isinstance(row, dict):
                continue
            t = (row.get(title_key) or "").strip()
            if t:
                yield t

        next_offset = data.get("next_offset")
        if not next_offset:
            break
        offset = int(next_offset)


def main() -> None:
    # Cmd+F: GH_ANCHOR_CT_COUNTS_BOWMAN_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="", help="RUN_ID folder under workflows/product_player_price_rankings/data/")
    ap.add_argument("--q", default="", help="Worker search q fallback (e.g. '2025 Bowman Draft')")
    ap.add_argument("--title-col", default="title", help="Title column in export CSV (default: title)")
    ap.add_argument("--max-rows", type=int, default=0, help="If >0, stop after this many titles")
    ap.add_argument("--samples-per-ct", type=int, default=5, help="Sample titles per CT (default: 5)")
      # Cmd+F: GH_ANCHOR_REQUIRE_WORDS_FILTER_1A7C9D20
    ap.add_argument(
        "--require-all",
        default="bowman,draft",
        help="Comma-separated words that MUST appear in title (case-insensitive). Default: bowman,draft",
    )
    args = ap.parse_args()

    workflow_root = Path(__file__).resolve().parent
    data_root = workflow_root / "data"

    run_id = (args.run_id or os.getenv("RUN_ID") or "").strip()
    if not run_id:
        raise SystemExit("Missing --run-id (or env RUN_ID)")

    run_dir = data_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    export_csv = run_dir / "term_search_items_export.csv"
    title_col = (args.title_col or "title").strip()
    max_rows = int(args.max_rows or 0)
    samples_per_ct = max(0, int(args.samples_per_ct or 0))

    classify_title = _load_bowman_classifier()

    # Discover all CT_* keys (so we can output zeros too)
    # Cmd+F: GH_ANCHOR_DISCOVER_ALL_CT_KEYS_BOWMAN_2C7B9D10
    tmpl: Dict[str, object] = classify_title("")
    ct_keys: List[str] = sorted([k for k, v in tmpl.items() if k.startswith("CT_") and isinstance(v, bool)])

    counts = Counter({k: 0 for k in ct_keys})
    samples: Dict[str, List[str]] = defaultdict(list)

    # Decide source
    # Cmd+F: GH_ANCHOR_SELECT_SOURCE_CSV_OR_WORKER_9B7A1C20
    titles_iter: Iterable[str]
    source = ""
    if export_csv.exists():
        source = f"csv:{export_csv}"
        titles_iter = _iter_titles_from_export_csv(export_csv, title_col)
    else:
        # fallback to Worker/Supabase
        base = _require_env("WORKER_BASE_URL")
        key = _require_env("INTERNAL_API_KEY")
        q = (args.q or os.getenv("PREFIX") or "").strip()
        if not q:
            raise SystemExit(
                f"Input CSV not found: {export_csv}\n"
                "And no fallback query provided. Provide --q or set env PREFIX."
            )
        source = f"worker:/internal/termSearchItems/search?q={q}"
        titles_iter = _iter_titles_from_worker(base, key, q, title_key="title")

    scanned = 0

    # Cmd+F: GH_ANCHOR_COUNT_AND_SAMPLE_LOOP_BOWMAN_88AA10F1
    for title in titles_iter:
        scanned += 1
        # Cmd+F: GH_ANCHOR_APPLY_REQUIRE_ALL_FILTER_3C8F0B2A
        if not _passes_require_all(title, args.require_all):
            continue
        flags = classify_title(title)

        for k in ct_keys:
            if _truthy(flags.get(k, False)):
                counts[k] += 1
                if samples_per_ct > 0 and len(samples[k]) < samples_per_ct:
                    samples[k].append(title)

        if max_rows > 0 and scanned >= max_rows:
            break

    out_counts = run_dir / "ct_counts_by_bowman_classifier.csv"
    out_samples = run_dir / "ct_samples_by_bowman_classifier.csv"

    # Write counts INCLUDING zeros
    # Cmd+F: GH_ANCHOR_WRITE_COUNTS_WITH_ZEROS_6C2A1D12
    with out_counts.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ct_key", "count"])
        for k in ct_keys:
            w.writerow([k, int(counts.get(k, 0))])

    # Write samples to validate “which ones fit”
    # Cmd+F: GH_ANCHOR_WRITE_CT_SAMPLES_6C2A1D13
    with out_samples.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ct_key", "count", "sample_titles"])
        for k in ct_keys:
            w.writerow([k, int(counts.get(k, 0)), " | ".join(samples.get(k, []))])

    print(f"SOURCE={source}")
    print(f"RUN_ID={run_id}")
    print(f"SCANNED_TITLES={scanned}")
    print(f"OUT_COUNTS={out_counts}")
    print(f"OUT_SAMPLES={out_samples}")
    print(f"CT_KEYS_TOTAL={len(ct_keys)}")
    print(f"REQUIRE_ALL={args.require_all}")


if __name__ == "__main__":
    main()
