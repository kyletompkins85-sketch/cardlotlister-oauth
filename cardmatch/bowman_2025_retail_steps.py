# Cmd+F: GH_ANCHOR_BOWMAN_2025_RETAIL_STEPS_7E4A2B01
"""
First-pass 2025 Bowman (retail) listing pipeline: exclusions + checklist code match.

Step 1 aligns with docs/classification/2025_bowman_classifier_notes.md (Excluded listings).
Step 2 matches extracted checklist codes to data/checklists/normalized/2025_Bowman_card_number_lookup.csv
and scores player alignment using cardmatch.player_match.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Sequence, Tuple

from cardmatch.player_match import build_last_index, guess_player_from_title

_DEFAULT_LOOKUP = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "checklists"
    / "normalized"
    / "2025_Bowman_card_number_lookup.csv"
)


def _re(pat: str) -> re.Pattern[str]:
    return re.compile(pat, re.IGNORECASE)


def _clean(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


# --- Step 1: exclusions (retail Bowman; no Draft BD/BDC seller-header patterns) ---

_RX_COMPLETE_SET = _re(
    r"\bcomplete\s+set\b|\bset\s+complete\b|\bcomplete\b.*\bset\b"
)
_RX_PICK = _re(
    r"\b(pick\s*your|you\s*pick|u\s*pick|pick\s*one)\b"
    r"|\b(choose\s*your|choose\s*one)\b"
    r"|\bpick\s*&\s*choose\b"
    r"|\bchoose\s+from\b"
    r"|\b\d+\s+card\s+minimum\b"
    r"|\bminimum\s+\d+\s+cards?\b"
    r"|\binserts\s*-\s*.+,.+"
    r"|\bSingles\s*-\s*(?:volume|discount)"
    r"|\bParallels\s*,\s*Mojos\b"
    r"|\bChrome\s+Prospects\s+and\s+Inserts\b"
)
_RX_LOT = _re(r"\blot\b|\blots\b")
_RX_SET_BUILDER = _re(
    r"\bset\s*builder\b|\bcomplete\s+your\s+set\b|\bbuild\s+your\s+set\b"
)
_RX_PRESALE = _re(r"\bpre[\s-]?sale\b|\bpre[\s-]?order\b|\bpresale\b|\bpreorder\b")
_RX_GRADED = _re(r"\bpsa\b|\bbgs\b|\bsgc\b|\bcgc\b|\bgem\s*mint\b|\bgraded\b")


def exclusion_reason(title: str) -> str:
    """
    Return a non-empty reason string if the listing should be excluded; else "".
    """
    s = _clean(title)
    if not s:
        return "empty_title"
    if _RX_COMPLETE_SET.search(s):
        return "complete_set"
    if _RX_PICK.search(s):
        return "pick_or_volume_header"
    if _RX_SET_BUILDER.search(s):
        return "set_builder"
    if _RX_PRESALE.search(s):
        return "presale"
    if _RX_GRADED.search(s):
        return "graded_or_slab"
    if _RX_LOT.search(s):
        return "lot"
    return ""


@dataclass(frozen=True)
class ChecklistRow:
    card_number: str
    player: str
    card_type: str


def load_card_lookup(path: Path | None = None) -> Tuple[Dict[str, ChecklistRow], List[str]]:
    """Returns lookup by normalized card_number and parallel list of player names (checklist order)."""
    p = path or _DEFAULT_LOOKUP
    by_key: Dict[str, ChecklistRow] = {}
    names: List[str] = []
    with p.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            cn = (row.get("card_number") or "").strip()
            pl = (row.get("player") or "").strip()
            ct = (row.get("card_type") or "").strip()
            if not cn:
                continue
            by_key[cn] = ChecklistRow(cn, pl, ct)
            names.append(pl)
    return by_key, names


def checklist_code_prefixes(by_key: Dict[str, ChecklistRow]) -> List[str]:
    seen: set[str] = set()
    for k in by_key:
        if "-" in k:
            seen.add(k.split("-", 1)[0].upper())
    return sorted(seen, key=lambda x: (-len(x), x))


def _normalize_code(prefix: str, suffix: str) -> Optional[str]:
    pre = prefix.strip().upper()
    suf = suffix.strip().upper()
    if not pre or not suf:
        return None
    if suf.isdigit():
        return f"{pre}-{int(suf)}"
    if re.fullmatch(r"[A-Z]{2,5}", suf):
        return f"{pre}-{suf}"
    return None


def extract_checklist_codes(title: str, prefixes: Sequence[str]) -> List[str]:
    """
    Return ordered unique checklist codes found in the title.

    Uses **strict** patterns so plain words are not parsed as codes (e.g. ``Royals`` ≠ ``ROY``,
    ``base`` ≠ ``BA``, ``Baty`` ≠ ``BA`` + ``ty``, ``Cracked`` ≠ ``CRA`` + ``cked``):

    - ``PREFIX-SUFFIX`` with a real hyphen (optional spaces around the hyphen). Suffix is
      digits or 2–5 letters (initials-style auto codes).
    - ``PREFIX`` immediately followed by digits only (no hyphen), e.g. ``BCP22``, ``HS11`` —
      digits must end the run (``(?!\d)``) so we do not eat into longer numbers.
    - Base slot: ``#`` + 1–3 digits for **veteran/rookie base** checklist slots **1–100** only.
      Not followed by a serial fraction (``#116/199`` is serial, not card 116). Matches
      ``#99``, ``# 99``, not ``#11/25`` as card 11 (ambiguous; skipped).
    """
    s = _clean(title)
    if not s or not prefixes:
        return []

    alt = "|".join(re.escape(p) for p in prefixes)
    # Hyphen required — kills ROY+als, BA+se, CRA+cked, BA+ty, etc.
    rx_hyphen = re.compile(
        rf"\b({alt})\s*-\s*(\d{{1,4}}|[A-Za-z]{{2,5}})(?!\d|[A-Za-z])\b",
        re.IGNORECASE,
    )
    # Digits only, glued to prefix (no letters in suffix) — e.g. BCP22, HS11; not ROYals.
    rx_glued_digits = re.compile(
        rf"\b({alt})(\d{{1,4}})(?!\d)\b",
        re.IGNORECASE,
    )

    found: List[str] = []
    seen: set[str] = set()

    for m in rx_hyphen.finditer(s):
        key = _normalize_code(m.group(1), m.group(2))
        if key and key not in seen:
            seen.add(key)
            found.append(key)

    for m in rx_glued_digits.finditer(s):
        key = _normalize_code(m.group(1), m.group(2))
        if key and key not in seen:
            seen.add(key)
            found.append(key)

    # Base #1–#100 only (2025 Bowman retail checklist); never treat #116/199 as card 116.
    rx_hash_base = re.compile(
        r"#\s*(\d{1,3})(?!\s*[\/／⁄]\s*\d)\b",
    )
    for m in rx_hash_base.finditer(s):
        n = int(m.group(1))
        if 1 <= n <= 100:
            key = str(n)
            if key not in seen:
                seen.add(key)
                found.append(key)

    return found


_PLAYER_SCORE_OK = 55.0
_PLAYER_SCORE_STRONG = 80.0


@dataclass(frozen=True)
class MatchResult:
    match_status: str
    matched_card_number: str
    matched_player: str
    matched_card_type: str
    player_match_score: float
    extracted_codes: str


def match_listing_to_checklist(
    title: str,
    by_key: Dict[str, ChecklistRow],
    prefixes: Sequence[str],
) -> MatchResult:
    """
    Step 2: extract codes, look up rows, pick best row by player-title similarity.
    """
    codes = extract_checklist_codes(title, prefixes)
    codes_joined = "|".join(codes)

    if not codes:
        return MatchResult("unmatched_no_code", "", "", "", 0.0, "")

    best: Tuple[float, ChecklistRow, str] = (-1.0, ChecklistRow("", "", ""), "")

    for code in codes:
        row = by_key.get(code)
        if not row:
            continue
        _g_name, g_score, _g_win = guess_player_from_title(
            title, [row.player], build_last_index([row.player])
        )
        if g_score > best[0] or (abs(g_score - best[0]) <= 0.01 and len(code) > len(best[2])):
            best = (g_score, row, code)

    score, row, _winning_code = best
    if not row.card_number:
        return MatchResult("unmatched_code_not_on_checklist", "", "", "", 0.0, codes_joined)

    if score >= _PLAYER_SCORE_STRONG:
        status = "matched"
    elif score >= _PLAYER_SCORE_OK:
        status = "matched_low_confidence"
    else:
        status = "matched_player_weak"

    return MatchResult(
        status,
        row.card_number,
        row.player,
        row.card_type,
        score,
        codes_joined,
    )


def process_title(
    title: str,
    by_key: Dict[str, ChecklistRow],
    prefixes: Sequence[str],
) -> Tuple[str, MatchResult]:
    """
    Run step 1 then step 2. Returns (exclusion_reason, MatchResult).

    When excluded, match_status is ``excluded`` and identity fields are cleared (extracted_codes kept).
    """
    ex = exclusion_reason(title)
    mr = match_listing_to_checklist(title, by_key, prefixes)
    if ex:
        return ex, MatchResult(
            "excluded",
            "",
            "",
            "",
            0.0,
            mr.extracted_codes,
        )
    return "", mr


# Columns written by ``write_listings_steps12_split_by_match_status`` (human review only).
STEP2_REVIEW_COLUMNS: Tuple[str, str, str, str] = (
    "card_number",
    "player_name",
    "card_type",
    "listing",
)


def _merged_row_to_step2_review_row(row: Dict[str, str]) -> Dict[str, str]:
    """Map a listings_steps12 row to the four review columns."""
    title = (row.get("title") or "").strip()
    num = (row.get("matched_card_number") or "").strip()
    if not num:
        codes = (row.get("extracted_codes") or "").strip()
        if codes:
            num = codes.split("|", 1)[0].strip()
    return {
        "card_number": num,
        "player_name": (row.get("matched_checklist_player") or "").strip(),
        "card_type": (row.get("matched_card_type") or "").strip(),
        "listing": title,
    }


def write_listings_steps12_split_by_match_status(
    merged_csv: Path,
    out_dir: Path | None = None,
) -> Dict[str, int]:
    """
    Read ``listings_steps12.csv`` (or any CSV with ``match_status`` and the step-2 columns)
    and write one CSV per status under ``out_dir`` (default: ``<merged_csv.parent>/step2_by_match_status/``).

    Each output file has exactly: ``card_number``, ``player_name``, ``card_type``, ``listing``
    (listing text is the eBay ``title``).

    ``card_number`` uses ``matched_card_number`` when present; otherwise the first value in
    ``extracted_codes`` (pipe-separated), if any.

    Filenames: ``listings_step2_<match_status>.csv``.

    Returns row counts keyed by match_status.
    """
    merged_csv = merged_csv.resolve()
    if out_dir is None:
        out_dir = merged_csv.parent / "step2_by_match_status"
    else:
        out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    buckets: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    with merged_csv.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        fieldnames = list(r.fieldnames or [])
        if "match_status" not in fieldnames:
            raise ValueError(f"CSV missing match_status column: {merged_csv}")
        for row in r:
            st = (row.get("match_status") or "").strip() or "unknown"
            buckets[st].append(_merged_row_to_step2_review_row(dict(row)))

    out_fields = list(STEP2_REVIEW_COLUMNS)
    counts: Dict[str, int] = {}
    for status, rows in buckets.items():
        safe = re.sub(r"[^0-9a-zA-Z_.-]+", "_", status).strip("_") or "unknown"
        path = out_dir / f"listings_step2_{safe}.csv"
        with path.open("w", newline="", encoding="utf-8") as fout:
            w = csv.DictWriter(fout, fieldnames=out_fields, extrasaction="ignore")
            w.writeheader()
            for row in rows:
                w.writerow(row)
        counts[status] = len(rows)

    summary_path = out_dir / "step2_split_summary.txt"
    lines = [f"source: {merged_csv}", f"output_dir: {out_dir}", ""]
    for st in sorted(counts, key=lambda k: (-counts[k], k)):
        lines.append(f"{counts[st]}\t{st}")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return counts
