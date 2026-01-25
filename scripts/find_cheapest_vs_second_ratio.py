#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_CHEAPEST_VS_SECOND_RATIO_7B2A1C90
import argparse
import os
from typing import Any, Optional

import pandas as pd


def _norm(s: Any) -> str:
    return " ".join(str(s or "").strip().split())


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        s = str(v).strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None


def main() -> None:
    # Cmd+F: GH_ANCHOR_CHEAPEST_VS_SECOND_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-csv", required=True, help="Market CSV (classified) to analyze")
    ap.add_argument("--out-csv", required=True, help="Output CSV")

    ap.add_argument("--player-col", default="player_guess", help="Player column (default: player_guess)")
    ap.add_argument("--ct-col", default="CT_list", help="CT_list column (default: CT_list)")
    ap.add_argument("--price-col", default="all_in_price", help="All-in price column (default: all_in_price)")

    ap.add_argument("--drop-multi-ct", default="true", help="true = drop rows whose CT_list contains ',' (default: true)")
    ap.add_argument("--max-out", type=int, default=1000, help="Top N rows to keep after sort (default: 1000; 0=all)")
    args = ap.parse_args()

    in_csv = (args.input_csv or "").strip()
    out_csv = (args.out_csv or "").strip()

    player_col = (args.player_col or "player_guess").strip()
    ct_col = (args.ct_col or "CT_list").strip()
    price_col = (args.price_col or "all_in_price").strip()

    drop_multi_ct = str(args.drop_multi_ct).lower().strip() in ("1", "true", "yes", "y")
    max_out = int(args.max_out)

    if not os.path.exists(in_csv):
        raise SystemExit(f"Missing input-csv: {in_csv}")
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)

    df = pd.read_csv(in_csv)

    for c in [player_col, ct_col, price_col]:
        if c not in df.columns:
            raise SystemExit(f"input-csv missing required column '{c}' (has: {list(df.columns)})")

    # Cmd+F: GH_ANCHOR_FILTER_NONNULL_KEYS_2D7A1C91
    df[player_col] = df[player_col].astype(str)
    df[ct_col] = df[ct_col].astype(str)

    # Require non-empty player + CT_list
    df = df[df[player_col].str.strip() != ""].copy()
    df = df[~df[player_col].str.lower().isin(["nan", "none", "null"])].copy()

    df = df[df[ct_col].str.strip() != ""].copy()
    df = df[~df[ct_col].str.lower().isin(["nan", "none", "null"])].copy()

    if drop_multi_ct:
        df = df[~df[ct_col].astype(str).str.contains(",", na=False)].copy()

    # Price numeric
    df["__price"] = pd.to_numeric(df[price_col], errors="coerce")
    df = df.dropna(subset=["__price"]).copy()

    # Keep optional detail cols if present
    has_seller = "seller_username" in df.columns
    has_title = "title" in df.columns
    has_url = "item_web_url" in df.columns
    has_item_id = "item_id" in df.columns

    # Cmd+F: GH_ANCHOR_GROUP_MIN1_MIN2_9D2A1C90
    out_rows = []
    for (player, ct), g in df.groupby([player_col, ct_col], dropna=False):
        g2 = g.sort_values("__price", ascending=True)
        if len(g2) < 2:
            continue

        r1 = g2.iloc[0]
        r2 = g2.iloc[1]

        p1 = float(r1["__price"])
        p2 = float(r2["__price"])
        if p2 <= 0:
            continue

        ratio = p1 / p2

        out_rows.append({
            "player_name": _norm(player),
            "CT_list": _norm(ct),

            "lowest_price": round(p1, 4),
            "second_lowest_price": round(p2, 4),
            "lowest_to_second_ratio": round(ratio, 6),
            "price_gap": round(p2 - p1, 4),

            "lowest_seller": _norm(r1["seller_username"]) if has_seller else "",
            "lowest_title": (str(r1["title"]) if has_title else ""),
            "lowest_item_web_url": (str(r1["item_web_url"]) if has_url else ""),
            "lowest_item_id": (str(r1["item_id"]) if has_item_id else ""),

            "second_seller": _norm(r2["seller_username"]) if has_seller else "",
            "second_title": (str(r2["title"]) if has_title else ""),
            "second_item_web_url": (str(r2["item_web_url"]) if has_url else ""),
            "second_item_id": (str(r2["item_id"]) if has_item_id else ""),
        })

    out = pd.DataFrame(out_rows)

    # Sort: smallest ratio first (your ask), then bigger absolute gap as tiebreaker
    out = out.sort_values(
        ["lowest_to_second_ratio", "price_gap", "second_lowest_price"],
        ascending=[True, False, False],
    ).reset_index(drop=True)

    if max_out > 0:
        out = out.head(max_out)

    out.to_csv(out_csv, index=False)

    print(f"INPUT={in_csv}")
    print(f"OUT={out_csv}")
    print(f"ROWS_OUT={len(out)}")


if __name__ == "__main__":
    main()
