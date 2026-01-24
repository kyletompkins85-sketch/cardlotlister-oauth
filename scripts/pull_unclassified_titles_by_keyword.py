#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_PULL_UNCLASSIFIED_BY_KEYWORD_6C2A1D90
import argparse
import csv
import os
import sys
from typing import Dict, List, Any

# Allow importing sibling script from scripts/
# Cmd+F: GH_ANCHOR_IMPORT_CLASSIFIER_FOR_UNCLASSIFIED_2B7A1D91
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from topps_listing_classifier import classify_title  # noqa: E402


def _truthy_csv(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "y", "t")
    return bool(v)


def main() -> None:
    # Cmd+F: GH_ANCHOR_PULL_UNCLASSIFIED_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input CSV path (e.g. data/term_search_items_table.csv)")
    ap.add_argument("--keyword", required=True, help="Case-insensitive substring match on title")
    ap.add_argument("--out", required=True, help="Output CSV path (e.g. data/unclassified_titles_canvas.csv)")
    ap.add_argument("--max-rows", type=int, default=1000, help="Max output rows (default: 1000)")
    ap.add_argument("--title-col", default="title", help="Title column name (default: title)")
    ap.add_argument("--dedupe", action="store_true", help="If set, de-dupe identical titles")
    ap.add_argument(
        "--use-ct-any-column",
        action="store_true",
        help="If set, use existing CT_any column from input instead of classifying titles",
    )
    ap.add_argument("--ct-any-col", default="CT_any", help="CT_any column name if present (default: CT_any)")
    args = ap.parse_args()

    in_path = args.input
    out_path = args.out
    title_col = (args.title_col or "title").strip()
    kw = (args.keyword or "").strip().lower()
    max_rows = max(1, int(args.max_rows))
    dedupe = bool(args.dedupe)
    use_ct_any_col = bool(args.use_ct_any_column)
    ct_any_col = (args.ct_any_col or "CT_any").strip()

    if not os.path.exists(in_path):
        raise SystemExit(f"Input CSV not found: {in_path}")
    if not kw:
        raise SystemExit("Missing --keyword")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Pre-discover CT_* keys so CT_any is computed by looping, not hard-coded.
    # Cmd+F: GH_ANCHOR_DISCOVER_CT_KEYS_7A1B2C3D
    tmpl: Dict[str, object] = classify_title("")
    ct_keys: List[str] = [k for k, v in tmpl.items() if isinstance(v, bool) and k.startswith("CT_")]

    seen = set()
    wrote = 0
    scanned = 0
    matched_kw = 0
    unclassified = 0

    # Output minimal columns: keyword, title
    # Cmd+F: GH_ANCHOR_OUTPUT_COLUMNS_UNCLASSIFIED_TITLES_9D2A1C90
    out_cols = ["keyword", "title"]

    with open(in_path, "r", encoding="utf-8", newline="") as fin, open(out_path, "w", encoding="utf-8", newline="") as fout:
        r = csv.DictReader(fin)
        if not r.fieldnames:
            raise SystemExit("Input CSV has no header row")

        w = csv.DictWriter(fout, fieldnames=out_cols)
        w.writeheader()

        for row in r:
            scanned += 1
            title = (row.get(title_col) or "").strip()
            if not title:
                continue

            if kw not in title.lower():
                continue
            matched_kw += 1

            # Decide classified vs unclassified
            if use_ct_any_col and (ct_any_col in row):
                ct_any = _truthy_csv(row.get(ct_any_col))
            else:
                flags = classify_title(title)
                ct_any = any(bool(flags.get(k, False)) for k in ct_keys)

            if ct_any:
                continue
            unclassified += 1

            if dedupe:
                key = title.lower()
                if key in seen:
                    continue
                seen.add(key)

            w.writerow({"keyword": kw, "title": title})
            wrote += 1

            if wrote >= max_rows:
                break

    print(f"INPUT={in_path}")
    print(f"OUTPUT={out_path}")
    print(f"KEYWORD={kw}")
    print(f"MAX_ROWS={max_rows}")
    print(f"USE_CT_ANY_COLUMN={use_ct_any_col} ({ct_any_col})")
    print(f"SCANNED_ROWS={scanned}")
    print(f"MATCHED_KEYWORD={matched_kw}")
    print(f"UNCLASSIFIED_MATCHED={unclassified}")
    print(f"WROTE_ROWS={wrote}")


# Cmd+F: GH_ANCHOR_PULL_UNCLASSIFIED_RUN_MAIN_6C2A1D92
if __name__ == "__main__":
    main()

