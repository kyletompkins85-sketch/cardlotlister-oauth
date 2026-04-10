#!/usr/bin/env python3
"""
Train an AutoGluon regression model: **player_rank**, **card_type_rank**, **serial_scarcity**,
**autograph** → listing **all-in price**. Train / validation / holdout split; lift table on holdout
by quantiles of predicted price. Optional **--baseline-model-dir** for a comparison lift chart on
the same holdout (bins by baseline predicted quantiles).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import tempfile
from typing import Any, Dict, List

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pandas as pd  # noqa: E402

from cardmatch.bowman_pilot_triples import bowman_pilot_row_to_training_row  # noqa: E402
from cardmatch.pairwise_price_rankings import _norm  # noqa: E402
from cardmatch.serial_scarcity import serial_scarcity_from_flags  # noqa: E402
from cardmatch.taxonomy import flags_for_title  # noqa: E402


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
    """Pilot rows with player, card type, all-in price, title; exclusions via bowman triple."""
    rows_out: List[Dict[str, Any]] = []
    with open(pilot_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = bowman_pilot_row_to_training_row(row)
            if t is None:
                continue
            rows_out.append(t)
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


def _lift_table_compare_by_disagreement(
    df: pd.DataFrame,
    label_col: str,
    pred_baseline_col: str,
    pred_updated_col: str,
    q_bins: int,
) -> pd.DataFrame:
    """
    Bin holdout rows by quantiles of **model disagreement** ``updated - baseline`` (sum-rebased preds).

    ``pd.qcut`` uses ascending ``delta``: smallest ``delta`` = old model furthest **above** new;
    largest ``delta`` = old furthest **below** new.

    ``quantile_bin`` is reversed for plotting left → right: **1** = largest ``delta`` (old most below
    new), **q** = smallest ``delta`` (old most above new).
    """
    cols = [label_col, pred_baseline_col, pred_updated_col]
    d = df[cols].dropna()
    if len(d) < 2:
        return pd.DataFrame()
    q = max(2, min(int(q_bins), len(d)))
    d = d.copy()
    pu = pd.to_numeric(d[pred_updated_col], errors="coerce")
    pb = pd.to_numeric(d[pred_baseline_col], errors="coerce")
    d["_delta"] = pu - pb
    try:
        d["_bin"] = pd.qcut(d["_delta"], q=q, labels=False, duplicates="drop")
    except ValueError:
        d["_bin"] = 0
    d["_bin"] = d["_bin"].astype(int)
    lift_table = (
        d.groupby("_bin", as_index=False)
        .agg(
            n=("_delta", "size"),
            mean_pred_baseline=(pred_baseline_col, "mean"),
            mean_pred_updated=(pred_updated_col, "mean"),
            mean_observed=(label_col, "mean"),
            mean_delta=("_delta", "mean"),
            min_delta=("_delta", "min"),
            max_delta=("_delta", "max"),
        )
        .reset_index(drop=True)
    )
    max_bin = int(lift_table["_bin"].max())
    lift_table["quantile_bin"] = max_bin - lift_table["_bin"] + 1
    lift_table = lift_table.sort_values("quantile_bin", ascending=True).reset_index(drop=True)
    return lift_table.drop(columns=["_bin"])


def _add_sum_rebased_prediction_columns(
    df: pd.DataFrame,
    label_col: str,
    pred_cols: List[str],
) -> tuple[pd.DataFrame, Dict[str, float]]:
    """
    For each prediction column, multiply by ``sum(observed) / sum(pred)`` on rows where both are
    finite so **column sums match** ``sum(observed)`` on that row set.

    New columns: ``{col}_sum_rebased`` (e.g. ``predicted_price_sum_rebased``).
    """
    out = df.copy()
    obs = pd.to_numeric(out[label_col], errors="coerce")
    scales: Dict[str, float] = {}
    for c in pred_cols:
        if c not in out.columns:
            continue
        p = pd.to_numeric(out[c], errors="coerce")
        m = obs.notna() & p.notna()
        if not m.any():
            scales[c] = 1.0
            out[f"{c}_sum_rebased"] = p
            continue
        s_obs = float(obs.loc[m].sum())
        s_p = float(p.loc[m].sum())
        if abs(s_p) < 1e-12:
            scale = 1.0
        else:
            scale = s_obs / s_p
        scales[c] = float(scale)
        out[f"{c}_sum_rebased"] = p * scale
    return out, scales


def _rebase_compare_lift_to_observed(lift_table: pd.DataFrame) -> pd.DataFrame:
    """
    Per-bin ratios to **mean_observed** so the observed series is 1.0 and preds are pred/observed.
    Expects **sum-rebased** prediction means in ``mean_pred_*`` (holdout column sums already match).
    Adds ``ratio_observed``, ``ratio_pred_baseline``, ``ratio_pred_updated``.
    """
    out = lift_table.copy()
    denom = pd.to_numeric(out["mean_observed"], errors="coerce")
    denom = denom.mask(denom.abs() <= 1e-12)  # avoid divide-by-zero → NaN
    out["ratio_observed"] = 1.0
    out["ratio_pred_baseline"] = pd.to_numeric(out["mean_pred_baseline"], errors="coerce") / denom
    out["ratio_pred_updated"] = pd.to_numeric(out["mean_pred_updated"], errors="coerce") / denom
    return out


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


def _save_lift_comparison_chart(
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
    fig = plt.figure(figsize=(9, 5))
    x = lift_table["quantile_bin"]
    # Preds are sum-rebased on full holdout; ratios are per-bin mean pred / mean observed.
    plt.plot(x, lift_table["ratio_observed"], marker="o", label="Observed (rebased = 1.0)")
    plt.plot(x, lift_table["ratio_pred_baseline"], marker="o", label="Baseline pred ÷ observed")
    plt.plot(x, lift_table["ratio_pred_updated"], marker="o", label="Updated pred ÷ observed")
    plt.xlabel(xlabel)
    plt.ylabel("Ratio to bin mean observed")
    plt.title(title)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="AutoGluon: ranks + serial_scarcity + autograph → all_in_price (Bowman pilot)."
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
    ap.add_argument(
        "--baseline-model-dir",
        default="",
        help="Optional path to prior AutoGluon agModels folder for holdout comparison lift chart",
    )
    ap.add_argument(
        "--features",
        choices=("full", "ranks_only"),
        default="full",
        help="full: ranks + serial_scarcity + autograph; ranks_only: pairwise ranks only (for a 2-feature baseline)",
    )

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

    ranks_only = args.features == "ranks_only"
    rows: List[Dict[str, Any]] = []
    for r in raw:
        pk = _norm(r["player"])
        ck = _norm(r["card_type"])
        row: Dict[str, Any] = {
            "player_rank": float(pl_map.get(pk, pl_med)),
            "card_type_rank": float(ct_map.get(ck, ct_med)),
            args.target_col: float(r["all_in_price"]),
        }
        if not ranks_only:
            flags = flags_for_title(r.get("title") or "")
            ss, _numbered = serial_scarcity_from_flags(flags)
            row["serial_scarcity"] = ss
            row["autograph"] = 1.0 if flags.get("WF_auto") else 0.0
        rows.append(row)

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

    if ranks_only:
        feature_cols = ["player_rank", "card_type_rank"]
    else:
        ss_med = train_df["serial_scarcity"].median()
        if pd.isna(ss_med):
            ss_med = (
                float(df["serial_scarcity"].dropna().median())
                if df["serial_scarcity"].notna().any()
                else 0.0
            )
        for part in (train_df, val_df, holdout):
            part["serial_scarcity"] = pd.to_numeric(part["serial_scarcity"], errors="coerce").fillna(
                float(ss_med)
            )
        feature_cols = ["player_rank", "card_type_rank", "serial_scarcity", "autograph"]
    label = args.target_col

    model_path = os.path.join(out_dir, "agModels")
    baseline_dir = (args.baseline_model_dir or "").strip()
    baseline_predictor = None
    if baseline_dir:
        base_path = os.path.abspath(baseline_dir)
        if not os.path.isdir(base_path):
            raise SystemExit(f"--baseline-model-dir is not a directory: {base_path}")
        # ``.fit()`` writes to ``model_path``; if baseline is the same folder, copy first so load
        # stays valid after overwrite (predictors may re-read artifacts from disk).
        if os.path.normpath(base_path) == os.path.normpath(os.path.abspath(model_path)):
            snap_parent = tempfile.mkdtemp(prefix="agbaseline_")
            baseline_snapdir = os.path.join(snap_parent, "agModels")
            shutil.copytree(base_path, baseline_snapdir)
            base_path = baseline_snapdir
        baseline_predictor = TabularPredictor.load(base_path)

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

    if baseline_predictor is not None:
        base_feats = ["player_rank", "card_type_rank"]
        bp = baseline_predictor.predict(holdout[base_feats])
        holdout_out["predicted_price_baseline"] = bp.values if hasattr(bp, "values") else bp

    holdout_out[label] = pd.to_numeric(holdout_out[label], errors="coerce")
    holdout_out["predicted_price"] = pd.to_numeric(holdout_out["predicted_price"], errors="coerce")
    if baseline_predictor is not None:
        holdout_out["predicted_price_baseline"] = pd.to_numeric(
            holdout_out["predicted_price_baseline"], errors="coerce"
        )

    pred_cols_for_sum: List[str] = ["predicted_price"]
    if "predicted_price_baseline" in holdout_out.columns:
        pred_cols_for_sum.append("predicted_price_baseline")
    holdout_out, sum_rebase_scales = _add_sum_rebased_prediction_columns(
        holdout_out, label, pred_cols_for_sum
    )

    # Per-row bin (1..20) from sum-rebased predicted-price quantiles (rank order unchanged vs raw)
    q = max(
        2,
        min(
            int(args.lift_quantiles),
            len(holdout_out.dropna(subset=[label, "predicted_price_sum_rebased"])),
        ),
    )
    ho_valid = holdout_out.dropna(subset=[label, "predicted_price_sum_rebased"]).copy()
    try:
        ho_valid["quantile_bin"] = (
            pd.qcut(ho_valid["predicted_price_sum_rebased"], q=q, labels=False, duplicates="drop").astype(int)
            + 1
        )
    except ValueError:
        ho_valid["quantile_bin"] = 1
    holdout_out = holdout_out.join(ho_valid[["quantile_bin"]], how="left")

    holdout_out.to_csv(os.path.join(out_dir, "holdout_predictions.csv"), index=False)

    ho_pred = holdout_out.dropna(subset=[label, "predicted_price_sum_rebased"])

    # Full holdout lift (20 bins); predictions sum-rebased to match holdout sum(observed)
    lift_table = _lift_table_from_predictions(ho_pred, label, "predicted_price_sum_rebased", q)
    lift_path = os.path.join(out_dir, "lift_table_holdout.csv")
    lift_table.to_csv(lift_path, index=False)

    # Sub-holdout lifts: drop top predicted-quantile rows, then re-quantile remainder
    lift_variants = [
        ("ex20", "Exclude original bin 20 only", 19, lambda d: d["quantile_bin"] <= 19),
        ("ex19_20", "Exclude original bins 19–20", 18, lambda d: d["quantile_bin"] <= 18),
        ("ex18_19_20", "Exclude original bins 18–20", 17, lambda d: d["quantile_bin"] <= 17),
    ]

    meta_extra: Dict[str, Any] = {}
    if baseline_predictor is not None:
        ho_cmp = holdout_out.dropna(
            subset=[
                label,
                "predicted_price_sum_rebased",
                "predicted_price_baseline_sum_rebased",
            ]
        )
        q_cmp = max(2, min(int(args.lift_quantiles), len(ho_cmp)))
        lift_compare = _lift_table_compare_by_disagreement(
            ho_cmp,
            label,
            "predicted_price_baseline_sum_rebased",
            "predicted_price_sum_rebased",
            q_cmp,
        )
        lift_compare = _rebase_compare_lift_to_observed(lift_compare)
        cmp_csv = os.path.join(out_dir, "lift_table_holdout_compare_baseline.csv")
        lift_compare.to_csv(cmp_csv, index=False)
        meta_extra["lift_compare_baseline_bins_written"] = int(len(lift_compare))
        meta_extra["lift_compare_baseline_csv"] = cmp_csv
        meta_extra["lift_compare_binning"] = "disagreement_updated_minus_baseline"
        try:
            _save_lift_comparison_chart(
                lift_compare,
                os.path.join(out_dir, "lift_chart_holdout_compare_baseline.png"),
                title=(
                    "Holdout: baseline vs updated (sum-rebased; ratio to bin mean observed; "
                    "bins by model disagreement)"
                ),
                xlabel=(
                    f"Bin by disagreement updated−baseline (1 = old most below new; "
                    f"{len(lift_compare)} bins; right = old most above new)"
                ),
            )
            print(f"LIFT_CHART_COMPARE={os.path.join(out_dir, 'lift_chart_holdout_compare_baseline.png')}")
        except Exception as e:
            print(f"(comparison lift chart skipped: {e})")
        print(f"LIFT_TABLE_COMPARE={cmp_csv}")

    for suffix, desc, q_rebin, mask_fn in lift_variants:
        sub = ho_pred.dropna(subset=["quantile_bin"])
        sub = sub.loc[mask_fn(sub)].copy()
        lt = _lift_table_from_predictions(sub, label, "predicted_price_sum_rebased", q_rebin)
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
        "sum_rebase_scales": sum_rebase_scales,
        **meta_extra,
    }
    with open(os.path.join(out_dir, "run_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)

    try:
        _save_lift_chart(
            lift_table,
            os.path.join(out_dir, "lift_chart_holdout.png"),
            title="Holdout lift: sum-rebased predicted vs observed (all quantiles)",
            xlabel="Bin by sum-rebased predicted price (1 = lowest, 20 = highest)",
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
