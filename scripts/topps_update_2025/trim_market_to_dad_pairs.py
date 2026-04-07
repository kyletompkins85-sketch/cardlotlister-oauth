#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_TRIM_MARKET_TO_DAD_PAIRS_7B3A1C20
import argparse
import csv
import os
from typing import Dict, Iterable, Set, Tuple, Optional

# Cmd+F: GH_ANCHOR_TO_FLOAT_TRIM_1B7A1C90
def _to_float(v: str) -> float:
    try:
        s = (v or "").strip()
        if s == "":
            return 0.0
        return float(s)
    except Exception:
        return 0.0

def _norm(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


# Cmd+F: GH_ANCHOR_LOAD_DAD_PAIR_PRICE_MAP_5C2A1D12
def _load_pair_price_map(
    path: str,
    ct_col: str,
    player_col: str,
    price_col: str,
) -> Dict[Tuple[str, str], float]:
    """
    Returns map: (ct_norm, player_norm) -> our_all_in_price (min across dad rows for that pair)
    """
    m: Dict[Tuple[str, str], float] = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit(f"Dad CSV has no header row: {path}")

        for row in r:
            ct = _norm(row.get(ct_col, ""))
            pl = _norm(row.get(player_col, ""))
            if not ct or not pl:
                continue

            p = _to_float((row.get(price_col) or "").strip())
            key = (ct, pl)

            if key not in m:
                m[key] = p
            else:
                # keep the minimum dad price for that (ct,player) pair
                if p < m[key]:
                    m[key] = p

    return m


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
    ap.add_argument("--dad-price-col", default="all_in_price", help="Dad all-in price column (default: all_in_price)")
    args = ap.parse_args()

    dad_csv = (args.dad_csv or "").strip()
    market_csv = (args.market_csv or "").strip()
    out_path = (args.out or "").strip()

    if not os.path.exists(dad_csv):
        raise SystemExit(f"Dad CSV not found: {dad_csv}")
    if not os.path.exists(market_csv):
        raise SystemExit(f"Market CSV not found: {market_csv}")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Cmd+F: GH_ANCHOR_BUILD_DAD_PAIR_PRICE_MAP_6C2A1D14
    dad_price_map = _load_pair_price_map(dad_csv, args.dad_ct_col, args.dad_player_col, args.dad_price_col)
    if not dad_price_map:
        raise SystemExit("No (CT_list, player) pairs found in dad CSV (check column names / content).")
    pairs = set(dad_price_map.keys())


    # Cmd+F: GH_ANCHOR_OUTPUT_COLS_WITH_OUR_PRICE_7C2A1D15
    out_cols = ["player_name", "CT_list", "our_all_in_price", "market_all_in_price", "seller", "title"]


    # Cmd+F: GH_ANCHOR_SORT_AND_SHAPE_WITH_OUR_PRICE_8C2A1D21
    rows_in = list(_iter_filtered_rows(market_csv, pairs, args.market_ct_col, args.market_player_col))
    
    rows_out = []
    for row in rows_in:
        pl_norm = _norm(row.get(args.market_player_col, "") or "")
        ct_norm = _norm(row.get(args.market_ct_col, "") or "")
        our_price = dad_price_map.get((ct_norm, pl_norm), 0.0)
    
        market_price_raw = (row.get("all_in_price", "") or "").strip()
        market_price = _to_float(market_price_raw)
    
        rows_out.append({
            "player_name": (row.get(args.market_player_col, "") or "").strip(),
            "CT_list": (row.get(args.market_ct_col, "") or "").strip(),
            "our_all_in_price": f"{our_price:.4f}",
            "market_all_in_price": f"{market_price:.4f}",
            "seller": (row.get("seller_username", "") or "").strip(),
            "title": (row.get("title", "") or "").strip(),
        })
    
    def _sort_key(row: Dict[str, str]):
        pl = _norm(row.get("player_name", ""))
        ct = _norm(row.get("CT_list", ""))
        mkt = _to_float(row.get("market_all_in_price", ""))
        return (pl, ct, -mkt)
    
    rows_out.sort(key=_sort_key)
    
    wrote = 0
    with open(out_path, "w", encoding="utf-8", newline="") as fout:
        w = csv.DictWriter(fout, fieldnames=out_cols)
        w.writeheader()
        for row in rows_out:
            w.writerow(row)
            wrote += 1


    print(f"DAD_CSV={dad_csv}")
    print(f"MARKET_CSV={market_csv}")
    print(f"OUT={out_path}")
    print(f"PAIRS={len(pairs)}")
    print(f"DAD_PRICE_MAP={len(dad_price_map)}")
    print(f"WROTE={wrote}")


if __name__ == "__main__":
    main()
