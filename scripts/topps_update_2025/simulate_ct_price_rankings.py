#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_SIMULATE_CT_PRICE_RANKINGS_2D7A1C90
"""CLI for Monte Carlo card-type rankings (same player, different CT). Core: cardmatch.pairwise_price_rankings."""
import argparse
import csv
import os
import sys
from typing import List

# Repo root on path for `python3 scripts/...` from repo root
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cardmatch.card_type import row_excluded_from_listing_counts  # noqa: E402
from cardmatch.pairwise_price_rankings import (  # noqa: E402
    SimRow,
    _norm,
    _to_float,
    run_monte_carlo_card_type_rankings_same_player,
)


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input classified CSV (market universe)")
    ap.add_argument("--out-summary", required=True, help="Output summary CSV")
    ap.add_argument("--out-matches", default="", help="Optional: write sampled matches CSV (blank = skip)")

    ap.add_argument("--iterations", type=int, default=50000, help="Number of simulated matchups (default: 50000)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")

    ap.add_argument("--player-col", default="player_guess", help="Player column (default: player_guess)")
    ap.add_argument("--ct-col", default="CT_list", help="Card type column (default: CT_list)")
    ap.add_argument("--price-col", default="all_in_price", help="All-in price column (default: all_in_price)")

    ap.add_argument("--max-match-log", type=int, default=2000, help="Max rows to write to out-matches if enabled")
    args = ap.parse_args()

    in_path = (args.input or "").strip()
    out_summary = (args.out_summary or "").strip()
    out_matches = (args.out_matches or "").strip()

    iters = max(1, int(args.iterations))
    seed = int(args.seed)

    player_col = (args.player_col or "player_guess").strip()
    ct_col = (args.ct_col or "CT_list").strip()
    price_col = (args.price_col or "all_in_price").strip()

    if not os.path.exists(in_path):
        raise SystemExit(f"Input CSV not found: {in_path}")
    os.makedirs(os.path.dirname(out_summary) or ".", exist_ok=True)
    if out_matches:
        os.makedirs(os.path.dirname(out_matches) or ".", exist_ok=True)

    sim_rows = _load_sim_rows(in_path, player_col, ct_col, price_col)
    if len(sim_rows) < 2:
        raise SystemExit("Not enough usable rows (need at least 2 with player + CT + price).")

    try:
        result = run_monte_carlo_card_type_rankings_same_player(
            sim_rows,
            iterations=iters,
            seed=seed,
            max_match_log=int(args.max_match_log) if out_matches else 0,
        )
    except ValueError as e:
        raise SystemExit(str(e))

    with open(out_summary, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["CT_list", "wins", "losses", "win_rate", "avg_win_margin", "played"])
        w.writeheader()
        for s in result.stats:
            w.writerow(
                {
                    "CT_list": s.name,
                    "wins": s.wins,
                    "losses": s.losses,
                    "win_rate": s.win_rate,
                    "avg_win_margin": s.avg_win_margin,
                    "played": s.played,
                }
            )

    if out_matches:
        with open(out_matches, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "player_name",
                    "winner_ct",
                    "loser_ct",
                    "winner_price",
                    "loser_price",
                    "price_diff",
                    "winner_seller",
                    "winner_title",
                    "loser_seller",
                    "loser_title",
                ],
            )
            w.writeheader()
            for row in result.match_log:
                w.writerow(row)

    print(f"INPUT={in_path}")
    print(f"ROWS_USED={result.rows_used}")
    print(f"ELIGIBLE_PLAYERS={result.eligible_players}")
    print(f"ITERATIONS_REQUESTED={iters}")
    print(f"ITERATIONS_MADE={result.iterations_made}")
    print(f"SUMMARY_OUT={out_summary}")
    if out_matches:
        print(f"MATCHES_OUT={out_matches}")
        print(f"MATCHES_LOGGED={len(result.match_log)}")


if __name__ == "__main__":
    main()
