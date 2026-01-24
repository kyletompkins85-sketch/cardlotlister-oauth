#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_JSONL_TO_TABLE_SCRIPT_8D2A1C90
import argparse
import csv
import glob
import json
import os
from typing import Any, Dict, List, Set, Tuple


def _is_scalar(x: Any) -> bool:
    return x is None or isinstance(x, (str, int, float, bool))


def flatten(obj: Any, prefix: str = "", out: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Flatten nested JSON into dot-keys:
      {"a":{"b":1}} -> {"a.b":1}
    Lists/dicts that remain are JSON-stringified.
    """
    if out is None:
        out = {}

    if _is_scalar(obj):
        if prefix:
            out[prefix] = obj
        return out

    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if _is_scalar(v) or isinstance(v, dict):
                flatten(v, key, out)
            else:
                out[key] = json.dumps(v, ensure_ascii=False)
        return out

    if isinstance(obj, list):
        if prefix:
            out[prefix] = json.dumps(obj, ensure_ascii=False)
        return out

    if prefix:
        out[prefix] = str(obj)
    return out


def iter_rows(paths: List[str]):
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)


def discover_columns(paths: List[str], max_scan: int = 200_000) -> List[str]:
    # Cmd+F: GH_ANCHOR_DISCOVER_COLUMNS_4B1F8A22
    cols: Set[str] = set()
    scanned = 0
    for row in iter_rows(paths):
        flat = flatten(row)
        cols.update(flat.keys())
        scanned += 1
        if scanned >= max_scan:
            break
    return sorted(cols)


def write_csv(paths: List[str], out_path: str, columns: List[str]) -> Tuple[int, int]:
    # Cmd+F: GH_ANCHOR_WRITE_CSV_91A0D2C3
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    written = 0
    dropped = 0

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()

        for row in iter_rows(paths):
            flat = flatten(row)
            out_row = {k: flat.get(k, None) for k in columns}
            if not any(v is not None and v != "" for v in out_row.values()):
                dropped += 1
                continue
            w.writerow(out_row)
            written += 1

    return written, dropped


def main():
    # Cmd+F: GH_ANCHOR_JSONL_TO_TABLE_MAIN_3F1B7C2A
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Input JSONL path or glob (e.g. data/term_search_items_*.jsonl)")
    ap.add_argument("--out", required=True, help="Output CSV path (e.g. data/term_search_items_table.csv)")
    ap.add_argument(
        "--columns",
        default="ALL",
        help="Comma-separated columns OR ALL. Example: run_id,title,price,seller_username,shipping_cost,shipping_cost_type",
    )
    ap.add_argument("--print-columns", action="store_true", help="Print discovered columns and exit")
    ap.add_argument("--max-scan", type=int, default=200000, help="Max rows to scan for column discovery")
    args = ap.parse_args()

    paths = sorted(glob.glob(args.input))
    if not paths:
        raise SystemExit(f"No files matched: {args.input}")

    all_cols = discover_columns(paths, max_scan=args.max_scan)

    if args.print_columns:
        print("\n".join(all_cols))
        return

    if args.columns.strip().upper() == "ALL":
        cols = all_cols
    else:
        wanted = [c.strip() for c in args.columns.split(",") if c.strip()]
        cols = wanted + [c for c in all_cols if c not in wanted]

    written, dropped = write_csv(paths, args.out, cols)

    print(f"INPUT_FILES={len(paths)}")
    print(f"DISCOVERED_COLUMNS={len(all_cols)}")
    print(f"OUTPUT_COLUMNS={len(cols)}")
    print(f"WROTE_ROWS={written}")
    print(f"DROPPED_EMPTY_ROWS={dropped}")
    print(f"OUTPUT={args.out}")


if __name__ == "__main__":
    main()
