#!/usr/bin/env python3
"""Write pairwise Monte Carlo ranking CSVs with listing_count and avg_listing_price (data/topps_update_2025/)."""
import argparse
import csv
import os
import sys
from typing import List

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cardmatch.card_type import row_excluded_from_listing_counts  # noqa: E402
from cardmatch.pairwise_price_rankings import (  # noqa: E402
    SimRow,
    _norm,
    _to_float,
    aggregate_listing_count_and_avg_price_by_card_type,
    aggregate_listing_count_and_avg_price_by_player,
    build_ranking_export_rows,
    run_pairwise_monte_carlo_rankings,
)

_EXPORT_FIELDS_CT = [
    "rank",
    "CT_list",
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
    "player_name",
    "win_rate",
    "wins",
    "losses",
    "avg_win_margin",
    "pairwise_duels_played",
    "listing_count",
    "avg_listing_price",
]


def _load_sim_rows(
    in_path: str,
    player_col: str,
    ct_col: str,
    price_col: str,
) -> List[SimRow]:
    rows: List[SimRow] = []
    with open(in_path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit("Input CSV has no header row")
        for row in r:
            player = _norm(row.get(player_col, ""))
            ct = _norm(row.get(ct_col, ""))
            if "," in ct:
                continue
            price = _to_float(row.get(price_col))
            if not player or not ct or price is None:
                continue
            if row_excluded_from_listing_counts(row, ct):
                continue
            seller = _norm(row.get("seller_username", ""))
            title = (row.get("title") or "").strip()
            rows.append((player, ct, float(price), seller, title))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Run both pairwise simulations once, merge per-entity listing counts and mean all-in price, "
            "and write two ranked CSVs (rank 1 = highest win_rate)."
        )
    )
    ap.add_argument("--input", required=True, help="Classified market CSV (player_guess, CT_list, all_in_price, …)")
    ap.add_argument(
        "--out-dir",
        default="data/topps_update_2025",
        help="Output directory (default: data/topps_update_2025)",
    )
    ap.add_argument(
        "--stem",
        default="",
        help="Output filename stem (default: input basename without .csv)",
    )
    ap.add_argument("--iterations", type=int, default=50000, help="Pairwise duels per simulation (default: 50000)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    ap.add_argument("--player-col", default="player_guess", help="Player column (default: player_guess)")
    ap.add_argument("--ct-col", default="CT_list", help="Card type column (default: CT_list)")
    ap.add_argument("--price-col", default="all_in_price", help="All-in price column (default: all_in_price)")
    args = ap.parse_args()

    in_path = (args.input or "").strip()
    out_dir = (args.out_dir or "").strip() or "data/topps_update_2025"
    stem = (args.stem or "").strip()
    if not stem:
        stem = os.path.splitext(os.path.basename(in_path))[0]

    iters = max(1, int(args.iterations))
    seed = int(args.seed)
    player_col = (args.player_col or "player_guess").strip()
    ct_col = (args.ct_col or "CT_list").strip()
    price_col = (args.price_col or "all_in_price").strip()

    if not os.path.exists(in_path):
        raise SystemExit(f"Input CSV not found: {in_path}")
    os.makedirs(out_dir, exist_ok=True)

    sim_rows = _load_sim_rows(in_path, player_col, ct_col, price_col)
    if len(sim_rows) < 2:
        raise SystemExit("Not enough usable rows (need at least 2 with player + CT + price).")

    try:
        bundle = run_pairwise_monte_carlo_rankings(sim_rows, iterations=iters, seed=seed, max_match_log=0)
    except ValueError as e:
        raise SystemExit(str(e))

    by_player = dict(aggregate_listing_count_and_avg_price_by_player(sim_rows))
    by_ct = dict(aggregate_listing_count_and_avg_price_by_card_type(sim_rows))

    ct_rows = build_ranking_export_rows(
        bundle.same_player_card_types.stats,
        by_ct,
        name_field="CT_list",
        descending_win_rate=True,
    )
    pl_rows = build_ranking_export_rows(
        bundle.same_card_type_players.stats,
        by_player,
        name_field="player_name",
        descending_win_rate=True,
    )

    out_ct = os.path.join(out_dir, f"{stem}_pairwise_card_type_rankings_with_listings.csv")
    out_pl = os.path.join(out_dir, f"{stem}_pairwise_player_rankings_with_listings.csv")

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

    print(f"Wrote {out_ct} ({len(ct_rows)} rows)")
    print(f"Wrote {out_pl} ({len(pl_rows)} rows)")


if __name__ == "__main__":
    main()
