#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_CLASSIFY_TERM_SEARCH_ITEMS_CSV_1F3A9C20
import argparse
import csv
import os
import sys
from typing import Any, Dict, List, Tuple

# Cmd+F: GH_ANCHOR_IMPORTS_TERM_SEARCH_7C2A1D11
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from topps_listing_classifier import classify_title  # noqa: E402
# Reuse your existing player matching + CT formatting + lot detection helpers
# Cmd+F: GH_ANCHOR_REUSE_HELPERS_8B1D2C33
from classify_existing_listings_json import (  # noqa: E402
    load_players_index,
    guess_player_from_title,
    format_ct_name,
    is_lot_title,
)

# Cmd+F: GH_ANCHOR_PLAYER_ALLOWLIST_4F2A1D77
# PLAYER_ALLOWLIST = {
#     "Gage Workman",
#     "Maverick Handley",
#     "Curtis Mead",
#     "Patrick Monteverde",
# }

# Cmd+F: GH_ANCHOR_TO_FLOAT_HELPER_19A2CC40
def _to_float(v: Any) -> float:
    try:
        if v is None:
            return 0.0
        s = str(v).strip()
        if s == "":
            return 0.0
        return float(s)
    except Exception:
        return 0.0

# Cmd+F: GH_ANCHOR_SHOULD_EXCLUDE_ROW_2A7D1C90
def _should_exclude_row(title: str, flags: Dict[str, Any], exclude_lots: bool, exclude_pyc: bool) -> bool:
    if exclude_lots and is_lot_title(title, flags):
        return True
    if exclude_pyc and (bool(flags.get("WF_pick_your_card", False)) or bool(flags.get("CT_pick_your_card", False))):
        return True
    return False

