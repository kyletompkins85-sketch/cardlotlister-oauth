from __future__ import annotations

import re
import unicodedata
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
    "insert",
    "axis",
    "giants",
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


def _expand_de_prefix_tokens(
    title_tokens: List[str],
    last_index: Dict[str, List[int]],
) -> List[str]:
    """
    eBay titles often lowercase Dutch particles: 'leo devries' vs checklist 'Leo De Vries'.
    expand_concatenated_names only splits De+V when V is uppercase (DeVries → De Vries).
    If a token is 'de' + suffix and suffix is a known checklist last name, emit de + suffix.
    """
    out: List[str] = []
    for t in title_tokens:
        if len(t) >= 5 and t.startswith("de") and t[2:].isalpha() and t[2:] in last_index:
            out.append("de")
            out.append(t[2:])
        else:
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


def _candidate_ids_from_fuzzy_lastname(
    title_tokens: List[str],
    last_index: Dict[str, List[int]],
    *,
    min_tok_len: int = 4,
    min_last_len: int = 4,
    min_ratio: float = 88.0,
) -> set[int]:
    """
    When no title token exactly matches a checklist last name (eBay typos: Gonalez vs Gonzalez),
    add player indices whose last name fuzzy-matches a title token.
    """
    cand_ids: set[int] = set()
    for tok in title_tokens:
        if len(tok) < min_tok_len:
            continue
        for last, ids in last_index.items():
            if len(last) < min_last_len:
                continue
            if tok == last:
                continue
            if _ratio(tok, last) >= min_ratio:
                cand_ids.update(ids)
    return cand_ids


def expand_concatenated_names(s: str) -> str:
    """
    Split FirstLast run together (e.g. WalkerJenkins → Walker Jenkins) so tokens match checklist.
    Skips Mc*/Mac* surnames (McDonald, MacDonald) where a lowercase letter precedes the surname.
    """
    if not s:
        return s

    def repl(m) -> str:
        i = m.start(1)
        # McDonald / John McDonald — c before D; char before c is M
        if m.group(1) == "c" and i >= 1 and s[i - 1] == "M":
            return m.group(0)
        # MacDonald — "Mac" + Donald
        if i >= 2 and len(s) >= i + 1 and s[i - 2 : i + 1].lower() == "mac":
            return m.group(0)
        return m.group(1) + " " + m.group(2)

    return re.sub(r"([a-z])([A-Z][a-z]{2,})", repl, s)


def _eval_candidate_ids(
    cand_ids: set[int],
    title_tokens: List[str],
    names: List[str],
) -> Tuple[str, float, str]:
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


# If exact last-name hits are wrong (noisy tokens), fuzzy typo matches can still win.
_FUZZY_SUPPLEMENT_BELOW_SCORE = 85.0


def guess_player_from_title(
    title: str,
    names: List[str],
    last_index: Dict[str, List[int]],
    max_candidates: int = 1500,
) -> Tuple[str, float, str]:
    title = unicodedata.normalize("NFKC", (title or "").strip())
    title = expand_concatenated_names(title)
    title_tokens = _norm_tokens(title)
    title_tokens = _expand_de_prefix_tokens(title_tokens, last_index)
    if not title_tokens:
        return "", 0.0, ""

    cand_ids: set[int] = set()
    for tok in title_tokens:
        # Single-letter tokens (e.g. "a" from "#A-17" word-split) match bogus last-name keys.
        if len(tok) < 2:
            continue
        ids = last_index.get(tok)
        if ids:
            for i in ids:
                cand_ids.add(i)
        if len(cand_ids) >= max_candidates:
            break

    if not cand_ids:
        cand_ids = _candidate_ids_from_fuzzy_lastname(title_tokens, last_index)

    if not cand_ids:
        return "", 0.0, ""

    best_name, best_score, best_win = _eval_candidate_ids(cand_ids, title_tokens, names)

    if best_score < _FUZZY_SUPPLEMENT_BELOW_SCORE:
        extra = _candidate_ids_from_fuzzy_lastname(title_tokens, last_index)
        merged = cand_ids | extra
        if len(merged) > len(cand_ids):
            best_name, best_score, best_win = _eval_candidate_ids(merged, title_tokens, names)

    return best_name, best_score, best_win
