#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_SIMULATE_CT_PRICE_RANKINGS_2D7A1C90
import argparse
import csv
import os
import random
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


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
    # Cmd+F: GH_ANCHOR_SIM_MAIN_5F1A3B8D
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

    random.seed(seed)

    # ------------------------------------------------------------
    # Load rows + build indexes:
    # - rows: list of (player, ct, price, seller, title)
    # - by_player: player -> list of row indices
    # - by_player_ct: (player, ct) -> list of row indices
    # ------------------------------------------------------------
    # Cmd+F: GH_ANCHOR_LOAD_AND_INDEX_7A1B2C3D
    rows: List[Tuple[str, str, float, str, str]] = []
    by_player: Dict[str, List[int]] = defaultdict(list)
    by_player_ct: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    with open(in_path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit("Input CSV has no header row")

        for row in r:
            player = _norm(row.get(player_col, ""))
            ct = _norm(row.get(ct_col, ""))
            price = _to_float(row.get(price_col))
            if not player or not ct or price is None:
                continue

            seller = _norm(row.get("seller_username", ""))
            title = (row.get("title") or "").strip()

            idx = len(rows)
            rows.append((player, ct, float(price), seller, title))
            by_player[player].append(idx)
            by_player_ct[(player, ct)].append(idx)

    if len(rows) < 2:
        raise SystemExit("Not enough usable rows (need at least 2 with player + CT + price).")

    # Only players that have >=2 different CT_list values can produce matchups
    # Cmd+F: GH_ANCHOR_ELIGIBLE_PLAYERS_3C2A1D10
    eligible_players: List[str] = []
    player_cts: Dict[str, List[str]] = {}
    for p, idxs in by_player.items():
        cts = sorted({rows[i][1] for i in idxs})
        if len(cts) >= 2:
            eligible_players.append(p)
            player_cts[p] = cts

    if not eligible_players:
        raise SystemExit("No eligible players found (need same player with 2+ different CT_list values).")

    # ------------------------------------------------------------
    # Simulation stats
    # ------------------------------------------------------------
    # wins[ct] = number of wins
    # losses[ct] = number of losses
    # margin_sum[ct] = sum of (winner_price - loser_price) when ct wins
    # played[ct] = total appearances in matchups
    # ------------------------------------------------------------
    # Cmd+F: GH_ANCHOR_SIM_STATS_6C2A1D11
    wins: Dict[str, int] = defaultdict(int)
    losses: Dict[str, int] = defaultdict(int)
    played: Dict[str, int] = defaultdict(int)
    margin_sum: Dict[str, float] = defaultdict(float)

    # Optional match log (audit)
    match_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------
    # Matchup process:
    # 1) pick a random listing A uniformly from all rows
    # 2) pick random listing B with same player but different CT_list
    # 3) compare prices; record winner/loser CT_list
    # If A's player has no other CT options, resample A
    # ------------------------------------------------------------
    # Cmd+F: GH_ANCHOR_RUN_SIMULATION_9D2A1C90
    attempts = 0
    made = 0
    max_attempts = iters * 50  # prevent infinite loops if data is weird

    while made < iters and attempts < max_attempts:
        attempts += 1

        a_idx = random.randrange(0, len(rows))
        a_player, a_ct, a_price, a_seller, a_title = rows[a_idx]

        # If this player isn't eligible, resample
        if a_player not in player_cts:
            continue

        # pick a different CT for the same player
        cts = player_cts[a_player]
        if len(cts) < 2:
            continue

        # choose a CT != a_ct
        other_cts = [c for c in cts if c != a_ct]
        if not other_cts:
            continue

        b_ct = random.choice(other_cts)
        b_pool = by_player_ct.get((a_player, b_ct), [])
        if not b_pool:
            continue

        b_idx = random.choice(b_pool)
        b_player, b_ct2, b_price, b_seller, b_title = rows[b_idx]

        # sanity (should be same player)
        if b_player != a_player or b_ct2 != b_ct:
            continue

        # record played
        played[a_ct] += 1
        played[b_ct] += 1

        # compare
        if a_price == b_price:
            # tie: count as half win/half loss (or skip). We'll SKIP ties to keep it simple.
            continue

        if a_price > b_price:
            w_ct, l_ct = a_ct, b_ct
            w_price, l_price = a_price, b_price
            w_seller, w_title = a_seller, a_title
            l_seller, l_title = b_seller, b_title
        else:
            w_ct, l_ct = b_ct, a_ct
            w_price, l_price = b_price, a_price
            w_seller, w_title = b_seller, b_title
            l_seller, l_title = a_seller, a_title

        wins[w_ct] += 1
        losses[l_ct] += 1
        margin_sum[w_ct] += (w_price - l_price)

        if out_matches and len(match_log) < int(args.max_match_log):
            match_log.append({
                "player_name": a_player,
                "winner_ct": w_ct,
                "loser_ct": l_ct,
                "winner_price": round(w_price, 4),
                "loser_price": round(l_price, 4),
                "price_diff": round(w_price - l_price, 4),
                "winner_seller": w_seller,
                "winner_title": w_title,
                "loser_seller": l_seller,
                "loser_title": l_title,
            })

        made += 1

    # Build summary rows
    # Cmd+F: GH_ANCHOR_WRITE_SUMMARY_4D2A1C90
    summary_rows: List[Dict[str, Any]] = []
    all_cts = sorted(set(list(wins.keys()) + list(losses.keys()) + list(played.keys())))
    for ct in all_cts:
        w = int(wins.get(ct, 0))
        l = int(losses.get(ct, 0))
        p = int(played.get(ct, 0))
        denom = (w + l)
        win_rate = (w / denom) if denom > 0 else 0.0
        avg_margin = (margin_sum.get(ct, 0.0) / w) if w > 0 else 0.0
        summary_rows.append({
            "CT_list": ct,
            "wins": w,
            "losses": l,
            "win_rate": round(win_rate, 6),
            "avg_win_margin": round(avg_margin, 4),
            "played": p,
        })

    # Sort spectrum: win_rate ascending -> descending (most expensive on top)
    summary_rows.sort(key=lambda x: (x["win_rate"], x["wins"] + x["losses"]))

    # Write summary
    with open(out_summary, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["CT_list", "wins", "losses", "win_rate", "avg_win_margin", "played"])
        w.writeheader()
        for row in summary_rows:
            w.writerow(row)

    # Write match log (optional)
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
            for row in match_log:
                w.writerow(row)

    print(f"INPUT={in_path}")
    print(f"ROWS_USED={len(rows)}")
    print(f"ELIGIBLE_PLAYERS={len(eligible_players)}")
    print(f"ITERATIONS_REQUESTED={iters}")
    print(f"ITERATIONS_MADE={made}")
    print(f"SUMMARY_OUT={out_summary}")
    if out_matches:
        print(f"MATCHES_OUT={out_matches}")
        print(f"MATCHES_LOGGED={len(match_log)}")


if __name__ == "__main__":
    main()
