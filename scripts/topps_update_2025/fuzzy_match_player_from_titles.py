#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_FUZZY_MATCH_PLAYER_FROM_TITLES_6C2A1D90
import argparse
import csv
import os
import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional, Any

# Optional faster lib; fallback to difflib if not installed.
# Cmd+F: GH_ANCHOR_OPTIONAL_RAPIDFUZZ_6C2A1D91
try:
    from rapidfuzz import fuzz  # type: ignore
    _HAS_RAPIDFUZZ = True
except Exception:
    fuzz = None
    _HAS_RAPIDFUZZ = False

# Cmd+F: GH_ANCHOR_TOKENIZER_6C2A1D92
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

# Cmd+F: GH_ANCHOR_LOTISH_FILTER_6C2A1D93
RX_LOTISH = re.compile(
    r"\b(lot|lots|team\s*lot|player\s*lot|bundle|bundles|bulk|group|groups|set\s*builder|pick\s*from\s*list|you\s*choose)\b",
    re.IGNORECASE,
)

# Cmd+F: GH_ANCHOR_TITLE_NOISE_WORDS_6C2A1D94
NOISE = {
    "topps","update","series","base","baseball","card","cards","rc","rookie","auto","autograph",
    "parallel","refractor","chrome","foil","holo","holofoil","rainbow","complete","set","pick",
    "your","you","choose","from","list","mlb","fs","free","ship","shipping",
    "us", "of", "and", "or", "with", "for", "to", "in",
}

def _norm_tokens(s: str) -> List[str]:
    ts = WORD_RE.findall(s or "")
    out: List[str] = []
    for t in ts:
        t = t.lower().strip()
        if not t or t in NOISE:
            continue
        out.append(t)
    return out

def _is_lot(title: str) -> bool:
    return RX_LOTISH.search(title or "") is not None

def _ratio(a: str, b: str) -> float:
    # Cmd+F: GH_ANCHOR_RATIO_FUNC_6C2A1D95
    a = (a or "").lower().strip()
    b = (b or "").lower().strip()
    if not a or not b:
        return 0.0
    if _HAS_RAPIDFUZZ:
        return float(fuzz.ratio(a, b))  # 0..100
    return SequenceMatcher(None, a, b).ratio() * 100.0

def _best_window_score(title_tokens: List[str], name_tokens: List[str]) -> Tuple[float, str]:
    # Cmd+F: GH_ANCHOR_BEST_WINDOW_SCORE_6C2A1D96
    k = len(name_tokens)
    if k == 0 or len(title_tokens) < k:
        return 0.0, ""

    name_str = " ".join(name_tokens)
    best = 0.0
    best_win = ""

    # Slide a window of same token-length as the name
    for i in range(0, len(title_tokens) - k + 1):
        win_tokens = title_tokens[i:i+k]
        win_str = " ".join(win_tokens)
        sc = _ratio(win_str, name_str)
        if sc > best:
            best = sc
            best_win = win_str

            # perfect-ish early exit
            if best >= 99.0:
                break

    return best, best_win

