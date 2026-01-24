#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_CLASSIFY_EXISTING_LISTINGS_JSON_6C2A1D90
import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List

# Allow importing sibling script from scripts/
# Cmd+F: GH_ANCHOR_IMPORT_CLASSIFIER_EXISTING_LISTINGS_2B7A1D91
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from topps_listing_classifier import classify_title  # noqa: E402

# Cmd+F: GH_ANCHOR_CT_NAME_FORMATTER_6C2A1D93
def format_ct_name(ct_key: str) -> str:
    """
    Convert 'CT_chrome' -> 'Chrome'
            'CT_base_rainbow' -> 'Base Rainbow'
            'CT_x_fractor' -> 'X-Fractor'
            'CT_ssp' -> 'SSP'
    """
    raw = (ct_key or "").strip()
    if raw.startswith("CT_"):
        raw = raw[3:]

    specials = {
        "ssp": "SSP",
        "sp": "SP",
        "rc": "RC",
        "x_fractor": "X-Fractor",
    }
    if raw in specials:
        return specials[raw]

    parts = raw.split("_")
    out_parts: List[str] = []
    for p in parts:
        if not p:
            continue
        if p.isdigit():
            out_parts.append(p)
        elif p in ("ssp", "sp", "rc"):
            out_parts.append(p.upper())
        else:
            out_parts.append(p[:1].upper() + p[1:].lower())
    return " ".join(out_parts)

# Cmd+F: GH_ANCHOR_LOT_FILTER_HELPER_6C2A1D95
import re
RX_LOT = re.compile(r"\blot\b|\blots\b|\bteam\s*lot\b|\bplayer\s*lot\b", re.IGNORECASE)

def is_lot_title(title: str, flags: Dict[str, Any]) -> bool:
    # Prefer classifier signal if present; fallback to regex.
    if bool(flags.get("WF_lot", False)) or bool(flags.get("CT_lot", False)):
        return True
    return RX_LOT.search(title or "") is not None

def _to_float(v: Any) -> float:
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except Exception:
        return 0.0


def _load_rows_from_json(path: str) -> List[Dict[str, Any]]:
    # Cmd+F: GH_ANCHOR_LOAD_ROWS_FROM_JSON_7A1B2C3D
    # Supports:
    #  - .json  (array or {"rows":[...]})
    #  - .jsonl (one JSON object per line)
    p = path.lower().strip()

    if p.endswith(".jsonl"):
        rows: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
        return rows

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support common shapes:
    #  - [ {...}, {...} ]
    #  - { "rows": [ ... ] }
    #  - { ...single row... }
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("rows"), list):
            return [r for r in data["rows"] if isinstance(r, dict)]
        return [data]
    return []


def main() -> None:
    # Cmd+F: GH_ANCHOR_CLASSIFY_EXISTING_LISTINGS_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input JSON file (e.g. data/listings_2025_topps_update.json)")
    ap.add_argument("--out", required=True, help="Output CSV file (e.g. data/listings_2025_topps_update_classified.csv)")
    ap.add_argument("--title-key", default="title", help="Title field name (default: title)")
    ap.add_argument("--price-key", default="price", help="Price field name (default: price)")
    ap.add_argument("--shipping-key", default="shipping_cost", help="Shipping field name (default: shipping_cost)")
    ap.add_argument("--max-out", type=int, default=1000, help="Max output rows (default: 1000)")
    ap.add_argument("--only-unclassified", action="store_true", help="If set, keep only CT_any=false rows")
    args = ap.parse_args()

    in_path = args.input.strip()
    out_path = args.out.strip()
    title_key = (args.title_key or "title").strip()
    price_key = (args.price_key or "price").strip()
    shipping_key = (args.shipping_key or "shipping_cost").strip()
    max_out = max(1, int(args.max_out))
    only_unclassified = bool(args.only_unclassified)

    if not os.path.exists(in_path):
        raise SystemExit(f"Input JSON not found: {in_path}")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    rows = _load_rows_from_json(in_path)

    # Discover CT_* keys deterministically
    # Cmd+F: GH_ANCHOR_DISCOVER_CT_KEYS_EXISTING_LISTINGS_4D2A1C90
    tmpl: Dict[str, object] = classify_title("")
    ct_cols: List[str] = [k for k, v in tmpl.items() if isinstance(v, bool) and k.startswith("CT_")]

    # Build classified rows, filter if requested, sort by all_in_price desc, take top N
    # Cmd+F: GH_ANCHOR_CLASSIFY_FILTER_SORT_LIMIT_9D2A1C90
    classified: List[Dict[str, Any]] = []
    for r in rows:
        title = (r.get(title_key) or "").strip()
        price = _to_float(r.get(price_key))
        ship = _to_float(r.get(shipping_key))
        all_in = price + ship

        flags = classify_title(title)
        if is_lot_title(title, flags):
            continue
        ct_values = {k: bool(flags.get(k, False)) for k in ct_cols}
        ct_any = any(ct_values.values())
        ct_true_names = [format_ct_name(k) for k, v in ct_values.items() if v]
        ct_list = ", ".join(ct_true_names)


        if only_unclassified and ct_any:
            continue

        out_row: Dict[str, Any] = {
            "title": title,
            "all_in_price": round(all_in, 4),
            "CT_any": ct_any,
            "CT_list": ct_list,
        }
        classified.append(out_row)

    classified.sort(key=lambda x: _to_float(x.get("all_in_price")), reverse=True)
    classified = classified[:max_out]

    # Output columns (keep it small): title + price + classification summary
    out_cols = ["title", "all_in_price", "CT_any", "CT_list"]


    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_cols)
        w.writeheader()
        for row in classified:
            w.writerow(row)

    print(f"INPUT={in_path}")
    print(f"OUTPUT={out_path}")
    print(f"ROWS_IN={len(rows)}")
    print(f"ONLY_UNCLASSIFIED={only_unclassified}")
    print(f"WROTE={len(classified)}")
    print(f"CT_COLS={len(ct_cols)}")


if __name__ == "__main__":
    main()
