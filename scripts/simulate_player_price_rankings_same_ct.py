#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_SIMULATE_PLAYER_RANKINGS_SAME_CT_7D2A1C90
import argparse
import csv
import os
import random
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Optional


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
    # Cmd+F: GH_ANCHOR_SIM_PLAYER_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input classified CSV (needs player_guess, CT_list, all_in_price)")
    ap.add_argument("--out-summary", required=True, help="Output summary CSV (player rankings)")
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
    # Load rows + build indexes (skip multi-CT_list like "A, B")
    # rows: (player, ct, price, seller, title)
    # by_ct: ct -> list of row indices
    # by_ct_player: (ct, player) -> list of row indices
    # ct_players: ct -> list of distinct players (eligible if >=2)
    # ------------------------------------------------------------
    # Cmd+F: GH_ANCHOR_LOAD_INDEX_PLAYER_SIM_7A1B2C3D
    rows: List[Tuple[str, str, float, str, str]] = []
    by_ct: Dict[str, List[int]] = defaultdict(list)
    by_ct_player: Dict[Tuple[str, str], List[int]] = defaultdict(list)

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

            # Cmd+F: GH_ANCHOR_DROP_MULTI_CT_LIST_PLAYER_SIM_6C2A1D12
            if "," in ct:
                continue

            seller = _norm(row.get("seller_username", ""))
            title = (row.get("title") or "").strip()

            idx = len(rows)
            rows.append((player, ct, float(price), seller, title))
            by_ct[ct].append(idx)
            by_ct_player[(ct, player)].append(idx)

    if len(rows) < 2:
        raise SystemExit("Not enough usable rows (need at least 2 with player + CT + price).")

    # Determine eligible CTs (must have >=2 different players)
    # Cmd+F: GH_ANCHOR_ELIGIBLE_CTS_FOR_PLAYER_SIM_3C2A1D10
    ct_players: Dict[str, List[str]] = {}
    eligible_cts: List[str] = []
    for ct, idxs in by_ct.items():
        players = sorted({rows[i][0] for i in idxs})
        if len(players) >= 2:
            eligible_cts.append(ct)
            ct_players[ct] = players

    if not eligible_cts:
        raise SystemExit("No eligible CT_list groups found (need a CT_list with 2+ different players).")

    # ------------------------------------------------------------
    # Stats per player
    # wins[player], losses[player], played[player], margin_sum[player]
    # margin_sum accumulates (winner_price - loser_price) when that player wins
    # ------------------------------------------------------------
    # Cmd+F: GH_ANCHOR_PLAYER_SIM_STATS_6C2A1D11
    wins: Dict[str, int] = defaultdict(int)
    losses: Dict[str, int] = defaultdict(int)
    played: Dict[str, int] = defaultdict(int)
    margin_sum: Dict[str, float] = defaultdict(float)

    match_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------
    # Simulation:
    # 1) pick random listing A
    # 2) hold CT constant, pick a different player within that CT
    # 3) pick random listing B from that (CT, other_player)
    # 4) compare prices; record winner/loser players
    # ------------------------------------------------------------
    # Cmd+F: GH_ANCHOR_RUN_PLAYER_SIMULATION_9D2A1C90
    attempts = 0
    made = 0
    max_attempts = iters * 50

    while made < iters and attempts < max_attempts:
        attempts += 1

        a_idx = random.randrange(0, len(rows))
        a_player, a_ct, a_price, a_seller, a_title = rows[a_idx]

        players_in_ct = ct_players.get(a_ct)
        if not players_in_ct or len(players_in_ct) < 2:
            continue

        other_players = [p for p in players_in_ct if p != a_player]
        if not other_players:
            continue

        b_player = random.choice(other_players)
        b_pool = by_ct_player.get((a_ct, b_player), [])
        if not b_pool:
            continue

        b_idx = random.choice(b_pool)
        b_player2, b_ct2, b_price, b_seller, b_title = rows[b_idx]
        if b_ct2 != a_ct or b_player2 != b_player:
            continue

        # record played
        played[a_player] += 1
        played[b_player] += 1

        # compare (skip ties)
        if a_price == b_price:
            continue

        if a_price > b_price:
            w_player, l_player = a_player, b_player
            w_price, l_price = a_price, b_price
            w_seller, w_title = a_seller, a_title
            l_seller, l_title = b_seller, b_title
        else:
            w_player, l_player = b_player, a_player
            w_price, l_price = b_price, a_price
            w_seller, w_title = b_seller, b_title
            l_seller, l_title = a_seller, a_title

        wins[w_player] += 1
        losses[l_player] += 1
        margin_sum[w_player] += (w_price - l_price)

        if out_matches and len(match_log) < int(args.max_match_log):
            match_log.append({
                "CT_list": a_ct,
                "winner_player": w_player,
                "loser_player": l_player,
                "winner_price": round(w_price, 4),
                "loser_price": round(l_price, 4),
                "price_diff": round(w_price - l_price, 4),
                "winner_seller": w_seller,
                "winner_title": w_title,
                "loser_seller": l_seller,
                "loser_title": l_title,
            })

        made += 1

    # Build summary
    # Cmd+F: GH_ANCHOR_WRITE_PLAYER_SUMMARY_4D2A1C90
    players_all = sorted(set(list(wins.keys()) + list(losses.keys()) + list(played.keys())))
    summary_rows: List[Dict[str, Any]] = []
    for p in players_all:
        w = int(wins.get(p, 0))
        l = int(losses.get(p, 0))
        denom = w + l
        win_rate = (w / denom) if denom > 0 else 0.0
        avg_margin = (margin_sum.get(p, 0.0) / w) if w > 0 else 0.0
        summary_rows.append({
            "player_name": p,
            "wins": w,
            "losses": l,
            "win_rate": round(win_rate, 6),
            "avg_win_margin": round(avg_margin, 4),
            "played": int(played.get(p, 0)),
        })

    # Rank players: most expensive first (highest win_rate)
    summary_rows.sort(key=lambda x: (x["win_rate"], x["wins"] + x["losses"]), reverse=True)

    with open(out_summary, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["player_name", "wins", "losses", "win_rate", "avg_win_margin", "played"])
        w.writeheader()
        for row in summary_rows:
            w.writerow(row)

    if out_matches:
        with open(out_matches, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "CT_list",
                    "winner_player",
                    "loser_player",
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
    print(f"ELIGIBLE_CT_GROUPS={len(eligible_cts)}")
    print(f"ITERATIONS_REQUESTED={iters}")
    print(f"ITERATIONS_MADE={made}")
    print(f"SUMMARY_OUT={out_summary}")
    if out_matches:
        print(f"MATCHES_OUT={out_matches}")
        print(f"MATCHES_LOGGED={len(match_log)}")


if __name__ == "__main__":
    main()
