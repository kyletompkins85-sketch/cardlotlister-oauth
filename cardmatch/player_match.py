from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

try:
    from rapidfuzz import fuzz  # type: ignore

    _HAS_RAPIDFUZZ = True
except Exception:
    fuzz = None
    _HAS_RAPIDFUZZ = False

WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

NOISE = {
    "topps",
    "update",
    "series",
    "base",
    "baseball",
    "card",
    "cards",
    "rc",
    "rookie",
    "auto",
    "autograph",
    "parallel",
    "refractor",
    "chrome",
    "foil",
    "holo",
    "holofoil",
    "rainbow",
    "complete",
    "set",
    "pick",
    "your",
    "you",
    "choose",
    "from",
    "list",
    "mlb",
    "fs",
    "free",
    "ship",
    "shipping",
    "bowman",
    "draft",
    "us",
    "of",
    "and",
    "or",
    "with",
    "for",
    "to",
    "in",
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
        return float(fuzz.ratio(a, b))
    return SequenceMatcher(None, a, b).ratio() * 100.0


def _best_window_score(title_tokens: List[str], name_tokens: List[str]) -> Tuple[float, str]:
    k = len(name_tokens)
    if k == 0 or len(title_tokens) < k:
        return 0.0, ""
    name_str = " ".join(name_tokens)
    best = 0.0
    best_win = ""
    for i in range(0, len(title_tokens) - k + 1):
        win_tokens = title_tokens[i : i + k]
        win_str = " ".join(win_tokens)
        sc = _ratio(win_str, name_str)
        if sc > best:
            best = sc
            best_win = win_str
            if best >= 99.0:
                break
    return best, best_win


def build_last_index(names: List[str]) -> Dict[str, List[int]]:
    last_index: Dict[str, List[int]] = {}
    for idx, nm in enumerate(names):
        toks = _norm_tokens(nm)
        if not toks:
            continue
        last = toks[-1]
        last_index.setdefault(last, []).append(idx)
    return last_index


def guess_player_from_title(
    title: str,
    names: List[str],
    last_index: Dict[str, List[int]],
    max_candidates: int = 1500,
) -> Tuple[str, float, str]:
    title_tokens = _norm_tokens(title)
    if not title_tokens:
        return "", 0.0, ""

    cand_ids: set[int] = set()
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
        if all(t in title_tokens for t in nm_tokens):
            return nm, 100.0, " ".join(nm_tokens)
        sc, win = _best_window_score(title_tokens, nm_tokens)
        if sc > best_score:
            best_score = sc
            best_name = nm
            best_win = win

    return best_name, best_score, best_win
