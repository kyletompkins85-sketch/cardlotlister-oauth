#!/usr/bin/env python3
"""
Train an AutoGluon regression model: **player_rank** + **card_type_rank** (from pairwise exports)
→ listing **all-in price**. Train / validation / holdout split; lift table on holdout by 20 quantiles
of predicted price (lowest → highest predicted).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd  # noqa: E402

from cardmatch.bowman_pilot_triples import bowman_all_in_price  # noqa: E402
from cardmatch.pairwise_price_rankings import _norm  # noqa: E402


def _load_rank_map(path: str, name_col: str, rank_col: str = "rank") -> Dict[str, int]:
    out: Dict[str, int] = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            k = _norm(row.get(name_col, "") or "")
            if not k:
                continue
            try:
                out[k] = int(float(row.get(rank_col, "")))
            except (TypeError, ValueError):
                continue
    return out


def _load_training_rows(pilot_csv: str) -> List[Dict[str, Any]]:
    """Pilot rows with player, primary card type, all-in price; exclusions applied via bowman triple."""
    from cardmatch.bowman_pilot_triples import bowman_pilot_row_to_triple

    rows_out: List[Dict[str, Any]] = []
    with open(pilot_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = bowman_pilot_row_to_triple(row)
            if t is None:
                continue
            player, ct, price = t
            rows_out.append(
                {
                    "player": player,
                    "card_type": ct,
                    "all_in_price": float(price),
                }
            )
    return rows_out


def _median_rank(rank_map: Dict[str, int]) -> float:
    if not rank_map:
        return 1.0
    vals = sorted(rank_map.values())
    mid = len(vals) // 2
    if len(vals) % 2:
        return float(vals[mid])
    return (vals[mid - 1] + vals[mid]) / 2.0


def main() -> None:
    ap = argparse.ArgumentParser(
        description="AutoGluon: player_rank + card_type_rank → all_in_price (Bowman pilot)."
    )
    ap.add_argument("--pilot-csv", required=True, help="pilot_scored_full.csv")
    ap.add_argument(
        "--player-rankings-csv",
        required=True,
        help="bowman_pairwise_player_rankings_with_listings.csv (columns: rank, player)",
    )
    ap.add_argument(
        "--card-type-rankings-csv",
        required=True,
        help="bowman_pairwise_card_type_rankings_with_listings.csv (columns: rank, card_type)",
    )
    ap.add_argument("--out-dir", required=True, help="Output directory (created)")

    ap.add_argument("--test-frac", type=float, default=0.2, help="Holdout fraction (default: 0.2)")
    ap.add_argument(
        "--val-frac-of-train",
        type=float,
        default=0.2,
        help="Validation fraction of the non-holdout slice (default: 0.2 → 64%% train / 16%% val / 20%% test)",
    )
    ap.add_argument("--seed", type=int, default=42, help="Shuffle seed")
    ap.add_argument("--presets", default="medium_quality_faster_train", help="AutoGluon presets")
    ap.add_argument("--time-limit", type=int, default=120, help="Training time limit (seconds)")
    ap.add_argument("--lift-quantiles", type=int, default=20, help="Holdout lift bins (default: 20)")
    ap.add_argument("--target-col", default="all_in_price", help="Label column name")

    args = ap.parse_args()

    try:
        from autogluon.tabular import TabularPredictor  # type: ignore
    except ImportError as e:
        raise SystemExit(
            "autogluon.tabular is required: pip install autogluon.tabular\n" + str(e)
        ) from e

    out_dir = (args.out_dir or "").strip()
    os.makedirs(out_dir, exist_ok=True)

    raw = _load_training_rows(args.pilot_csv)
    if len(raw) < 10:
        raise SystemExit(f"Too few rows after exclusions: {len(raw)}")

    pl_map = _load_rank_map(args.player_rankings_csv, "player", "rank")
    ct_map = _load_rank_map(args.card_type_rankings_csv, "card_type", "rank")
    pl_med = _median_rank(pl_map)
    ct_med = _median_rank(ct_map)

    rows: List[Dict[str, Any]] = []
    for r in raw:
        pk = _norm(r["player"])
        ck = _norm(r["card_type"])
        rows.append(
            {
                "player_rank": float(pl_map.get(pk, pl_med)),
                "card_type_rank": float(ct_map.get(ck, ct_med)),
                args.target_col: float(r["all_in_price"]),
            }
        )

    df = pd.DataFrame(rows)
    df = df.sample(frac=1.0, random_state=int(args.seed)).reset_index(drop=True)
    n = len(df)
    test_n = max(1, int(round(n * float(args.test_frac))))
    train_val = df.iloc[:-test_n].copy()
    holdout = df.iloc[-test_n:].copy()

    tv_n = len(train_val)
    val_n = max(1, int(round(tv_n * float(args.val_frac_of_train))))
    if tv_n < 3:
        raise SystemExit(f"Not enough rows for train/val/test after split (need >=3, got {tv_n}).")
    if val_n >= tv_n:
        val_n = max(1, tv_n // 2)
    train_df = train_val.iloc[:-val_n].copy()
    val_df = train_val.iloc[-val_n:].copy()
    if len(train_df) < 2:
        raise SystemExit("Train split too small; lower --test-frac or --val-frac-of-train.")

    feature_cols = ["player_rank", "card_type_rank"]
    label = args.target_col

    model_path = os.path.join(out_dir, "agModels")
    predictor = TabularPredictor(
        label=label,
        path=model_path,
        problem_type="regression",
        eval_metric="rmse",
    ).fit(
        train_data=train_df[feature_cols + [label]],
        tuning_data=val_df[feature_cols + [label]],
        presets=(args.presets or "").strip(),
        time_limit=int(args.time_limit),
        verbosity=2,
    )

    metrics_holdout = predictor.evaluate(holdout[feature_cols + [label]], silent=True)
    with open(os.path.join(out_dir, "metrics_holdout.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_holdout, f, indent=2, sort_keys=True)

    leaderboard = predictor.leaderboard(holdout[feature_cols + [label]], silent=True)
    leaderboard.to_csv(os.path.join(out_dir, "leaderboard_holdout.csv"), index=False)

    preds = predictor.predict(holdout[feature_cols])
    holdout_out = holdout.copy()
    holdout_out["predicted_price"] = preds.values if hasattr(preds, "values") else preds

    holdout_out.to_csv(os.path.join(out_dir, "holdout_predictions.csv"), index=False)

    # Lift: 20 quantiles by predicted price on holdout only
    q = max(2, min(int(args.lift_quantiles), len(holdout_out)))
    lift_df = holdout_out[[label, "predicted_price"]].copy()
    lift_df[label] = pd.to_numeric(lift_df[label], errors="coerce")
    lift_df["predicted_price"] = pd.to_numeric(lift_df["predicted_price"], errors="coerce")
    lift_df = lift_df.dropna(subset=[label, "predicted_price"])

    try:
        lift_df["bin"] = pd.qcut(
            lift_df["predicted_price"],
            q=q,
            labels=False,
            duplicates="drop",
        )
    except ValueError:
        lift_df["bin"] = 0

    lift_df["bin"] = lift_df["bin"].astype(int)

    lift_table = (
        lift_df.groupby("bin", as_index=False)
        .agg(
            n=("predicted_price", "size"),
            mean_predicted=("predicted_price", "mean"),
            mean_observed=(label, "mean"),
            min_predicted=("predicted_price", "min"),
            max_predicted=("predicted_price", "max"),
        )
        .sort_values("bin")
        .reset_index(drop=True)
    )
    lift_table["quantile_bin"] = lift_table["bin"] + 1
    lift_table = lift_table.drop(columns=["bin"])

    lift_path = os.path.join(out_dir, "lift_table_holdout.csv")
    lift_table.to_csv(lift_path, index=False)

    meta = {
        "rows_total": n,
        "rows_train": len(train_df),
        "rows_val": len(val_df),
        "rows_holdout": len(holdout),
        "predictors": feature_cols,
        "target": label,
        "lift_quantiles_requested": q,
        "lift_bins_written": int(len(lift_table)),
    }
    with open(os.path.join(out_dir, "run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)

    # Optional matplotlib chart
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(8, 5))
        x = lift_table["quantile_bin"]
        plt.plot(x, lift_table["mean_predicted"], marker="o", label="Mean predicted (holdout)")
        plt.plot(x, lift_table["mean_observed"], marker="o", label="Mean observed (holdout)")
        plt.xlabel("Bin by predicted price (1 = lowest predicted, 20 = highest)")
        plt.ylabel("Price")
        plt.title("Holdout lift: observed vs predicted by prediction quantile")
        plt.legend(loc="best")
        plt.tight_layout()
        png_path = os.path.join(out_dir, "lift_chart_holdout.png")
        plt.savefig(png_path, dpi=160)
        plt.close(fig)
        print(f"LIFT_CHART={png_path}")
    except Exception as e:
        print(f"(lift chart skipped: {e})")

    print(f"LIFT_TABLE={lift_path}")
    print(f"OUT_DIR={out_dir}")
    print(f"ROWS train={len(train_df)} val={len(val_df)} holdout={len(holdout)}")
    print(f"METRICS_HOLDOUT={os.path.join(out_dir, 'metrics_holdout.json')}")


if __name__ == "__main__":
    main()
