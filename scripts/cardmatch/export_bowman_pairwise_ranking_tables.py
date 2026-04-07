#!/usr/bin/env python3
"""
Bowman Draft pilot: pairwise Monte Carlo rankings + listing_count / avg all-in price per player and card type.

Reads ``pilot_scored_full.csv`` (or any pilot-scored CSV with ``pilot_player_guess``, price, shipping,
and classifier columns used by :func:`cardmatch.card_type.row_primary_card_type`). Writes two CSVs next
to the input (or under ``--out-dir``).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import Any, Dict, List

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cardmatch.bowman_pilot_triples import bowman_pilot_rows_to_ranking_triples  # noqa: E402
from cardmatch.pairwise_price_rankings import (  # noqa: E402
    aggregate_listing_count_and_avg_price_by_card_type,
    aggregate_listing_count_and_avg_price_by_player,
    aggregate_listing_count_and_median_price_by_player_for_card_type,
    build_ranking_export_rows,
    listing_triples_to_sim_rows,
    run_pairwise_monte_carlo_rankings,
)

# Canonical primary from ``row_primary_card_type`` for plain paper base (not Black Border, etc.).
_BASE_PAPER_CT = "Base-Paper"

_EXPORT_FIELDS_CT = [
    "rank",
    "card_type",
    "win_rate",
    "wins",
    "losses",
    "avg_win_margin",
    "pairwise_duels_played",
    "listing_count",
    "avg_listing_price",
]
_EXPORT_FIELDS_PLAYER = [
    "rank",
    "player",
    "win_rate",
    "wins",
    "losses",
    "avg_win_margin",
    "pairwise_duels_played",
    "listing_count",
    "avg_listing_price",
    "base_paper_listing_count",
    "median_base_paper_listing_price",
]


def _load_pilot_rows(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit("Input CSV has no header row")
        return list(r)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Bowman pilot scored listings → pairwise card-type and player rankings with "
            "listing_count and mean all-in price (rank 1 = highest win_rate)."
        )
    )
    ap.add_argument("--input", required=True, help="Path to pilot_scored_full.csv (or compatible pilot CSV)")
    ap.add_argument(
        "--out-dir",
        default="",
        help="Output directory (default: same directory as --input)",
    )
    ap.add_argument(
        "--prefix",
        default="bowman",
        help="Output filename prefix (default: bowman) → {prefix}_pairwise_*_rankings_with_listings.csv",
    )
    ap.add_argument(
        "--iterations",
        type=int,
        default=100_000,
        help="Scored pairwise duels for the **player** simulation (default: 100000)",
    )
    ap.add_argument(
        "--card-type-base-iterations",
        type=int,
        default=0,
        help="Phase 1 scored duels for **card-type** simulation (default: 0 = use --iterations)",
    )
    ap.add_argument(
        "--card-type-min-duels-per-type",
        type=int,
        default=500,
        help="After phase 1, boost CTs until each duelable type has at least this many played counts "
        "(default: 500; set 0 to disable phase 2)",
    )
    ap.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    args = ap.parse_args()

    in_path = (args.input or "").strip()
    out_dir = (args.out_dir or "").strip()
    prefix = (args.prefix or "bowman").strip() or "bowman"

    if not os.path.isfile(in_path):
        raise SystemExit(f"Input not found: {in_path}")
    if not out_dir:
        out_dir = os.path.dirname(os.path.abspath(in_path)) or "."
    os.makedirs(out_dir, exist_ok=True)

    pilot_rows = _load_pilot_rows(in_path)
    triples = bowman_pilot_rows_to_ranking_triples(pilot_rows)
    sim_rows = listing_triples_to_sim_rows(triples)
    if len(sim_rows) < 2:
        raise SystemExit(
            "Not enough usable rows after Bowman triple extraction (need 2+ with player, card type, all-in price)."
        )

    iters = max(1, int(args.iterations))
    ct_base = int(args.card_type_base_iterations)
    if ct_base <= 0:
        ct_base = iters
    min_ct = int(args.card_type_min_duels_per_type)
    if min_ct <= 0:
        min_ct = None
    seed = int(args.seed)

    try:
        bundle = run_pairwise_monte_carlo_rankings(
            sim_rows,
            iterations=iters,
            card_type_base_iterations=ct_base,
            card_type_min_duels_per_type=min_ct,
            seed=seed,
            max_match_log=0,
        )
    except ValueError as e:
        raise SystemExit(str(e))

    by_player = dict(aggregate_listing_count_and_avg_price_by_player(sim_rows))
    by_ct = dict(aggregate_listing_count_and_avg_price_by_card_type(sim_rows))

    ct_rows = build_ranking_export_rows(
        bundle.same_player_card_types.stats,
        by_ct,
        name_field="card_type",
        descending_win_rate=True,
    )
    pl_rows = build_ranking_export_rows(
        bundle.same_card_type_players.stats,
        by_player,
        name_field="player",
        descending_win_rate=True,
    )
    by_player_base_paper = dict(
        aggregate_listing_count_and_median_price_by_player_for_card_type(
            sim_rows, card_type=_BASE_PAPER_CT
        )
    )
    for row in pl_rows:
        pname = row["player"]
        lc_bp, med_bp = by_player_base_paper.get(pname, (0, 0.0))
        row["base_paper_listing_count"] = lc_bp
        row["median_base_paper_listing_price"] = round(med_bp, 4) if lc_bp else 0.0

    out_ct = os.path.join(out_dir, f"{prefix}_pairwise_card_type_rankings_with_listings.csv")
    out_pl = os.path.join(out_dir, f"{prefix}_pairwise_player_rankings_with_listings.csv")

    with open(out_ct, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_EXPORT_FIELDS_CT)
        w.writeheader()
        for row in ct_rows:
            w.writerow({k: row[k] for k in _EXPORT_FIELDS_CT})

    with open(out_pl, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_EXPORT_FIELDS_PLAYER)
        w.writeheader()
        for row in pl_rows:
            w.writerow({k: row[k] for k in _EXPORT_FIELDS_PLAYER})

    ct_meta = bundle.same_player_card_types
    print(f"Wrote {out_ct} ({len(ct_rows)} rows)")
    print(f"Wrote {out_pl} ({len(pl_rows)} rows)")
    print(
        f"CT sim: phase1_scored={ct_meta.phase1_scored_duels} phase2_scored={ct_meta.phase2_scored_duels} "
        f"min_duels_per_type={ct_meta.min_duels_per_card_type!r}"
    )


if __name__ == "__main__":
    main()
