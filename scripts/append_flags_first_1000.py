#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_APPEND_FLAGS_FIRST_1000_2A7C1D90
import argparse
import csv
import os
import sys
from typing import Dict, List

# Allow importing sibling script from scripts/
# Cmd+F: GH_ANCHOR_IMPORT_CLASSIFIER_5F1A3B8D
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from topps_listing_classifier import classify_title  # noqa: E402


def main() -> None:
    # Cmd+F: GH_ANCHOR_APPEND_FLAGS_MAIN_9C0B3E12
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input CSV path (e.g. data/term_search_items_table.csv)")
    ap.add_argument("--out", required=True, help="Output CSV path (e.g. data/term_search_items_table_classified_1000.csv)")
    ap.add_argument("--title-col", default="title", help="CSV column containing the title (default: title)")
    ap.add_argument("--max-rows", type=int, default=1000, help="Max rows to process (default: 1000)")
    args = ap.parse_args()

    in_path = args.input
    out_path = args.out
    title_col = args.title_col
    max_rows = max(1, int(args.max_rows))

    if not os.path.exists(in_path):
        raise SystemExit(f"Input CSV not found: {in_path}")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Discover the classifier output columns deterministically.
    # classify_title("") returns all keys (colors/finishes/etc.) with False/None values.
    # Cmd+F: GH_ANCHOR_FLAG_COLUMNS_DISCOVERY_7A1B2C3D
    flag_template: Dict[str, object] = classify_title("")
    flag_cols: List[str] = list(flag_template.keys())

    processed = 0

    with open(in_path, "r", encoding="utf-8", newline="") as fin:
        r = csv.DictReader(fin)
        if not r.fieldnames:
            raise SystemExit("Input CSV has no header row")

        base_cols = list(r.fieldnames)
        out_cols = base_cols + [c for c in flag_cols if c not in base_cols]

        with open(out_path, "w", encoding="utf-8", newline="") as fout:
            w = csv.DictWriter(fout, fieldnames=out_cols, extrasaction="ignore")
            w.writeheader()

            for row in r:
                if processed >= max_rows:
                    break

                title = (row.get(title_col) or "").strip()
                flags = classify_title(title)

                out_row = dict(row)
                out_row.update({k: flags.get(k) for k in flag_cols})

                w.writerow(out_row)
                processed += 1

    print(f"INPUT={in_path}")
    print(f"OUTPUT={out_path}")
    print(f"PROCESSED_ROWS={processed}")
    print(f"FLAG_COLUMNS={len(flag_cols)}")


if __name__ == "__main__":
    main()
