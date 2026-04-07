#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_CLASSIFY_EXISTING_LISTINGS_JSON_6C2A1D90
import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

# Allow importing topps_listing_classifier from this directory.
# Cmd+F: GH_ANCHOR_IMPORT_CLASSIFIER_EXISTING_LISTINGS_2B7A1D91
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from topps_listing_classifier import classify_title  # noqa: E402
# Cmd+F: GH_ANCHOR_PLAYER_MATCH_HELPERS_6C2A1DA8
import re
from difflib import SequenceMatcher

# Optional faster lib; fallback to difflib if not installed.
try:
    from rapidfuzz import fuzz  # type: ignore
    _HAS_RAPIDFUZZ = True
except Exception:
    fuzz = None
    _HAS_RAPIDFUZZ = False

WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

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

def _ratio(a: str, b: str) -> float:
    a = (a or "").lower().strip()
    b = (b or "").lower().strip()
    if not a or not b:
        return 0.0
    if _HAS_RAPIDFUZZ:
        return float(fuzz.ratio(a, b))  # 0..100
    return SequenceMatcher(None, a, b).ratio() * 100.0

def _best_window_score(title_tokens: List[str], name_tokens: List[str]) -> Tuple[float, str]:
    k = len(name_tokens)
    if k == 0 or len(title_tokens) < k:
        return 0.0, ""
    name_str = " ".join(name_tokens)
    best = 0.0
    best_win = ""
    for i in range(0, len(title_tokens) - k + 1):
        win_tokens = title_tokens[i:i+k]
        win_str = " ".join(win_tokens)
        sc = _ratio(win_str, name_str)
        if sc > best:
            best = sc
            best_win = win_str
            if best >= 99.0:
                break
    return best, best_win

def load_players_index(players_csv: str, player_name_col: str = "playerName") -> Tuple[List[str], Dict[str, List[int]]]:
    """
    Returns:
      names: list of playerName strings
      last_index: map last_name_token -> list of indices into names
    """
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

def guess_player_from_title(
    title: str,
    names: List[str],
    last_index: Dict[str, List[int]],
    max_candidates: int = 1500,
) -> Tuple[str, float, str]:
    """
    Returns: (player_guess, score_0_to_100, matched_window)
    """
    title_tokens = _norm_tokens(title)
    if not title_tokens:
        return "", 0.0, ""

    cand_ids = set()
    for tok in title_tokens:
        ids = last_index.get(tok)
        if ids:
            for i in ids:
                cand_ids.add(i)
        if len(cand_ids) >= max_candidates:
            break

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

        # Strong exact containment shortcut
        if all(t in title_tokens for t in nm_tokens):
            return nm, 100.0, " ".join(nm_tokens)

        sc, win = _best_window_score(title_tokens, nm_tokens)
        if sc > best_score:
            best_score = sc
            best_name = nm
            best_win = win

    return best_name, best_score, best_win

# Cmd+F: GH_ANCHOR_CT_NAME_FORMATTER_6C2A1D93
def format_ct_name(ct_key: str) -> str:
    """
    Convert 'CT_chrome' -> 'Chrome'
            'CT_base_rainbow' -> 'Base Rainbow'
            'CT_x_fractor' -> 'X-Fractor'
            'CT_ssp' -> 'SSP'
    """
    raw = (ct_key or "").strip()
    if raw.startswith("CT_"):
        raw = raw[3:]

    specials = {
        "ssp": "SSP",
        "sp": "SP",
        "rc": "RC",
        "x_fractor": "X-Fractor",
    }
    if raw in specials:
        return specials[raw]

    parts = raw.split("_")
    out_parts: List[str] = []
    for p in parts:
        if not p:
            continue
        if p.isdigit():
            out_parts.append(p)
        elif p in ("ssp", "sp", "rc"):
            out_parts.append(p.upper())
        else:
            out_parts.append(p[:1].upper() + p[1:].lower())
    return " ".join(out_parts)

# Cmd+F: GH_ANCHOR_LOT_FILTER_HELPER_6C2A1D95
import re
RX_LOT = re.compile(r"\blot\b|\blots\b|\bteam\s*lot\b|\bplayer\s*lot\b", re.IGNORECASE)

def is_lot_title(title: str, flags: Dict[str, Any]) -> bool:
    # Prefer classifier signal if present; fallback to regex.
    if bool(flags.get("WF_lot", False)) or bool(flags.get("CT_lot", False)):
        return True
    return RX_LOT.search(title or "") is not None

def _to_float(v: Any) -> float:
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except Exception:
        return 0.0


def _load_rows_from_json(path: str) -> List[Dict[str, Any]]:
    # Cmd+F: GH_ANCHOR_LOAD_ROWS_FROM_JSON_7A1B2C3D
    # Supports:
    #  - .json  (array or {"rows":[...]})
    #  - .jsonl (one JSON object per line)
    p = path.lower().strip()

    if p.endswith(".jsonl"):
        rows: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
        return rows

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Support common shapes:
    #  - [ {...}, {...} ]
    #  - { "rows": [ ... ] }
    #  - { ...single row... }
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("rows"), list):
            return [r for r in data["rows"] if isinstance(r, dict)]
        return [data]
    return []


