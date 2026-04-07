#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_APPEND_FLAGS_FIRST_1000_2A7C1D90
import argparse
import csv
import os
import sys
from typing import Dict, List

# Allow importing topps_listing_classifier from this directory.
# Cmd+F: GH_ANCHOR_IMPORT_CLASSIFIER_5F1A3B8D
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from topps_listing_classifier import classify_title  # noqa: E402


def main() -> None:
    # Cmd+F: GH_ANCHOR_APPEND_FLAGS_MAIN_9C0B3E12
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        required=True,
        help="Input CSV path (e.g. data/topps_update_2025/term_search_items_table.csv)",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output CSV path (e.g. data/topps_update_2025/term_search_items_table_classified_1000.csv)",
    )
    ap.add_argument("--title-col", default="title", help="CSV column containing the title (default: title)")
    ap.add_argument("--max-rows", type=int, default=1000, help="Max rows to process (default: 1000)")
    ap.add_argument("--only-unclassified", action="store_true",
                    help="If set, output only rows where CT_any is False (no CT_* matched)")
    ap.add_argument("--window", choices=["first", "last"], default="first",
                    help="Process first N rows or last N rows from the input (default: first)")

    args = ap.parse_args()

    in_path = args.input
    out_path = args.out
    title_col = args.title_col
    max_rows = max(1, int(args.max_rows))
    # Cmd+F: GH_ANCHOR_ALWAYS_FILTER_CT_ANY_FALSE_8C1A2D90
    only_unclassified = True  # ALWAYS filter: only rows where CT_any == False
    window = (args.window or "first").strip().lower()


    if not os.path.exists(in_path):
        raise SystemExit(f"Input CSV not found: {in_path}")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Discover boolean flag columns deterministically.
    # Output order requirement: title, then CT_*, then WF_*.
    # Cmd+F: GH_ANCHOR_FLAG_COLUMNS_DISCOVERY_7A1B2C3D
    flag_template: Dict[str, object] = classify_title("")
    bool_keys_in_order: List[str] = [k for k, v in flag_template.items() if isinstance(v, bool)]

    ct_cols: List[str] = [k for k in bool_keys_in_order if k.startswith("CT_")]
    wf_cols: List[str] = [k for k in bool_keys_in_order if k.startswith("WF_")]

    processed = 0

        # Read rows depending on window mode
    # Cmd+F: GH_ANCHOR_WINDOW_MODE_4D2A1C90
    def iter_source_rows():
        with open(in_path, "r", encoding="utf-8", newline="") as fin:
            r = csv.DictReader(fin)
            if not r.fieldnames:
                raise SystemExit("Input CSV has no header row")
            yield ("__header__", r.fieldnames)

            if window == "first":
                # Cmd+F: GH_ANCHOR_SCAN_ALL_ROWS_FOR_TOPN_8C1A2D90
                # IMPORTANT: when doing "top N by price", we must scan ALL rows.
                for row in r:
                    yield ("row", row)

            else:
                # last N: keep a ring buffer
                buf = []
                for row in r:
                    buf.append(row)
                    if len(buf) > max_rows:
                        buf.pop(0)
                for row in buf:
                    yield ("row", row)

    # Cmd+F: GH_ANCHOR_OUT_COLS_WITH_ALL_IN_7C2A1D90
    out_cols = [title_col, "all_in_price", "CT_any"] + ct_cols


    processed_in = 0
    written_out = 0

    # Cmd+F: GH_ANCHOR_ALL_IN_PRICE_SORT_BLOCK_4B1F8A22
    import heapq

    def _to_num(x):
        if x is None:
            return None
        s = str(x).strip()
        if not s:
            return None
        s = s.replace("$", "").replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None

    processed_in = 0
    kept_top_n = 0

    # Min-heap of (all_in_price, seq, out_row) so we can keep top-N efficiently
    top_heap = []
    seq = 0

    header_seen = False
    for kind, payload in iter_source_rows():
        if kind == "__header__":
            header_seen = True
            continue
        if not header_seen:
            raise SystemExit("Missing CSV header")

        row = payload
        processed_in += 1

        title = (row.get(title_col) or "").strip()
        flags = classify_title(title)

        # Compute CT_* values first (loop), then CT_any is "any true"
        ct_values = {k: bool(flags.get(k, False)) for k in ct_cols}
        ct_any = any(ct_values.values())

        # Filter: keep only unclassified if requested
        if only_unclassified and ct_any:
            continue

        price = _to_num(row.get("price"))
        ship = _to_num(row.get("shipping_cost"))

        if price is None and ship is None:
            # no usable price -> skip for "top priced"
            continue

        all_in = (price or 0.0) + (ship or 0.0)

        out_row = {title_col: title, "all_in_price": all_in, "CT_any": ct_any}
        out_row.update(ct_values)

        seq += 1
        item = (all_in, seq, out_row)

        if len(top_heap) < max_rows:
            heapq.heappush(top_heap, item)
        else:
            # Keep only the largest all_in prices
            if all_in > top_heap[0][0]:
                heapq.heapreplace(top_heap, item)

    # Extract and sort descending by all_in_price
    top_rows = [t[2] for t in top_heap]
    top_rows.sort(key=lambda r: (r["all_in_price"] is None, -(r["all_in_price"] or 0.0)))

    with open(out_path, "w", encoding="utf-8", newline="") as fout:
        w = csv.DictWriter(fout, fieldnames=out_cols, extrasaction="ignore")
        w.writeheader()
        for r in top_rows:
            w.writerow(r)

    kept_top_n = len(top_rows)

    print(f"INPUT={in_path}")
    print(f"OUTPUT={out_path}")
    print(f"WINDOW={window}")
    print(f"MAX_ROWS={max_rows}")
    print(f"ONLY_UNCLASSIFIED={only_unclassified}")
    print(f"PROCESSED_ROWS_TOTAL={processed_in}")
    print(f"TOP_N_WRITTEN={kept_top_n}")






if __name__ == "__main__":
    main()
