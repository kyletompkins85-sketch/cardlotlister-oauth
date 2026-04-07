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


def _lift_table_from_predictions(
    df: pd.DataFrame,
    label_col: str,
    pred_col: str,
    q_bins: int,
) -> pd.DataFrame:
    """Aggregate mean predicted / observed by ``q_bins`` quantiles of ``pred_col``."""
    d = df[[label_col, pred_col]].dropna()
    if len(d) < 2:
        return pd.DataFrame()
    q = max(2, min(int(q_bins), len(d)))
    try:
        d = d.copy()
        d["_bin"] = pd.qcut(d[pred_col], q=q, labels=False, duplicates="drop")
    except ValueError:
        d["_bin"] = 0
    d["_bin"] = d["_bin"].astype(int)
    lift_table = (
        d.groupby("_bin", as_index=False)
        .agg(
            n=(pred_col, "size"),
            mean_predicted=(pred_col, "mean"),
            mean_observed=(label_col, "mean"),
            min_predicted=(pred_col, "min"),
            max_predicted=(pred_col, "max"),
        )
        .sort_values("_bin")
        .reset_index(drop=True)
    )
    lift_table["quantile_bin"] = lift_table["_bin"] + 1
    return lift_table.drop(columns=["_bin"])


def _save_lift_chart(
    lift_table: pd.DataFrame,
    path: str,
    *,
    title: str,
    xlabel: str,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if lift_table.empty:
        return
    fig = plt.figure(figsize=(8, 5))
    x = lift_table["quantile_bin"]
    plt.plot(x, lift_table["mean_predicted"], marker="o", label="Mean predicted (holdout)")
    plt.plot(x, lift_table["mean_observed"], marker="o", label="Mean observed (holdout)")
    plt.xlabel(xlabel)
    plt.ylabel("Price")
    plt.title(title)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close(fig)


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

    holdout_out[label] = pd.to_numeric(holdout_out[label], errors="coerce")
    holdout_out["predicted_price"] = pd.to_numeric(holdout_out["predicted_price"], errors="coerce")

    # Per-row bin (1..20) from full holdout predicted-price quantiles (for exclusion views)
    q = max(2, min(int(args.lift_quantiles), len(holdout_out.dropna(subset=[label, "predicted_price"]))))
    ho_valid = holdout_out.dropna(subset=[label, "predicted_price"]).copy()
    try:
        ho_valid["quantile_bin"] = (
            pd.qcut(ho_valid["predicted_price"], q=q, labels=False, duplicates="drop").astype(int) + 1
        )
    except ValueError:
        ho_valid["quantile_bin"] = 1
    holdout_out = holdout_out.join(ho_valid[["quantile_bin"]], how="left")

    holdout_out.to_csv(os.path.join(out_dir, "holdout_predictions.csv"), index=False)

    ho_pred = holdout_out.dropna(subset=[label, "predicted_price"])

    # Full holdout lift (20 bins)
    lift_table = _lift_table_from_predictions(ho_pred, label, "predicted_price", q)
    lift_path = os.path.join(out_dir, "lift_table_holdout.csv")
    lift_table.to_csv(lift_path, index=False)

    # Sub-holdout lifts: drop top predicted-quantile rows, then re-quantile remainder
    lift_variants = [
        ("ex20", "Exclude original bin 20 only", 19, lambda d: d["quantile_bin"] <= 19),
        ("ex19_20", "Exclude original bins 19–20", 18, lambda d: d["quantile_bin"] <= 18),
        ("ex18_19_20", "Exclude original bins 18–20", 17, lambda d: d["quantile_bin"] <= 17),
    ]

    meta_extra: Dict[str, Any] = {}
    for suffix, desc, q_rebin, mask_fn in lift_variants:
        sub = ho_pred.dropna(subset=["quantile_bin"])
        sub = sub.loc[mask_fn(sub)].copy()
        lt = _lift_table_from_predictions(sub, label, "predicted_price", q_rebin)
        tpath = os.path.join(out_dir, f"lift_table_holdout_{suffix}.csv")
        lt.to_csv(tpath, index=False)
        meta_extra[f"lift_{suffix}_rows"] = int(len(sub))
        meta_extra[f"lift_{suffix}_bins_written"] = int(len(lt))
        try:
            _save_lift_chart(
                lt,
                os.path.join(out_dir, f"lift_chart_holdout_{suffix}.png"),
                title=f"Holdout lift ({desc}; {q_rebin} quantiles on remainder)",
                xlabel=f"Bin by predicted price on subset (1 = lowest; {q_rebin} bins)",
            )
            print(f"LIFT_CHART_{suffix.upper()}={os.path.join(out_dir, f'lift_chart_holdout_{suffix}.png')}")
        except Exception as e:
            print(f"(lift chart {suffix} skipped: {e})")
        print(f"LIFT_TABLE_{suffix.upper()}={tpath}")

    meta = {
        "rows_total": n,
        "rows_train": len(train_df),
        "rows_val": len(val_df),
        "rows_holdout": len(holdout),
        "predictors": feature_cols,
        "target": label,
        "lift_quantiles_requested": q,
        "lift_bins_written": int(len(lift_table)),
        **meta_extra,
    }
    with open(os.path.join(out_dir, "run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)

    try:
        _save_lift_chart(
            lift_table,
            os.path.join(out_dir, "lift_chart_holdout.png"),
            title="Holdout lift: full holdout (all prediction quantiles)",
            xlabel="Bin by predicted price (1 = lowest predicted, 20 = highest)",
        )
        print(f"LIFT_CHART={os.path.join(out_dir, 'lift_chart_holdout.png')}")
    except Exception as e:
        print(f"(lift chart skipped: {e})")

    print(f"LIFT_TABLE={lift_path}")
    print(f"OUT_DIR={out_dir}")
    print(f"ROWS train={len(train_df)} val={len(val_df)} holdout={len(holdout)}")
    print(f"METRICS_HOLDOUT={os.path.join(out_dir, 'metrics_holdout.json')}")


if __name__ == "__main__":
    main()
