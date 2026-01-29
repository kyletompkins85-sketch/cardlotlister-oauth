#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_SIMULATE_PLAYER_RANKINGS_BOWMAN_92A1C7D0
"""
Build player price rankings for a product by simulating head-to-head matchups
while holding CT_list constant.

Inputs (in workflows/product_player_price_rankings/data/<RUN_ID>/):
  - term_search_items_export.csv   (from your Step 02 export)
  - Step 01 summary CSV that contains column 'query' (used to derive player list)
    We auto-detect it in the run folder.

NO EBAY CALLS. Reads local export CSV only.

Outputs (same run folder):
  - player_rankings_simulation.csv
  - player_rankings_simulation_matches_sample.csv  (optional sample)
  - player_rankings_simulation_debug_rows.csv      (optional debug, small)
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# -----------------------------
# Helpers
# -----------------------------

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

def _tokenize(s: str) -> List[str]:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    toks = [t for t in s.split() if t]
    return toks

def _require_run_dir(run_id: str) -> Path:
    workflow_root = Path(__file__).resolve().parent
    run_dir = workflow_root / "data" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir

# -----------------------------
# Import Bowman classifier
# -----------------------------

def _load_bowman_classifier():
    here = Path(__file__).resolve().parent
    if str(here) not in os.sys.path:
        os.sys.path.insert(0, str(here))
    from z10_bowman_listing_classifier import classify_title  # type: ignore
    return classify_title

# -----------------------------
# Player list derivation (from Step 01 summary)
# -----------------------------

def _detect_step01_summary_csv(run_dir: Path) -> Optional[Path]:
    """
    Find a CSV in the run folder with a 'query' column.
    We'll use it to derive the searched player names.
    """
    candidates = sorted(run_dir.glob("*.csv"))
    for p in candidates:
        # skip the export itself
        if p.name == "term_search_items_export.csv":
            continue
        try:
            with p.open("r", encoding="utf-8", newline="") as f:
                r = csv.DictReader(f)
                if r.fieldnames and "query" in r.fieldnames:
                    return p
        except Exception:
            continue
    return None

def _derive_players_from_queries(summary_csv: Path, product_prefix: str) -> List[str]:
    """
    Extract player names from query strings like:
      "2025 Bowman Draft Dylan Crews"
    by removing the prefix.
    """
    prefix = _norm(product_prefix).lower()
    players = []
    with summary_csv.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            q = _norm(row.get("query", ""))
            if not q:
                continue
            ql = q.lower()
            if prefix and ql.startswith(prefix):
                name = _norm(q[len(product_prefix):])
            else:
                # fallback: remove prefix words anywhere
                name = q
                if prefix:
                    name = _norm(re.sub(re.escape(prefix), "", ql, flags=re.IGNORECASE))
            name = _norm(name)
            # basic cleanup
            name = re.sub(r"\s+mlb\s*$", "", name, flags=re.IGNORECASE).strip()
            if name and len(name.split()) >= 2:
                players.append(name)

    # dedupe preserve order
    seen = set()
    out = []
    for p in players:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out

# -----------------------------
# Player matching (title -> best player)
# -----------------------------

def _build_lastname_index(players: List[str]) -> Dict[str, List[str]]:
    idx: Dict[str, List[str]] = defaultdict(list)
    for full in players:
        parts = _tokenize(full)
        if not parts:
            continue
        last = parts[-1]
        idx[last].append(full)
    return idx

def guess_player_from_title(title: str, players: List[str], last_idx: Dict[str, List[str]]) -> Tuple[str, float]:
    """
    Returns (player_name, score). score is a rough heuristic:
      - 100: all name tokens in title
      - 95: first+last present
      - 90: last + first-initial present
      - 80: last present
      - 0: no match
    """
    t_toks = _tokenize(title)
    if not t_toks:
        return "", 0.0
    t_set = set(t_toks)

    # quick candidate discovery by last name
    best_name = ""
    best_score = 0.0

    # scan last names present in title tokens
    last_names_in_title = [ln for ln in last_idx.keys() if ln in t_set]
    if not last_names_in_title:
        return "", 0.0

    for ln in last_names_in_title:
        for full in last_idx.get(ln, []):
            name_toks = _tokenize(full)
            if not name_toks:
                continue
            first = name_toks[0]
            last = name_toks[-1]

            all_in = all(tok in t_set for tok in name_toks)
            if all_in:
                score = 100.0
            elif first in t_set and last in t_set:
                score = 95.0
            else:
                # first initial
                fi = first[:1]
                score = 90.0 if (last in t_set and any(tok == fi for tok in t_set)) else 80.0

            if score > best_score:
                best_score = score
                best_name = full

    return best_name, best_score

# -----------------------------
# Core simulation
# -----------------------------

def simulate(rows: List[Tuple[str, str, float, str, str]],
             iterations: int,
             seed: int,
             max_match_log: int = 2000,
             write_match_log: bool = True) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    rows: (player, ct, price, seller, title)
    Returns: (summary_rows, match_log_rows)
    """
    random.seed(seed)

    by_ct: Dict[str, List[int]] = defaultdict(list)
    by_ct_player: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    for idx, (player, ct, price, seller, title) in enumerate(rows):
        by_ct[ct].append(idx)
        by_ct_player[(ct, player)].append(idx)

    # eligible CTs must have >=2 distinct players
    ct_players: Dict[str, List[str]] = {}
    eligible_cts: List[str] = []
    for ct, idxs in by_ct.items():
        players = sorted({rows[i][0] for i in idxs})
        if len(players) >= 2:
            eligible_cts.append(ct)
            ct_players[ct] = players

    if not eligible_cts:
        raise SystemExit("No eligible CT_list groups found (need CT_list with 2+ different players).")

    wins: Dict[str, int] = defaultdict(int)
    losses: Dict[str, int] = defaultdict(int)
    played: Dict[str, int] = defaultdict(int)
    margin_sum: Dict[str, float] = defaultdict(float)

    match_log: List[Dict[str, Any]] = []

    attempts = 0
    made = 0
    max_attempts = iterations * 50

    while made < iterations and attempts < max_attempts:
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

        played[a_player] += 1
        played[b_player] += 1

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

        if write_match_log and len(match_log) < max_match_log:
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

    summary_rows.sort(key=lambda x: (x["win_rate"], x["wins"] + x["losses"]), reverse=True)
    return summary_rows, match_log

