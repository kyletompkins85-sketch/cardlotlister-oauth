#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_SCORE_MARKET_UNDERPRICED_3C2A1D90
import argparse
import json
import os
from typing import Any, Dict, Optional

import pandas as pd
from autogluon.tabular import TabularPredictor


def _norm(s: str) -> str:
    return " ".join((s or "").strip().split())


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
    # Cmd+F: GH_ANCHOR_SCORE_MARKET_UNDERPRICED_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-csv", required=True, help="Market classified CSV (universe)")
    ap.add_argument("--model-path", required=True, help="Path to AutoGluon model dir (the agModels folder)")
    ap.add_argument("--ct-summary-csv", required=True, help="CT sim summary CSV (CT_list, win_rate)")
    ap.add_argument("--player-summary-csv", required=True, help="Player sim summary CSV (player_name, win_rate)")
    ap.add_argument("--out-csv", required=True, help="Output CSV (underpriced rows)")

    ap.add_argument("--ct-col", default="CT_list", help="CT column in input (default: CT_list)")
    ap.add_argument("--player-col", default="player_guess", help="Player column in input (default: player_guess)")
    ap.add_argument("--price-col", default="all_in_price", help="Market all-in price col in input (default: all_in_price)")

    ap.add_argument("--min-diff", type=float, default=0.01, help="Keep rows where (pred - actual) >= this (default: 0.01)")
    ap.add_argument("--drop-multi-ct", default="true", help="true = drop rows whose CT_list contains ',' (default: true)")
    ap.add_argument("--max-out", type=int, default=0, help="0 = no limit; otherwise keep top N underpriced (default: 0)")
    args = ap.parse_args()

    in_csv = (args.input_csv or "").strip()
    model_path = (args.model_path or "").strip()
    ct_sum = (args.ct_summary_csv or "").strip()
    pl_sum = (args.player_summary_csv or "").strip()
    out_csv = (args.out_csv or "").strip()

    ct_col = (args.ct_col or "CT_list").strip()
    player_col = (args.player_col or "player_guess").strip()
    price_col = (args.price_col or "all_in_price").strip()

    min_diff = float(args.min_diff)
    drop_multi_ct = str(args.drop_multi_ct).lower().strip() in ("1", "true", "yes", "y")
    max_out = int(args.max_out)

    if not os.path.exists(in_csv):
        raise SystemExit(f"Missing input-csv: {in_csv}")
    if not os.path.exists(model_path):
        raise SystemExit(f"Missing model-path: {model_path}")
    if not os.path.exists(ct_sum):
        raise SystemExit(f"Missing ct-summary-csv: {ct_sum}")
    if not os.path.exists(pl_sum):
        raise SystemExit(f"Missing player-summary-csv: {pl_sum}")

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)

    # Load model
    predictor = TabularPredictor.load(model_path)

    # Load data + summaries
    df = pd.read_csv(in_csv)
    ct_df = pd.read_csv(ct_sum)
    pl_df = pd.read_csv(pl_sum)

    for c in [ct_col, player_col, price_col]:
        if c not in df.columns:
            raise SystemExit(f"input-csv missing required column '{c}' (has: {list(df.columns)})")
    if "CT_list" not in ct_df.columns or "win_rate" not in ct_df.columns:
        raise SystemExit("ct-summary-csv must have columns: CT_list, win_rate")
    if "player_name" not in pl_df.columns or "win_rate" not in pl_df.columns:
        raise SystemExit("player-summary-csv must have columns: player_name, win_rate")

    # Build index maps
    ct_map: Dict[str, float] = {
        _norm(r["CT_list"]): float(r["win_rate"])
        for _, r in ct_df.iterrows()
        if str(r.get("CT_list", "")).strip() != ""
    }
    pl_map: Dict[str, float] = {
        _norm(r["player_name"]): float(r["win_rate"])
        for _, r in pl_df.iterrows()
        if str(r.get("player_name", "")).strip() != ""
    }

    # Make ct_index + player_index (same as training)
    df["_ct_key"] = df[ct_col].astype(str).map(_norm)
    df["_pl_key"] = df[player_col].astype(str).map(_norm)

    df["ct_index"] = df["_ct_key"].map(ct_map)
    df["player_index"] = df["_pl_key"].map(pl_map)

    ct_med = float(pd.Series(list(ct_map.values())).median()) if ct_map else 0.5
    pl_med = float(pd.Series(list(pl_map.values())).median()) if pl_map else 0.5
    df["ct_index"] = df["ct_index"].fillna(ct_med)
    df["player_index"] = df["player_index"].fillna(pl_med)

    # Actual market price numeric
    df["market_all_in_price"] = pd.to_numeric(df[price_col], errors="coerce")
    df = df.dropna(subset=["market_all_in_price"])

    # Optional: drop multi-CT rows
    if drop_multi_ct:
        df = df[~df[ct_col].astype(str).str.contains(",", na=False)].copy()

    # Score
    feats = df[["ct_index", "player_index"]].copy()
    df["pred_price"] = pd.to_numeric(predictor.predict(feats), errors="coerce")
    df = df.dropna(subset=["pred_price"])

    df["underpriced_by"] = df["pred_price"] - df["market_all_in_price"]
    df = df[df["underpriced_by"] >= min_diff].copy()

    # Output columns (use what exists if present)
    def _get(col: str) -> Any:
        return df[col] if col in df.columns else ""

    out = pd.DataFrame({
        "player_name": _get(player_col),
        "CT_list": _get(ct_col),
        "market_all_in_price": df["market_all_in_price"].round(4),
        "pred_price": df["pred_price"].round(4),
        "underpriced_by": df["underpriced_by"].round(4),
        "seller": _get("seller_username"),
        "title": _get("title"),
        "item_id": _get("item_id"),
        "item_web_url": _get("item_web_url"),
    })

    out = out.sort_values(["underpriced_by"], ascending=False).reset_index(drop=True)
    if max_out and max_out > 0:
        out = out.head(max_out)

    out.to_csv(out_csv, index=False)

    meta = {
        "input_csv": in_csv,
        "model_path": model_path,
        "ct_summary_csv": ct_sum,
        "player_summary_csv": pl_sum,
        "rows_scored": int(len(df)),
        "rows_out": int(len(out)),
        "min_diff": min_diff,
        "drop_multi_ct": drop_multi_ct,
        "max_out": max_out,
    }
    meta_path = os.path.splitext(out_csv)[0] + "_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)

    print(f"INPUT={in_csv}")
    print(f"MODEL={model_path}")
    print(f"OUT={out_csv}")
    print(f"META={meta_path}")
    print(f"ROWS_OUT={len(out)}")


if __name__ == "__main__":
    main()
