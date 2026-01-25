#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_TRAIN_PRICE_MODEL_AUTOGLUON_2C7A1D90
import argparse
import json
import os
import pandas as pd

from autogluon.tabular import TabularPredictor  # pip install autogluon.tabular


def _norm(s: str) -> str:
    return " ".join((s or "").strip().split())


def main() -> None:
    # Cmd+F: GH_ANCHOR_TRAIN_PRICE_MODEL_AUTOGLUON_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()

    ap.add_argument("--data-csv", required=True, help="Main dataset CSV (must include CT + player + target)")
    ap.add_argument("--ct-summary-csv", required=True, help="CT sim summary CSV (CT_list, win_rate)")
    ap.add_argument("--player-summary-csv", required=True, help="Player sim summary CSV (player_name, win_rate)")
    ap.add_argument("--out-dir", required=True, help="Output directory (will be created)")

    ap.add_argument("--ct-col", default="CT_list", help="CT column in data-csv (default: CT_list)")
    ap.add_argument("--player-col", default="player_name", help="Player column in data-csv (default: player_name)")
    ap.add_argument("--target-col", default="market_all_in_price", help="Target column (default: market_all_in_price)")

    ap.add_argument("--presets", default="medium_quality_faster_train", help="AutoGluon presets")
    ap.add_argument("--time-limit", type=int, default=120, help="Training time limit seconds (default: 120)")
    ap.add_argument("--seed", type=int, default=42, help="Split seed (default: 42)")
    ap.add_argument("--test-frac", type=float, default=0.2, help="Test fraction (default: 0.2)")

    args = ap.parse_args()

    data_csv = args.data_csv.strip()
    ct_sum_csv = args.ct_summary_csv.strip()
    pl_sum_csv = args.player_summary_csv.strip()
    out_dir = args.out_dir.strip()

    ct_col = args.ct_col.strip()
    player_col = args.player_col.strip()
    target_col = args.target_col.strip()

    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(data_csv):
        raise SystemExit(f"Missing data-csv: {data_csv}")
    if not os.path.exists(ct_sum_csv):
        raise SystemExit(f"Missing ct-summary-csv: {ct_sum_csv}")
    if not os.path.exists(pl_sum_csv):
        raise SystemExit(f"Missing player-summary-csv: {pl_sum_csv}")

    # -----------------------------
    # Load
    # -----------------------------
    df = pd.read_csv(data_csv)
    ct_df = pd.read_csv(ct_sum_csv)
    pl_df = pd.read_csv(pl_sum_csv)

    for c in [ct_col, player_col, target_col]:
        if c not in df.columns:
            raise SystemExit(f"data-csv missing required column '{c}' (has: {list(df.columns)})")

    if "CT_list" not in ct_df.columns or "win_rate" not in ct_df.columns:
        raise SystemExit("ct-summary-csv must have columns: CT_list, win_rate")

    if "player_name" not in pl_df.columns or "win_rate" not in pl_df.columns:
        raise SystemExit("player-summary-csv must have columns: player_name, win_rate")

    # -----------------------------
    # Build indices from simulation outputs
    # ct_index = CT win_rate
    # player_index = player win_rate
    # -----------------------------
    ct_map = { _norm(r["CT_list"]): float(r["win_rate"]) for _, r in ct_df.iterrows() if str(r.get("CT_list","")).strip() != "" }
    pl_map = { _norm(r["player_name"]): float(r["win_rate"]) for _, r in pl_df.iterrows() if str(r.get("player_name","")).strip() != "" }

    df["_ct_key"] = df[ct_col].astype(str).map(_norm)
    df["_pl_key"] = df[player_col].astype(str).map(_norm)

    df["ct_index"] = df["_ct_key"].map(ct_map)
    df["player_index"] = df["_pl_key"].map(pl_map)

    # Fill missing indices with medians (keeps rows instead of dropping)
    ct_med = float(pd.Series(list(ct_map.values())).median()) if ct_map else 0.5
    pl_med = float(pd.Series(list(pl_map.values())).median()) if pl_map else 0.5
    df["ct_index"] = df["ct_index"].fillna(ct_med)
    df["player_index"] = df["player_index"].fillna(pl_med)

    # Target numeric
    df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
    df = df.dropna(subset=[target_col])

    # Use ONLY the two indices as predictors
    model_df = df[["ct_index", "player_index", target_col]].copy()

    # -----------------------------
    # Train / test split
    # -----------------------------
    model_df = model_df.sample(frac=1.0, random_state=int(args.seed)).reset_index(drop=True)
    n = len(model_df)
    test_n = max(1, int(round(n * float(args.test_frac))))
    train_df = model_df.iloc[:-test_n].copy()
    test_df = model_df.iloc[-test_n:].copy()

    # -----------------------------
    # Train AutoGluon
    # -----------------------------
    model_path = os.path.join(out_dir, "agModels")
    predictor = TabularPredictor(
        label=target_col,
        path=model_path,
        problem_type="regression",
        eval_metric="rmse",
    ).fit(
        train_data=train_df,
        presets=args.presets,
        time_limit=int(args.time_limit),
        verbosity=2,
    )

    # -----------------------------
    # Evaluate + outputs
    # -----------------------------
    metrics = predictor.evaluate(test_df, silent=True)

    leaderboard = predictor.leaderboard(test_df, silent=True)
    leaderboard_path = os.path.join(out_dir, "leaderboard.csv")
    leaderboard.to_csv(leaderboard_path, index=False)

    metrics_path = os.path.join(out_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, sort_keys=True)

    # Predict on full dataset and write alongside identifying columns
    preds = predictor.predict(model_df.drop(columns=[target_col]))
    pred_path = os.path.join(out_dir, "predictions.csv")
    out_preds = model_df.copy()
    out_preds["pred"] = preds
    out_preds.to_csv(pred_path, index=False)

    print(f"DATA={data_csv}")
    print(f"CT_SUMMARY={ct_sum_csv}")
    print(f"PLAYER_SUMMARY={pl_sum_csv}")
    print(f"OUT_DIR={out_dir}")
    print(f"ROWS_USED={len(model_df)} TRAIN={len(train_df)} TEST={len(test_df)}")
    print(f"MODEL_PATH={model_path}")
    print(f"LEADERBOARD={leaderboard_path}")
    print(f"METRICS={metrics_path}")
    print(f"PREDICTIONS={pred_path}")
    print(f"METRICS_OBJ={metrics}")


if __name__ == "__main__":
    main()