def main() -> None:
    # Cmd+F: GH_ANCHOR_CLASSIFY_EXISTING_LISTINGS_MAIN_5F1A3B8D
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        required=True,
        help="Input JSON file (e.g. data/topps_update_2025/listings_2025_topps_update.jsonl)",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output CSV file (e.g. data/topps_update_2025/listings_2025_topps_update_jsonl_classified.csv)",
    )
    ap.add_argument("--title-key", default="title", help="Title field name (default: title)")
    ap.add_argument("--price-key", default="price", help="Price field name (default: price)")
    ap.add_argument("--shipping-key", default="shipping_cost", help="Shipping field name (default: shipping_cost)")
    ap.add_argument("--max-out", type=int, default=1000, help="Max output rows (default: 1000)")
    ap.add_argument("--only-unclassified", action="store_true", help="If set, keep only CT_any=false rows")
        # Cmd+F: GH_ANCHOR_PLAYER_MATCH_ARGS_6C2A1DA9
    ap.add_argument(
        "--players-csv",
        default="data/topps_update_2025/2025_Topps_Update_player_list.csv",
        help="Players CSV path (default: data/topps_update_2025/2025_Topps_Update_player_list.csv)",
    )
    ap.add_argument("--player-name-col", default="playerName",
                    help="Column in players CSV containing the full name (default: playerName)")
    ap.add_argument("--min-player-score", type=float, default=86.0,
                    help="Only keep player_guess if score >= this (default: 86)")
    args = ap.parse_args()

    in_path = args.input.strip()
    out_path = args.out.strip()
    title_key = (args.title_key or "title").strip()
    price_key = (args.price_key or "price").strip()
    shipping_key = (args.shipping_key or "shipping_cost").strip()
    max_out = max(1, int(args.max_out))
    only_unclassified = bool(args.only_unclassified)
    players_csv = (args.players_csv or "").strip()
    player_name_col = (args.player_name_col or "playerName").strip()
    min_player_score = float(args.min_player_score)

    if not os.path.exists(in_path):
        raise SystemExit(f"Input JSON not found: {in_path}")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    rows = _load_rows_from_json(in_path)

    # Discover CT_* keys deterministically
    # Cmd+F: GH_ANCHOR_DISCOVER_CT_KEYS_EXISTING_LISTINGS_4D2A1C90
    tmpl: Dict[str, object] = classify_title("")
    ct_cols: List[str] = [k for k, v in tmpl.items() if isinstance(v, bool) and k.startswith("CT_")]
    # Cmd+F: GH_ANCHOR_LOAD_PLAYERS_INDEX_ONCE_6C2A1DAA
    player_names: List[str] = []
    player_last_index: Dict[str, List[int]] = {}
    if players_csv and os.path.exists(players_csv):
        player_names, player_last_index = load_players_index(players_csv, player_name_col)
    else:
        # If missing, we still run classification; player_guess stays blank.
        player_names, player_last_index = [], {}


    # Build classified rows, filter if requested, sort by all_in_price desc, take top N
    # Cmd+F: GH_ANCHOR_CLASSIFY_FILTER_SORT_LIMIT_9D2A1C90
    classified: List[Dict[str, Any]] = []
    for r in rows:
        title = (r.get(title_key) or "").strip()
        price = _to_float(r.get(price_key))
        ship = _to_float(r.get(shipping_key))
        all_in = price + ship

        flags = classify_title(title)
        if is_lot_title(title, flags):
            continue
        ct_values = {k: bool(flags.get(k, False)) for k in ct_cols}
        ct_any = any(ct_values.values())
        ct_true_names = [format_ct_name(k) for k, v in ct_values.items() if v]
        ct_list = ", ".join(ct_true_names)
        # Cmd+F: GH_ANCHOR_PLAYER_GUESS_PER_ROW_6C2A1DAB
        player_guess = ""
        player_score = 0.0
        player_window = ""
        if player_names and player_last_index:
            g, sc, win = guess_player_from_title(title, player_names, player_last_index)
            if g and sc >= min_player_score:
                player_guess = g
                player_score = sc
                player_window = win


        if only_unclassified and ct_any:
            continue

        out_row: Dict[str, Any] = {
            "title": title,
            "all_in_price": round(all_in, 4),
            "CT_any": ct_any,
            "CT_list": ct_list,
            "player_guess": player_guess,
            "player_score": round(float(player_score), 2) if player_guess else "",
            "player_window": player_window,
        }
        classified.append(out_row)

    classified.sort(key=lambda x: _to_float(x.get("all_in_price")), reverse=True)
    classified = classified[:max_out]

    # Output columns (keep it small): title + price + classification summary
    out_cols = ["title", "all_in_price", "CT_any", "CT_list", "player_guess", "player_score", "player_window"]


    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_cols)
        w.writeheader()
        for row in classified:
            w.writerow(row)

    print(f"INPUT={in_path}")
    print(f"OUTPUT={out_path}")
    print(f"ROWS_IN={len(rows)}")
    print(f"ONLY_UNCLASSIFIED={only_unclassified}")
    print(f"WROTE={len(classified)}")
    print(f"CT_COLS={len(ct_cols)}")


if __name__ == "__main__":
    main()
