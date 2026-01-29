#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_SIMULATE_PLAYER_RANKINGS_BOWMAN_92A1C7D0
"""
Simulate player price rankings by holding CT_list constant.

Sources (in order):
  1) If present: workflows/product_player_price_rankings/data/<RUN_ID>/term_search_items_export.csv
  2) Fallback: Worker -> GET /internal/termSearchItems/search?q=... (SUPABASE ONLY, NO EBAY)

Also derives player list from Step 01 summary CSV in the same run folder (any CSV with 'query' column).
Queries are assumed like: "<product-prefix> <player name>"

Outputs (same run folder):
  - player_rankings_simulation.csv
  - player_rankings_simulation_matches_sample.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode, urljoin

import requests

def _detect_step01_players_csv(run_dir: Path) -> Path:
    # Step 01 writes: product_players_search_summary_<safe_product>.csv
    hits = sorted(run_dir.glob("product_players_search_summary_*.csv"))
    if hits:
        return hits[0]
    raise SystemExit(
        f"Could not find Step 01 players CSV in: {run_dir}\n"
        "Expected: product_players_search_summary_*.csv (written by Step 01)"
    )

def _load_players_from_step01_csv(path: Path) -> List[str]:
    players: List[str] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            nm = (row.get("playerName") or "").strip()
            if nm:
                players.append(nm)

    # de-dupe preserving order
    seen = set()
    out: List[str] = []
    for p in players:
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(p)

    return out

def _detect_step00_players_export_csv(run_dir: Path) -> Optional[Path]:
    p = run_dir / "players_export.csv"
    return p if p.exists() else None

def _load_players_from_step00_export(path: Path) -> List[str]:
    players: List[str] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        # supports header "playerName"
        for row in r:
            nm = (row.get("playerName") or "").strip()
            if nm:
                players.append(nm)

    # de-dupe preserving order
    seen = set()
    out: List[str] = []
    for p in players:
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out

def _worker_get_json(url: str, key: str) -> Dict[str, Any]:
    resp = requests.get(url, headers={"x-internal-key": key}, timeout=90)
    text = resp.text
    try:
        data = resp.json()
    except Exception:
        data = {"raw": text}
    if not resp.ok:
        raise RuntimeError(f"Worker GET failed {resp.status_code}: {text}")
    return data

def _iter_titles_rows_from_export_csv(csv_path: Path) -> Iterable[Dict[str, Any]]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            yield row

def _iter_titles_rows_from_worker(base_url: str, api_key: str, q: str) -> Iterable[Dict[str, Any]]:
    limit = 1000
    offset = 0
    while True:
        params = {"q": q, "limit": str(limit), "offset": str(offset)}
        endpoint = urljoin(base_url.rstrip("/") + "/", "internal/termSearchItems/search")
        url = f"{endpoint}?{urlencode(params)}"
        data = _worker_get_json(url, api_key)
        rows = data.get("rows") or []
        if not isinstance(rows, list):
            raise RuntimeError("Worker returned rows that were not a list")
        for row in rows:
            if isinstance(row, dict):
                yield row
        next_offset = data.get("next_offset")
        if not next_offset:
            break
        offset = int(next_offset)


# -----------------------------
# Basics
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

def _passes_require_all(title: str, require_all_csv: str) -> bool:
    words = [w.strip().lower() for w in (require_all_csv or "").split(",") if w.strip()]
    if not words:
        return True
    t = (title or "").lower()
    return all(w in t for w in words)

def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


# -----------------------------
# Import Bowman classifier
# -----------------------------
def _load_bowman_classifier():
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    from z10_bowman_listing_classifier import classify_title  # type: ignore
    return classify_title


# -----------------------------
# Step01 summary -> derive players
# -----------------------------
def _detect_step01_summary_csv(run_dir: Path) -> Optional[Path]:
    """
    Find any CSV in the run folder that contains a 'query' column.
    That is your Step 01 summary.
    """
    for p in sorted(run_dir.glob("*.csv")):
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
    prefix = _norm(product_prefix).lower()
    players: List[str] = []
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
                name = q  # fallback: use whole query
            name = _norm(name)
            if name and len(name.split()) >= 2:
                players.append(name)

    seen = set()
    out: List[str] = []
    for p in players:
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(p)
    return out


# -----------------------------
# Player matching (title -> player)
# -----------------------------
def _build_lastname_index(players: List[str]) -> Dict[str, List[str]]:
    idx: Dict[str, List[str]] = defaultdict(list)
    for full in players:
        parts = _tokenize(full)
        if parts:
            idx[parts[-1]].append(full)
    return idx

def guess_player_from_title(title: str, last_idx: Dict[str, List[str]]) -> Tuple[str, float]:
    """
    Heuristic scoring:
      100: all name tokens present
      95 : first+last present
      80 : last present
    """
    t_toks = _tokenize(title)
    if not t_toks:
        return "", 0.0
    t_set = set(t_toks)

    best_name = ""
    best_score = 0.0

    for last, candidates in last_idx.items():
        if last not in t_set:
            continue
        for full in candidates:
            ntoks = _tokenize(full)
            if not ntoks:
                continue
            first = ntoks[0]
            all_in = all(tok in t_set for tok in ntoks)
            if all_in:
                score = 100.0
            elif first in t_set and last in t_set:
                score = 95.0
            else:
                score = 80.0

            if score > best_score:
                best_score = score
                best_name = full

    return best_name, best_score


# -----------------------------
# Worker fallback (SUPABASE ONLY)
# -----------------------------
def _worker_get_json(url: str, key: str) -> Dict[str, Any]:
    resp = requests.get(url, headers={"x-internal-key": key}, timeout=90)
    text = resp.text
    try:
        data = resp.json()
    except Exception:
        data = {"raw": text}
    if not resp.ok:
        raise RuntimeError(f"Worker GET failed {resp.status_code}: {text}")
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response type: {type(data)}")
    return data

def _iter_rows_from_worker(base_url: str, api_key: str, q: str) -> Iterable[Dict[str, Any]]:
    """
    Reads from /internal/termSearchItems/search (NO EBAY)
    Must return rows with at least: title, price, shipping_cost, seller_username
    """
    limit = 1000
    offset = 0
    while True:
        params = {"q": q, "limit": str(limit), "offset": str(offset)}
        endpoint = urljoin(base_url.rstrip("/") + "/", "internal/termSearchItems/search")
        url = f"{endpoint}?{urlencode(params)}"

        data = _worker_get_json(url, api_key)
        rows = data.get("rows") or []
        if not isinstance(rows, list):
            raise RuntimeError("Worker returned rows that were not a list")

        for row in rows:
            if isinstance(row, dict):
                yield row

        next_offset = data.get("next_offset")
        if not next_offset:
            break
        offset = int(next_offset)


# -----------------------------
# Simulation
# -----------------------------
def simulate(rows: List[Tuple[str, str, float, str, str]],
             iterations: int,
             seed: int,
             max_match_log: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    random.seed(seed)

    by_ct: Dict[str, List[int]] = defaultdict(list)
    by_ct_player: Dict[Tuple[str, str], List[int]] = defaultdict(list)
    for idx, (player, ct, price, seller, title) in enumerate(rows):
        by_ct[ct].append(idx)
        by_ct_player[(ct, player)].append(idx)

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

        if len(match_log) < max_match_log:
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
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--product-prefix", default="2025 Bowman Draft")
    ap.add_argument("--require-all", default="bowman,draft")
    ap.add_argument("--min-player-score", type=float, default=95.0)
    ap.add_argument("--iterations", type=int, default=500000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-match-log", type=int, default=2000)

    # fallback inputs
    ap.add_argument("--q", default="", help="Worker fallback q (e.g. '2025 Bowman Draft')")
    args = ap.parse_args()

    run_id = args.run_id.strip()
    workflow_root = Path(__file__).resolve().parent
    run_dir = workflow_root / "data" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    export_csv = run_dir / "term_search_items_export.csv"

    # players list:
    # 1) prefer Step 01 CSV if it exists (when eBay path ran)
    # 2) fallback to Step 00 export (skip-eBay path)
    players: List[str] = []
    players_source = ""
    
    step01_csv = None
    try:
        step01_csv = _detect_step01_players_csv(run_dir)  # product_players_search_summary_*.csv
    except Exception:
        step01_csv = None
    
    if step01_csv and step01_csv.exists():
        players = _load_players_from_step01_csv(step01_csv)
        players_source = step01_csv.name
    else:
        step00_csv = _detect_step00_players_export_csv(run_dir)
        if step00_csv:
            players = _load_players_from_step00_export(step00_csv)
            players_source = step00_csv.name
        else:
            raise SystemExit(
                "No players list found.\n"
                f"- Expected Step 01 output: product_players_search_summary_*.csv in {run_dir}\n"
                f"- OR Step 00 output: players_export.csv in {run_dir}\n"
                "Run Step 00 (export players) or Step 01 (eBay path) first."
            )
    
    if len(players) < 2:
        raise SystemExit(f"Too few players in {players_source}: {len(players)}")
    
    last_idx = _build_lastname_index(players)



    classify_title = _load_bowman_classifier()

    rows_for_sim: List[Tuple[str, str, float, str, str]] = []

    source = ""
    if export_csv.exists():
        source = f"csv:{export_csv}"
        with export_csv.open("r", encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                title = (row.get("title") or "").strip()
                if not title:
                    continue
                if not _passes_require_all(title, args.require_all):
                    continue

                price = _to_float(row.get("price"))
                ship = _to_float(row.get("shipping_cost")) or 0.0
                if price is None:
                    continue
                all_in = float(price) + float(ship)

                flags = classify_title(title)
                ct_list = _norm(str(flags.get("CT_list") or "")).strip()
                if not ct_list:
                    continue

                # drop the “formats”
                if ct_list in ("lot", "pick_your_card", "complete_set", "presale"):
                    continue

                player, score = guess_player_from_title(title, last_idx)
                if not player or score < float(args.min_player_score):
                    continue

                seller = (row.get("seller_username") or "").strip()
                rows_for_sim.append((player, ct_list, all_in, seller, title))
    else:
        # Worker fallback (SUPABASE ONLY; NO EBAY)
        base = _require_env("WORKER_BASE_URL")
        key = _require_env("INTERNAL_API_KEY")
        q = (args.q or os.getenv("PREFIX") or "").strip()
        if not q:
            raise SystemExit(
                f"Missing input CSV: {export_csv}\n"
                "Provide --q or set env PREFIX for Worker fallback."
            )
        source = f"worker:/internal/termSearchItems/search?q={q}"
        for row in _iter_rows_from_worker(base, key, q):
            title = (row.get("title") or "").strip()
            if not title:
                continue
            if not _passes_require_all(title, args.require_all):
                continue

            price = _to_float(row.get("price"))
            ship = _to_float(row.get("shipping_cost")) or 0.0
            if price is None:
                continue
            all_in = float(price) + float(ship)

            flags = classify_title(title)
            ct_list = _norm(str(flags.get("CT_list") or "")).strip()
            if not ct_list:
                continue
            if ct_list in ("lot", "pick_your_card", "complete_set", "presale"):
                continue

            player, score = guess_player_from_title(title, last_idx)
            if not player or score < float(args.min_player_score):
                continue

            seller = (row.get("seller_username") or "").strip()
            rows_for_sim.append((player, ct_list, all_in, seller, title))

    if len(rows_for_sim) < 2:
        raise SystemExit("Not enough usable rows after filtering for simulation (need >=2).")

    summary_rows, match_log = simulate(
        rows_for_sim,
        iterations=int(args.iterations),
        seed=int(args.seed),
        max_match_log=int(args.max_match_log),
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

    print(f"SOURCE={source}")
    print(f"RUN_ID={run_id}")
    print(f"PLAYERS_SOURCE={players_source}")
    print(f"PLAYERS_LOADED={len(players)}")
    print(f"PLAYERS_DERIVED={len(players)}")
    print(f"ROWS_FOR_SIM={len(rows_for_sim)}")
    print(f"ITERATIONS={args.iterations}")
    print(f"OUT_SUMMARY={out_summary}")
    print(f"OUT_MATCHES={out_matches}")


if __name__ == "__main__":
    main()