# -----------------------------
# Main
# -----------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True, help="RUN_ID folder under workflows/product_player_price_rankings/data/")
    ap.add_argument("--product-prefix", default="2025 Bowman Draft", help="Prefix used in Step 01 queries (default: 2025 Bowman Draft)")
    ap.add_argument("--require-all", default="bowman,draft", help="Comma-separated words required in title (default: bowman,draft)")
    ap.add_argument("--min-player-score", type=float, default=95.0, help="Min score to keep player_guess (default: 95)")
    ap.add_argument("--iterations", type=int, default=500000, help="Simulation iterations (default: 500000)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed")
    ap.add_argument("--max-rows", type=int, default=0, help="If >0, limit titles processed (debug)")
    ap.add_argument("--max-match-log", type=int, default=2000, help="Max rows for match sample CSV")
    ap.add_argument("--write-debug-rows", action="store_true", help="If set, write a small debug rows CSV")
    args = ap.parse_args()

    run_id = args.run_id.strip()
    run_dir = _require_run_dir(run_id)

    export_csv = run_dir / "term_search_items_export.csv"
    if not export_csv.exists():
        raise SystemExit(f"Missing input CSV: {export_csv}")

    # Step 01 summary -> derive player list
    summary_csv = _detect_step01_summary_csv(run_dir)
    if not summary_csv:
        raise SystemExit(
            f"Could not find a Step 01 summary CSV with a 'query' column in {run_dir}.\n"
            "Expected Step 01 to write a CSV (any name) with at least a 'query' column."
        )

    players = _derive_players_from_queries(summary_csv, args.product_prefix)
    if len(players) < 2:
        raise SystemExit(f"Derived too few players from {summary_csv.name}: {len(players)}")

    last_idx = _build_lastname_index(players)

    classify_title = _load_bowman_classifier()

    def passes_require_all(title: str) -> bool:
        words = [w.strip().lower() for w in (args.require_all or "").split(",") if w.strip()]
        if not words:
            return True
        t = (title or "").lower()
        return all(w in t for w in words)

    rows_for_sim: List[Tuple[str, str, float, str, str]] = []

    debug_rows: List[Dict[str, Any]] = []
    max_rows = int(args.max_rows or 0)

    with export_csv.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            title = (row.get("title") or "").strip()
            if not title:
                continue
            if not passes_require_all(title):
                continue

            price = _to_float(row.get("price"))
            ship = _to_float(row.get("shipping_cost"))
            if price is None:
                continue
            ship = ship or 0.0
            all_in = float(price) + float(ship)

            flags = classify_title(title)
            ct_list = _norm(str(flags.get("CT_list") or "")).strip()
            if not ct_list:
                continue

            # Drop “formats” you usually don’t want in pricing comps
            if ct_list in ("lot", "pick_your_card", "complete_set", "presale"):
                continue

            player, score = guess_player_from_title(title, players, last_idx)
            if not player or score < float(args.min_player_score):
                continue

            seller = (row.get("seller_username") or "").strip()
            rows_for_sim.append((player, ct_list, all_in, seller, title))

            if args.write_debug_rows and len(debug_rows) < 2000:
                debug_rows.append({
                    "player_guess": player,
                    "player_score": score,
                    "CT_list": ct_list,
                    "all_in_price": round(all_in, 4),
                    "seller_username": seller,
                    "title": title,
                })

            if max_rows > 0 and i >= max_rows:
                break

    if len(rows_for_sim) < 2:
        raise SystemExit("Not enough usable rows after filtering (need >= 2).")

    summary_rows, match_log = simulate(
        rows_for_sim,
        iterations=int(args.iterations),
        seed=int(args.seed),
        max_match_log=int(args.max_match_log),
        write_match_log=True,
    )

    out_summary = run_dir / "player_rankings_simulation.csv"
    with out_summary.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["player_name", "wins", "losses", "win_rate", "avg_win_margin", "played"])
        w.writeheader()
        for row in summary_rows:
            w.writerow(row)

    out_matches = run_dir / "player_rankings_simulation_matches_sample.csv"
    with out_matches.open("w", encoding="utf-8", newline="") as f:
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

    if args.write_debug_rows:
        out_debug = run_dir / "player_rankings_simulation_debug_rows.csv"
        with out_debug.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["player_guess", "player_score", "CT_list", "all_in_price", "seller_username", "title"])
            w.writeheader()
            w.writerows(debug_rows)

    print(f"RUN_ID={run_id}")
    print(f"SOURCE_EXPORT={export_csv}")
    print(f"PLAYERS_SOURCE={summary_csv}")
    print(f"PLAYERS_DERIVED={len(players)}")
    print(f"ROWS_FOR_SIM={len(rows_for_sim)}")
    print(f"ITERATIONS={args.iterations}")
    print(f"OUT_SUMMARY={out_summary}")
    print(f"OUT_MATCHES={out_matches}")

if __name__ == "__main__":
    main()
