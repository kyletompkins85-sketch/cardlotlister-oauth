#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_CT_COUNTS_FROM_TERM_SEARCH_EXPORT_4B7D1C90
"""
Applies your Topps classifier to term_search_items_export.csv and counts how many
titles hit each CT_* boolean.

Input:
  workflows/product_player_price_rankings/data/<RUN_ID>/term_search_items_export.csv

Output:
  workflows/product_player_price_rankings/data/<RUN_ID>/ct_counts_by_topps_classifier.csv

Usage:
  python workflows/product_player_price_rankings/90_ct_counts_from_term_search_export.py \
    --run-id "$RUN_ID"

Or explicit paths:
  python workflows/product_player_price_rankings/90_ct_counts_from_term_search_export.py \
    --input workflows/product_player_price_rankings/data/<RUN_ID>/term_search_items_export.csv \
    --out   workflows/product_player_price_rankings/data/<RUN_ID>/ct_counts_by_topps_classifier.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import Counter
from typing import Any, Dict, List

# Cmd+F: GH_ANCHOR_IMPORT_TOPPS_CLASSIFIER_FOR_CT_COUNTS_1A2B3C4D
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# IMPORTANT: this must exist in your repo (same as your diagnostics scripts)
from topps_listing_classifier import classify_title  # noqa: E402


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "y", "t", "on")
    return bool(v)


def main() -> None:
    # Cmd+F: GH_ANCHOR_CT_COUNTS_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="", help="RUN_ID folder under workflows/product_player_price_rankings/data/")
    ap.add_argument("--input", default="", help="Explicit input CSV path (overrides --run-id)")
    ap.add_argument("--out", default="", help="Explicit output CSV path (overrides --run-id)")
    ap.add_argument("--title-col", default="title", help="Title column name (default: title)")
    ap.add_argument("--max-rows", type=int, default=0, help="If >0, stop after scanning this many rows")
    args = ap.parse_args()

    workflow_root = os.path.dirname(os.path.abspath(__file__))
    data_root = os.path.join(workflow_root, "data")

    run_id = (args.run_id or os.getenv("RUN_ID") or "").strip()

    if args.input.strip():
        in_path = args.input.strip()
    else:
        if not run_id:
            raise SystemExit("Provide --run-id or --input")
        in_path = os.path.join(data_root, run_id, "term_search_items_export.csv")

    if args.out.strip():
        out_path = args.out.strip()
    else:
        if not run_id:
            # if user passed --input only, default output beside input
            out_path = os.path.join(os.path.dirname(in_path), "ct_counts_by_topps_classifier.csv")
        else:
            out_path = os.path.join(data_root, run_id, "ct_counts_by_topps_classifier.csv")

    title_col = (args.title_col or "title").strip()
    max_rows = int(args.max_rows or 0)

    if not os.path.exists(in_path):
        raise SystemExit(f"Input CSV not found: {in_path}")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Discover CT_* keys from classifier template
    # Cmd+F: GH_ANCHOR_DISCOVER_CT_KEYS_CT_COUNTS_9D2A1C90
    tmpl: Dict[str, object] = classify_title("")
    ct_keys: List[str] = sorted([k for k, v in tmpl.items() if k.startswith("CT_") and isinstance(v, bool)])

    counts = Counter()
    scanned = 0
    empty_title = 0

    # Cmd+F: GH_ANCHOR_SCAN_AND_COUNT_LOOP_88AA10F1
    with open(in_path, "r", encoding="utf-8", newline="") as fin:
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

            if max_rows > 0 and scanned >= max_rows:
                break

    # Write output
    # Cmd+F: GH_ANCHOR_WRITE_CT_COUNTS_OUT_2C7B9D10
    with open(out_path, "w", encoding="utf-8", newline="") as fout:
        w = csv.writer(fout)
        w.writerow(["ct_key", "count"])
        for k, c in counts.most_common():
            w.writerow([k, c])

    print(f"INPUT={in_path}")
    print(f"OUTPUT={out_path}")
    print(f"ROWS_SCANNED={scanned}")
    print(f"EMPTY_TITLE_ROWS={empty_title}")
    print(f"CT_KEYS_DISCOVERED={len(ct_keys)}")
    print("TOP_20_CTS=")
    for k, c in counts.most_common(20):
        print(f"  {k}={c}")


if __name__ == "__main__":
    main()