def load_players(players_csv: str, player_name_col: str) -> Tuple[List[str], Dict[str, List[int]]]:
    # Cmd+F: GH_ANCHOR_LOAD_PLAYERS_AND_INDEX_6C2A1D97
    names: List[str] = []
    last_index: Dict[str, List[int]] = {}

    with open(players_csv, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit("Players CSV has no header row")
        if player_name_col not in r.fieldnames:
            raise SystemExit(f"Players CSV missing column '{player_name_col}' (has: {r.fieldnames})")

        for row in r:
            nm = (row.get(player_name_col) or "").strip()
            if not nm:
                continue
            idx = len(names)
            names.append(nm)

            toks = _norm_tokens(nm)
            if not toks:
                continue
            last = toks[-1]
            last_index.setdefault(last, []).append(idx)

    return names, last_index

def guess_player_for_title(
    title: str,
    names: List[str],
    last_index: Dict[str, List[int]],
    max_candidates: int,
) -> Tuple[str, float, str]:
    # Cmd+F: GH_ANCHOR_GUESS_PLAYER_FOR_TITLE_6C2A1D98
    title_tokens = _norm_tokens(title)
    if not title_tokens:
        return "", 0.0, ""

    # Candidate set by last-name token overlap
    cand_ids = set()
    for tok in title_tokens:
        ids = last_index.get(tok)
        if ids:
            for i in ids:
                cand_ids.add(i)
        if len(cand_ids) >= max_candidates:
            break

    # If no candidates, bail early (don’t brute-force full list)
    if not cand_ids:
        return "", 0.0, ""

    best_name = ""
    best_score = 0.0
    best_win = ""

    for i in cand_ids:
        nm = names[i]
        nm_tokens = _norm_tokens(nm)
        if not nm_tokens:
            continue

        # Fast exact token containment (strong signal)
        if all(t in title_tokens for t in nm_tokens):
            return nm, 100.0, " ".join(nm_tokens)

        sc, win = _best_window_score(title_tokens, nm_tokens)
        if sc > best_score:
            best_score = sc
            best_name = nm
            best_win = win

    return best_name, best_score, best_win

def main() -> None:
    # Cmd+F: GH_ANCHOR_FUZZY_MATCH_MAIN_6C2A1D99
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        required=True,
        help="Input CSV with titles (e.g. data/topps_update_2025/unclassified_titles_all.csv)",
    )
    ap.add_argument(
        "--players",
        required=True,
        help="Players CSV (e.g. data/topps_update_2025/2025_Topps_Update_player_list.csv)",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output CSV path (e.g. data/topps_update_2025/player_guesses_unclassified_titles_canvas.csv)",
    )
    ap.add_argument("--title-col", default="title", help="Title column name (default: title)")
    ap.add_argument("--player-name-col", default="playerName", help="Players name column (default: playerName)")
    ap.add_argument("--max-rows", type=int, default=1000, help="Max input rows to process (default: 1000)")
    ap.add_argument("--min-score", type=float, default=86.0, help="Only keep matches >= this score (default: 86)")
    ap.add_argument("--max-candidates", type=int, default=1500, help="Max candidates per title (default: 1500)")
    ap.add_argument("--skip-lots", action="store_true", help="If set, skip lot-ish titles entirely")
    args = ap.parse_args()

    in_csv = args.input.strip()
    players_csv = args.players.strip()
    out_csv = args.out.strip()

    title_col = (args.title_col or "title").strip()
    player_name_col = (args.player_name_col or "playerName").strip()
    max_rows = max(1, int(args.max_rows))
    min_score = float(args.min_score)
    max_candidates = max(50, int(args.max_candidates))
    skip_lots = bool(args.skip_lots)

    if not os.path.exists(in_csv):
        raise SystemExit(f"Input CSV not found: {in_csv}")
    if not os.path.exists(players_csv):
        raise SystemExit(f"Players CSV not found: {players_csv}")
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)

    names, last_index = load_players(players_csv, player_name_col)

    out_cols = ["title", "player_guess", "score", "matched_window"]
    wrote = 0
    processed = 0
    skipped_lots = 0

    with open(in_csv, "r", encoding="utf-8", newline="") as fin, open(out_csv, "w", encoding="utf-8", newline="") as fout:
        r = csv.DictReader(fin)
        if not r.fieldnames:
            raise SystemExit("Input CSV has no header row")
        if title_col not in r.fieldnames:
            raise SystemExit(f"Input CSV missing column '{title_col}' (has: {r.fieldnames})")

        w = csv.DictWriter(fout, fieldnames=out_cols)
        w.writeheader()

        for row in r:
            title = (row.get(title_col) or "").strip()
            if not title:
                continue

            if skip_lots and _is_lot(title):
                skipped_lots += 1
                continue

            processed += 1
            nm, sc, win = guess_player_for_title(title, names, last_index, max_candidates)

            if nm and sc >= min_score:
                w.writerow({
                    "title": title,
                    "player_guess": nm,
                    "score": round(sc, 2),
                    "matched_window": win,
                })
                wrote += 1

            if processed >= max_rows:
                break

    print(f"INPUT={in_csv}")
    print(f"PLAYERS={players_csv}")
    print(f"OUTPUT={out_csv}")
    print(f"PLAYERS_LOADED={len(names)}")
    print(f"MAX_ROWS={max_rows}")
    print(f"MIN_SCORE={min_score}")
    print(f"SKIP_LOTS={skip_lots} (skipped={skipped_lots})")
    print(f"PROCESSED={processed}")
    print(f"WROTE_MATCHES={wrote}")

if __name__ == "__main__":
    main()