def main() -> None:
    # Cmd+F: GH_ANCHOR_MAIN_TERM_SEARCH_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        required=True,
        help="Input CSV (e.g. data/topps_update_2025/term_search_items_table.csv)",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output CSV (e.g. data/topps_update_2025/term_search_items_table_classified.csv)",
    )

    ap.add_argument("--title-key", default="title", help="Title column name (default: title)")
    ap.add_argument("--price-key", default="price", help="Price column name (default: price)")
    ap.add_argument("--shipping-key", default="shipping_cost", help="Shipping column name (default: shipping_cost)")

    ap.add_argument("--exclude-lots", action="store_true", help="If set, drop lot listings")
    ap.add_argument("--exclude-pick-your-card", action="store_true", help="If set, drop pick-your-card listings")
    ap.add_argument("--max-out", type=int, default=0, help="If >0, stop after writing this many rows")

    # Player matching args (same defaults as your existing script)
    # Cmd+F: GH_ANCHOR_PLAYER_MATCH_ARGS_TERM_SEARCH_6C2A1DA9
    ap.add_argument(
        "--players-csv",
        default="data/topps_update_2025/2025_Topps_Update_player_list.csv",
        help="Players CSV path (default: data/topps_update_2025/2025_Topps_Update_player_list.csv)",
    )
    ap.add_argument("--player-name-col", default="playerName",
                    help="Column in players CSV containing full name (default: playerName)")
    ap.add_argument("--min-player-score", type=float, default=86.0,
                    help="Only keep player_guess if score >= this (default: 86)")
    args = ap.parse_args()

    in_path = (args.input or "").strip()
    out_path = (args.out or "").strip()
    title_key = (args.title_key or "title").strip()
    price_key = (args.price_key or "price").strip()
    shipping_key = (args.shipping_key or "shipping_cost").strip()

    exclude_lots = bool(args.exclude_lots)
    exclude_pyc = bool(args.exclude_pick_your_card)
    max_out = int(args.max_out or 0)

    players_csv = (args.players_csv or "").strip()
    player_name_col = (args.player_name_col or "playerName").strip()
    min_player_score = float(args.min_player_score)

    if not os.path.exists(in_path):
        raise SystemExit(f"Input CSV not found: {in_path}")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Cmd+F: GH_ANCHOR_DISCOVER_CT_KEYS_TERM_SEARCH_4D2A1C90
    tmpl: Dict[str, object] = classify_title("")
    ct_cols: List[str] = [k for k, v in tmpl.items() if isinstance(v, bool) and k.startswith("CT_")]

    # Load players once
    # Cmd+F: GH_ANCHOR_LOAD_PLAYERS_ONCE_TERM_SEARCH_6C2A1DAA
    player_names: List[str] = []
    player_last_index: Dict[str, List[int]] = {}
    if players_csv and os.path.exists(players_csv):
        player_names, player_last_index = load_players_index(players_csv, player_name_col)

    wrote = 0
    read = 0
    kept = 0
    excluded = 0

    # Cmd+F: GH_ANCHOR_STREAMING_CSV_LOOP_88AA10F1
    with open(in_path, "r", encoding="utf-8", newline="") as fin:
        r = csv.DictReader(fin)
        if not r.fieldnames:
            raise SystemExit("Input CSV has no header row")

        # Cmd+F: GH_ANCHOR_OUTPUT_COLUMNS_MINIMAL_9B1D2C34
        out_cols = ["seller_username", "title", "all_in_price", "CT_list", "player_guess"]

        with open(out_path, "w", encoding="utf-8", newline="") as fout:
            w = csv.DictWriter(fout, fieldnames=out_cols)
            w.writeheader()

            for row in r:
                read += 1

                title = (row.get(title_key) or "").strip()
                price = _to_float(row.get(price_key))
                ship = _to_float(row.get(shipping_key))
                all_in = price + ship
                
                # Cmd+F: GH_ANCHOR_DROP_CALCULATED_SHIPPING_3C2A1D12
                ship_type = (row.get("shipping_cost_type") or "").strip().lower()
                if ship_type == "calculated":
                    excluded += 1
                    continue


                flags = classify_title(title)

                if _should_exclude_row(title, flags, exclude_lots, exclude_pyc):
                    excluded += 1
                    continue

                ct_values = {k: bool(flags.get(k, False)) for k in ct_cols}
                ct_any = any(ct_values.values())
                ct_true_names = [format_ct_name(k) for k, v in ct_values.items() if v]
                ct_list = ", ".join(ct_true_names)

                player_guess = ""
                player_score = 0.0
                player_window = ""
                if player_names and player_last_index:
                    g, sc, win = guess_player_from_title(title, player_names, player_last_index)
                    if g and sc >= min_player_score:
                        player_guess = g
                        player_score = sc
                        player_window = win

                # Cmd+F: GH_ANCHOR_FILTER_TO_PLAYER_ALLOWLIST_8A2C1D55
                # if PLAYER_ALLOWLIST and player_guess not in PLAYER_ALLOWLIST:
                #     excluded += 1
                #     continue

                # Cmd+F: GH_ANCHOR_BUILD_MINIMAL_OUT_ROW_7D2A1C91
                out_row = {
                    "seller_username": (row.get("seller_username") or "").strip(),
                    "title": title,
                    "all_in_price": round(all_in, 4),
                    "CT_list": ct_list,
                    "player_guess": player_guess,
                }
                
                w.writerow(out_row)
                wrote += 1
                kept += 1

                if max_out > 0 and wrote >= max_out:
                    break

    print(f"INPUT={in_path}")
    print(f"OUTPUT={out_path}")
    print(f"ROWS_READ={read}")
    print(f"ROWS_EXCLUDED={excluded}")
    print(f"ROWS_WROTE={wrote}")
    print(f"CT_COLS={len(ct_cols)}")
    print(f"EXCLUDE_LOTS={exclude_lots}")
    print(f"EXCLUDE_PICK_YOUR_CARD={exclude_pyc}")

if __name__ == "__main__":
    main()
