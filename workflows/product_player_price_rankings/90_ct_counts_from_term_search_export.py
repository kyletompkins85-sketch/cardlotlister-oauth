#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_CT_COUNTS_FROM_TERM_SEARCH_EXPORT_4B7D1C90
"""
Apply Bowman classifier to an existing exported CSV of titles and count CT_* hits.
Includes ZERO counts for CTs that never hit.

Input default (by RUN_ID):
  workflows/product_player_price_rankings/data/<RUN_ID>/term_search_items_export.csv

Outputs:
  - ct_counts_by_bowman_classifier.csv  (ALL CT_* keys, including zeros)
  - ct_samples_by_bowman_classifier.csv (optional title samples per CT, for diagnostics)

NO NETWORK CALLS. NO EBAY.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "y", "t", "on")
    return bool(v)


def _load_bowman_classifier():
    """
    Load classify_title from z10_bowman_listing_classifier.py living in this workflow folder.
    """
    # Cmd+F: GH_ANCHOR_IMPORT_BOWMAN_CLASSIFIER_91C2A0B1
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))

    try:
        from z10_bowman_listing_classifier import classify_title  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Could not import z10_bowman_listing_classifier.py from "
            "workflows/product_player_price_rankings/. "
            "Make sure that file exists and is committed.\n"
            f"IMPORT_ERROR={e}"
        )
    return classify_title


def main() -> None:
    # Cmd+F: GH_ANCHOR_CT_COUNTS_BOWMAN_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="", help="RUN_ID folder under workflows/product_player_price_rankings/data/")
    ap.add_argument("--input", default="", help="Explicit input CSV path (overrides --run-id)")
    ap.add_argument("--out-counts", default="", help="Explicit output counts CSV path override")
    ap.add_argument("--out-samples", default="", help="Explicit output samples CSV path override (blank disables)")
    ap.add_argument("--title-col", default="title", help="Title column name (default: title)")
    ap.add_argument("--max-rows", type=int, default=0, help="If >0, stop after scanning this many rows")
    ap.add_argument("--samples-per-ct", type=int, default=5, help="How many example titles per CT (default: 5)")
    args = ap.parse_args()

    workflow_root = Path(__file__).resolve().parent
    data_root = workflow_root / "data"

    run_id = (args.run_id or os.getenv("RUN_ID") or "").strip()

    if args.input.strip():
        in_path = Path(args.input.strip())
    else:
        if not run_id:
            raise SystemExit("Provide --run-id or --input")
        in_path = data_root / run_id / "term_search_items_export.csv"

    if not in_path.exists():
        raise SystemExit(f"Input CSV not found: {in_path}")

    if args.out_counts.strip():
        out_counts = Path(args.out_counts.strip())
    else:
        if run_id:
            out_counts = data_root / run_id / "ct_counts_by_bowman_classifier.csv"
        else:
            out_counts = in_path.parent / "ct_counts_by_bowman_classifier.csv"
    out_counts.parent.mkdir(parents=True, exist_ok=True)

    samples_enabled = bool(args.out_samples.strip() or run_id or True)
    if args.out_samples.strip():
        out_samples = Path(args.out_samples.strip())
    else:
        # default: write alongside counts in run folder
        if run_id:
            out_samples = data_root / run_id / "ct_samples_by_bowman_classifier.csv"
        else:
            out_samples = in_path.parent / "ct_samples_by_bowman_classifier.csv"
    out_samples.parent.mkdir(parents=True, exist_ok=True)

    title_col = (args.title_col or "title").strip()
    max_rows = int(args.max_rows or 0)
    samples_per_ct = max(0, int(args.samples_per_ct or 0))

    classify_title = _load_bowman_classifier()

    # Discover all CT_* keys from template so we can output zeros too
    # Cmd+F: GH_ANCHOR_DISCOVER_ALL_CT_KEYS_BOWMAN_2C7B9D10
    tmpl: Dict[str, object] = classify_title("")
    ct_keys: List[str] = sorted([k for k, v in tmpl.items() if k.startswith("CT_") and isinstance(v, bool)])

    counts = Counter({k: 0 for k in ct_keys})  # pre-seed with zeros
    samples: Dict[str, List[str]] = defaultdict(list)

    scanned = 0
    empty_title = 0

    # Cmd+F: GH_ANCHOR_SCAN_AND_COUNT_LOOP_BOWMAN_88AA10F1
    with in_path.open("r", encoding="utf-8", newline="") as fin:
        r = csv.DictReader(fin)
        if not r.fieldnames:
            raise SystemExit("Input CSV has no header row")

        for row in r:
            scanned += 1
            title = (row.get(title_col) or "").strip()
            if not title:
                empty_title += 1
                continue

            flags = classify_title(title)

            for k in ct_keys:
                if _truthy(flags.get(k, False)):
                    counts[k] += 1
                    if samples_per_ct > 0 and len(samples[k]) < samples_per_ct:
                        samples[k].append(title)

            if max_rows > 0 and scanned >= max_rows:
                break

    # Write counts INCLUDING zeros
    # Cmd+F: GH_ANCHOR_WRITE_COUNTS_WITH_ZEROS_6C2A1D12
    with out_counts.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ct_key", "count"])
        for k in ct_keys:
            w.writerow([k, int(counts.get(k, 0))])

    # Write samples (helps you see “which ones fit”)
    # Cmd+F: GH_ANCHOR_WRITE_CT_SAMPLES_6C2A1D13
    if samples_per_ct > 0:
        with out_samples.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["ct_key", "count", "sample_titles"])
            for k in ct_keys:
                sample_joined = " | ".join(samples.get(k, []))
                w.writerow([k, int(counts.get(k, 0)), sample_joined])

    print(f"INPUT={in_path}")
    print(f"OUT_COUNTS={out_counts}")
    if samples_per_ct > 0:
        print(f"OUT_SAMPLES={out_samples}")
    print(f"ROWS_SCANNED={scanned}")
    print(f"EMPTY_TITLE_ROWS={empty_title}")
    print(f"CT_KEYS_TOTAL={len(ct_keys)}")


if __name__ == "__main__":
    main()
