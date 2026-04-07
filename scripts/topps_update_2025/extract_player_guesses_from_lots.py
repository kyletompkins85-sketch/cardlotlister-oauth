#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_EXTRACT_PLAYER_GUESSES_FROM_LOTS_6C2A1D90
import argparse
import csv
import os
import re
from collections import Counter
from typing import Dict, Iterable, List, Optional, Tuple

# ----------------------------
# Heuristics
# ----------------------------

# Cmd+F: GH_ANCHOR_LOT_REGEX_6C2A1D91
RX_LOTISH = re.compile(
    r"\b(lot|lots|team\s*lot|player\s*lot|bundle|bundles|bulk|group|groups|set\s*builder|pick\s*from\s*list|you\s*choose)\b",
    re.IGNORECASE,
)

# Words we don't want treated as a "name token"
# Cmd+F: GH_ANCHOR_NAME_STOPWORDS_6C2A1D92
STOP = {
    "TOPPS", "UPDATE", "SERIES", "BASE", "BASEBALL", "CARD", "CARDS", "RC", "ROOKIE", "AUTO", "AUTOGRAPH",
    "PARALLEL", "REFRACTOR", "CHROME", "FOIL", "HOLO", "HOLOFOIL", "RAINBOW", "COMPLETE", "SET",
    "PICK", "YOUR", "YOU", "CHOOSE", "FROM", "LIST", "LOT", "LOTS",
    "US", "MLB", "FS", "HOT", "SALE", "FREE", "SHIP", "SHIPPING",
    "OF", "THE", "AND", "OR", "WITH", "FOR", "TO", "IN",
    "2025", "2024", "2023", "2022", "2021", "2020",
}

# tokenize words and keep apostrophes/hyphens inside a token
# Cmd+F: GH_ANCHOR_TOKEN_RE_6C2A1D93
TOKEN_RE = re.compile(r"[A-Za-z]+(?:[’'][A-Za-z]+)?(?:-[A-Za-z]+)?")

def is_lot_title(title: str) -> bool:
    return RX_LOTISH.search(title or "") is not None

def tokens(title: str) -> List[str]:
    return TOKEN_RE.findall(title or "")

def is_name_token(tok: str) -> bool:
    if not tok:
        return False
    # strip punctuation-ish
    t = tok.strip("’'\"`.,:;()[]{}<>!@#$%^&*_+=|\\/").strip()
    if not t:
        return False
    up = t.upper()
    if up in STOP:
        return False
    # reject pure numbers
    if t.isdigit():
        return False
    # reject short noise
    if len(t) <= 1:
        return False
    # accept "TitleCase" and also ALLCAPS names like "OHTANI" (but not short abbreviations)
    if t[0].isalpha() and t[0].isupper():
        if t.isupper() and len(t) <= 2:
            return False
        return True
    return False

def find_capital_spans(title: str, min_tokens: int = 2, max_tokens: int = 3) -> List[str]:
    # Cmd+F: GH_ANCHOR_FIND_CAPITAL_SPANS_6C2A1D94
    ts = tokens(title)
    spans: List[str] = []
    good = [t for t in ts]  # preserve original casing
    n = len(good)
    for i in range(n):
        if not is_name_token(good[i]):
            continue
        for j in range(i + min_tokens, min(n, i + max_tokens) + 1):
            chunk = good[i:j]
            if all(is_name_token(x) for x in chunk):
                spans.append(" ".join(chunk).strip())
    return spans

def build_name_dictionary(titles: Iterable[str]) -> Counter:
    # Cmd+F: GH_ANCHOR_BUILD_NAME_DICTIONARY_6C2A1D95
    c = Counter()
    for t in titles:
        for span in find_capital_spans(t, min_tokens=2, max_tokens=3):
            c[span] += 1
    return c

