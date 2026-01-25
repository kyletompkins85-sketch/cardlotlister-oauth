#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_TRIM_MARKET_TO_DAD_PAIRS_7B3A1C20
import argparse
import csv
import os
from typing import Dict, Iterable, Set, Tuple


def _norm(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _load_pairs(path: str, ct_col: str, player_col: str) -> Set[Tuple[str, str]]:
    pairs: Set[Tuple[str, str]] = set()
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit(f"Dad CSV has no header row: {path}")
        for row in r:
            ct = _norm(row.get(ct_col, ""))
            pl = _norm(row.get(player_col, ""))
            if not ct or not pl:
                continue
            pairs.add((ct, pl))
    return pairs


def _iter_filtered_rows(
    market_path: str,
    pairs: Set[Tuple[str, str]],
    ct_col: str,
    player_col: str,
) -> Iterable[Dict[str, str]]:
    with open(market_path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit(f"Market CSV has no header row: {market_path}")

        for row in r:
            ct = _norm(row.get(ct_col, ""))
            pl = _norm(row.get(player_col, ""))
            if not ct or not pl:
                continue
            if (ct, pl) in pairs:
                yield row


def main() -> None:
    # Cmd+F: GH_ANCHOR_TRIM_MARKET_TO_DAD_PAIRS_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument("--dad-csv", required=True, help="Dad classified CSV (has CT_list + player_guess)")
    ap.add_argument("--market-csv", required=True, help="Market classified CSV to trim")
    ap.add_argument("--out", required=True, help="Output trimmed CSV")

    ap.add_argument("--dad-ct-col", default="CT_list", help="Dad CT column (default: CT_list)")
    ap.add_argument("--dad-player-col", default="player_guess", help="Dad player column (default: player_guess)")
    ap.add_argument("--market-ct-col", default="CT_list", help="Market CT column (default: CT_list)")
    ap.add_argument("--market-player-col", default="player_guess", help="Market player column (default: player_guess)")
    args = ap.parse_args()

    dad_csv = (args.dad_csv or "").strip()
    market_csv = (args.market_csv or "").strip()
    out_path = (args.out or "").strip()

    if not os.path.exists(dad_csv):
        raise SystemExit(f"Dad CSV not found: {dad_csv}")
    if not os.path.exists(market_csv):
        raise SystemExit(f"Market CSV not found: {market_csv}")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Load the join keys from dad
    pairs = _load_pairs(dad_csv, args.dad_ct_col, args.dad_player_col)
    if not pairs:
        raise SystemExit("No (CT_list, player) pairs found in dad CSV (check column names / content).")

    # Determine output header from market file
    with open(market_csv, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit("Market CSV has no header row")
        out_cols = list(r.fieldnames)

        # Cmd+F: GH_ANCHOR_SORT_TRIMMED_OUTPUT_2C7A1D21
    rows = list(_iter_filtered_rows(market_csv, pairs, args.market_ct_col, args.market_player_col))

    def _sort_key(row: Dict[str, str]) -> Tuple[str, str]:
        pl = _norm(row.get(args.market_player_col, ""))
        ct = _norm(row.get(args.market_ct_col, ""))
        return (pl, ct)

    rows.sort(key=_sort_key)

    wrote = 0
    with open(out_path, "w", encoding="utf-8", newline="") as fout:
        w = csv.DictWriter(fout, fieldnames=out_cols)
        w.writeheader()
        for row in rows:
            w.writerow(row)
            wrote += 1

    print(f"DAD_CSV={dad_csv}")
    print(f"MARKET_CSV={market_csv}")
    print(f"OUT={out_path}")
    print(f"PAIRS={len(pairs)}")
    print(f"WROTE={wrote}")


if __name__ == "__main__":
    main()