def pick_best_name_from_dict(title: str, name_counts: Counter) -> Tuple[Optional[str], float, str, int, int]:
    """
    Returns: (best_name, confidence, method, span_len, dict_freq)
    """
    # Cmd+F: GH_ANCHOR_PICK_BEST_NAME_6C2A1D96
    spans = find_capital_spans(title, min_tokens=2, max_tokens=3)
    if not spans:
        return None, 0.0, "none", 0, 0

    # score: prefer longer spans, then higher frequency in dict
    best = None
    best_score = -1.0
    best_len = 0
    best_freq = 0

    for s in spans:
        freq = int(name_counts.get(s, 0))
        length = len(s.split())
        score = (length * 10_000) + freq  # length dominates, freq breaks ties
        if score > best_score:
            best_score = score
            best = s
            best_len = length
            best_freq = freq

    # confidence: normalized-ish. (length gives big bump, freq adds more if common)
    conf = 0.3 if best_len == 2 else 0.45
    if best_len >= 3:
        conf = 0.6
    if best_freq >= 5:
        conf += 0.15
    if best_freq >= 20:
        conf += 0.15
    conf = min(0.99, conf)

    method = "dict" if best_freq > 0 else "heuristic"
    return best, conf, method, best_len, best_freq

def main() -> None:
    # Cmd+F: GH_ANCHOR_EXTRACT_PLAYER_GUESSES_MAIN_6C2A1D97
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        required=True,
        help="Input CSV path (e.g. data/topps_update_2025/term_search_items_table.csv)",
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output CSV path (e.g. data/topps_update_2025/lot_player_guesses.csv)",
    )
    ap.add_argument("--title-col", default="title", help="Column name for title (default: title)")
    ap.add_argument("--max-lots", type=int, default=1000, help="Max lot rows to output (default: 1000)")
    ap.add_argument("--dict-max", type=int, default=20000, help="Max non-lot titles to learn from (default: 20000)")
    args = ap.parse_args()

    in_path = args.input
    out_path = args.out
    title_col = (args.title_col or "title").strip()
    max_lots = max(1, int(args.max_lots))
    dict_max = max(100, int(args.dict_max))

    if not os.path.exists(in_path):
        raise SystemExit(f"Input CSV not found: {in_path}")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # First pass: collect non-lot titles for dictionary
    # Cmd+F: GH_ANCHOR_FIRST_PASS_COLLECT_NONLOTS_6C2A1D98
        # Cmd+F: GH_ANCHOR_FIRST_PASS_COLLECT_NONLOTS_6C2A1D98
    nonlot_titles: List[str] = []
    target_titles: List[str] = []

    with open(in_path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise SystemExit("Input CSV has no header row")
        if title_col not in r.fieldnames:
            raise SystemExit(f"Missing title column '{title_col}' in CSV header")

        for row in r:
            t = (row.get(title_col) or "").strip()
            if not t:
                continue

            # EXCLUDE lots entirely
            if is_lot_title(t):
                continue

            # use these to build dictionary
            if len(nonlot_titles) < dict_max:
                nonlot_titles.append(t)

            # also process as target rows
            target_titles.append(t)

    name_dict = build_name_dictionary(nonlot_titles)

    # Second pass: score lot titles
    # Cmd+F: GH_ANCHOR_SECOND_PASS_SCORE_LOTS_6C2A1D99
    out_cols = ["title", "player_guess", "confidence", "method", "span_len", "dict_freq"]
    wrote = 0

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_cols)
        w.writeheader()

        for t in target_titles:
            best, conf, method, span_len, freq = pick_best_name_from_dict(t, name_dict)
            w.writerow({
                "title": t,
                "player_guess": best or "",
                "confidence": round(conf, 4),
                "method": method,
                "span_len": span_len,
                "dict_freq": freq,
            })
            wrote += 1
            if wrote >= max_lots:
                break

    print(f"INPUT={in_path}")
    print(f"OUTPUT={out_path}")
    print(f"TITLE_COL={title_col}")
    print(f"NONLOT_TITLES_USED_FOR_DICT={len(nonlot_titles)}")
    print(f"UNIQUE_NAME_SPANS_IN_DICT={len(name_dict)}")
    print(f"TARGET_TITLES_FOUND={len(target_titles)}")
    print(f"WROTE_ROWS={wrote}")

if __name__ == "__main__":
    main()
