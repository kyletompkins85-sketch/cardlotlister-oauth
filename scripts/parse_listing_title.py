#!/usr/bin/env python3
"""
Parse an eBay listing title into structured fields (flat JSON).

Self-contained: stdlib only. Add new extractors to EXTRACTORS below.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple

Extractor = Callable[[str], Dict[str, Any]]

_MAX_CARD_COUNT = 10_000
_YEAR_MIN = 1980
_YEAR_MAX = 2040

# Lot / multi-card selling cues (detection only; count parsed separately).
_RX_LOTISH = re.compile(
    r"\b(?:"
    r"lot|lots|team\s+lot|player\s+lot|"
    r"bundle|bundles|bulk"
    r")\b",
    re.IGNORECASE,
)

# Seller minimum-order phrases — not the listing's card count.
_RX_CARD_MINIMUM = re.compile(
    r"\b(?:"
    r"\d{1,4}\s+cards?\s+minimum|"
    r"\d{1,4}\s*[-]?\s*card\s+minimum|"
    r"minimum\s+\d{1,4}\s+cards?"
    r")\b",
    re.IGNORECASE,
)

# Serial-style fractions near a candidate number (e.g. 12/99).
_RX_SERIAL_FRACTION = re.compile(
    r"(?<!\d)(\d{1,4})\s*[/／⁄]\s*(\d{1,4}(?:,\d{3})?)(?!\d)"
)

# Quantity patterns grouped by eBay "grammar family". First match wins within the list.
# requires_lot: only accept when the title already looks lot-ish (see _RX_LOTISH).
#
#   Tier 1 — explicit quantity markers (high confidence)
#   Tier 2 — lot-adjacent count (lot keyword directly beside the number)
#   Tier 3 — "lot/bundle of N" phrases
#   Tier 4 — count before/with lot word (N card lot, complete sets)
#   Tier 5 — multipliers (Nx)
#   Tier 6 — loose fallbacks (only with lot signal)
_CARD_COUNT_PATTERNS: List[Tuple[Pattern[str], str, bool]] = [
    # --- Tier 1: explicit quantity markers ---
    (re.compile(r"^\((\d{1,4})\)"), "leading_paren", False),
    (re.compile(r"\b(\d{1,3})\s*x\s+lot\b", re.IGNORECASE), "nx_lot", False),
    (re.compile(r"\blot\s*:\s*(\d{1,3})\s*x\b", re.IGNORECASE), "lot_colon_nx", False),
    # --- Tier 2: lot-adjacent (lot + parens, hyphen, or punctuation glue; not "lot of") ---
    # "Lot (10) …", "Lot-10 …", "Lot*36 …", "Lot#12 …"
    (re.compile(r"\blots?\s*\((\d{1,4})\)", re.IGNORECASE), "lot_paren_n", False),
    (
        re.compile(r"\blots?\s*[-–—*#×]\s*(\d{1,4})\b", re.IGNORECASE),
        "lot_glue_n",
        False,
    ),
    # --- Tier 3: lot/bundle "of N" ---
    (re.compile(r"\blot\s+of\s+\((\d{1,4})\)\s+cards?\b", re.IGNORECASE), "lot_of_paren_n_cards", False),
    (re.compile(r"\blot\s+of\s+\((\d{1,4})\)", re.IGNORECASE), "lot_of_paren_n", False),
    (re.compile(r"\blot\s+of\s+(\d{1,4})\s+cards?\b", re.IGNORECASE), "lot_of_n_cards", False),
    (re.compile(r"\blot\s+of\s+(\d{1,4})\b", re.IGNORECASE), "lot_of_n", False),
    (re.compile(r"\bbundle\s+of\s+(\d{1,4})\s+cards?\b", re.IGNORECASE), "bundle_of_n_cards", False),
    (re.compile(r"\bbundle\s+of\s+(\d{1,4})\b", re.IGNORECASE), "bundle_of_n", False),
    # --- Tier 4: count before/with lot word ---
    (re.compile(r"\blot\s+(\d{1,4})\s+cards?\b", re.IGNORECASE), "lot_n_cards", False),
    (re.compile(r"\b(\d{1,4})\s*[-]?\s*cards?\s+lot\b", re.IGNORECASE), "n_cards_lot", False),
    (re.compile(r"\b(\d{1,4})\s*[-]?\s*cards?\s+bundle\b", re.IGNORECASE), "n_cards_bundle", False),
    (re.compile(r"\bcomplete\s+(\d{1,4})\s+cards?\b", re.IGNORECASE), "complete_n_cards", False),
    (re.compile(r"\b(\d{1,4})\s+cards?\s+set\b", re.IGNORECASE), "n_cards_set", False),
    # --- Tier 5: multipliers away from "lot" ---
    (re.compile(r"\b(\d{1,3})\s*x\b", re.IGNORECASE), "nx", True),
    # --- Tier 6: loose fallbacks ---
    (re.compile(r"\b(\d{1,4})\s+cards?\b", re.IGNORECASE), "n_cards", True),
]

# Product breakdown tallies in titles: "Chrome-8", "Refractor-2" (not the lot headline count).
_RX_BREAKDOWN_BEFORE_HYPHEN = re.compile(
    r"(\w+)\s*[-–—]\s*$",
    re.IGNORECASE,
)
_BREAKDOWN_ANCHOR_WORDS = frozenset(
    {
        "lot",
        "lots",
        "bundle",
        "bundles",
    }
)

# Selling phrases with "team" that are not MLB club names.
_RX_TEAM_LOT_SCRUB = re.compile(
    r"\b(?:large\s+)?(?:player\s+)?team\s+lots?\b",
    re.IGNORECASE,
)

# MLB club aliases (longest match wins). Full names align with checklist affiliations.
_MLB_TEAM_ALIASES: Tuple[str, ...] = (
    "arizona diamondbacks",
    "atlanta braves",
    "baltimore orioles",
    "boston red sox",
    "chicago white sox",
    "chicago cubs",
    "cincinnati reds",
    "cleveland guardians",
    "colorado rockies",
    "detroit tigers",
    "houston astros",
    "kansas city royals",
    "los angeles dodgers",
    "los angeles angels",
    "miami marlins",
    "milwaukee brewers",
    "minnesota twins",
    "new york yankees",
    "new york mets",
    "oakland athletics",
    "philadelphia phillies",
    "pittsburgh pirates",
    "san diego padres",
    "san francisco giants",
    "seattle mariners",
    "st. louis cardinals",
    "st louis cardinals",
    "tampa bay rays",
    "texas rangers",
    "toronto blue jays",
    "washington nationals",
    "la dodgers",
    "la angels",
    "ny yankees",
    "ny mets",
    "sf giants",
    "diamondbacks",
    "d-backs",
    "dbacks",
    "blue jays",
    "white sox",
    "red sox",
    "guardians",
    "athletics",
    "phillies",
    "marlins",
    "braves",
    "orioles",
    "rockies",
    "brewers",
    "pirates",
    "padres",
    "rangers",
    "nationals",
    "cardinals",
    "yankees",
    "dodgers",
    "angels",
    "mariners",
    "astros",
    "cubs",
    "reds",
    "rays",
    "mets",
    "twins",
    "tigers",
    "royals",
    "giants",
    "a's",
)


def _compile_team_patterns() -> Tuple[Pattern[str], ...]:
    aliases = sorted(set(_MLB_TEAM_ALIASES), key=len, reverse=True)
    return tuple(
        re.compile(r"\b" + re.escape(alias) + r"\b", re.IGNORECASE) for alias in aliases
    )


_TEAM_PATTERNS = _compile_team_patterns()


def normalize_title(title: str) -> str:
    """Light cleanup shared by all extractors."""
    return re.sub(r"\s+", " ", (title or "").strip())


def _parse_count(raw: str) -> Optional[int]:
    try:
        n = int(raw.replace(",", ""))
    except (TypeError, ValueError):
        return None
    if 1 <= n <= _MAX_CARD_COUNT:
        return n
    return None


def _is_card_minimum_context(title: str, start: int, end: int) -> bool:
    """True when the match sits inside a 'N card minimum' seller phrase."""
    window_start = max(0, start - 20)
    window_end = min(len(title), end + 30)
    return _RX_CARD_MINIMUM.search(title[window_start:window_end]) is not None


def _is_product_year_count(count: int) -> bool:
    """Product years are never card counts (e.g. 2025 Bowman, lot of 2025 cards)."""
    return _YEAR_MIN <= count <= _YEAR_MAX


def _is_breakdown_suffix_count(title: str, start: int) -> bool:
    """
    Reject per-variant tallies like ``Chrome-8`` or ``Refractor-2``.

    Allows ``Lot-10`` because the word before the hyphen is a quantity anchor.
    """
    window = title[max(0, start - 32) : start]
    m = _RX_BREAKDOWN_BEFORE_HYPHEN.search(window)
    if not m:
        return False
    return m.group(1).lower() not in _BREAKDOWN_ANCHOR_WORDS


def _is_serial_fraction_context(title: str, start: int, end: int) -> bool:
    """
    True when the captured number is part of a serial fraction (e.g. 12/99).
    """
    for m in _RX_SERIAL_FRACTION.finditer(title):
        a_start, a_end = m.start(1), m.end(1)
        b_start, b_end = m.start(2), m.end(2)
        if a_start <= start < a_end or b_start <= start < b_end:
            return True
        if start <= a_start and end >= b_end:
            return True
    return False


def _extract_card_count_value(title: str) -> Optional[int]:
    has_lot_signal = _RX_LOTISH.search(title) is not None
    for rx, pattern_id, requires_lot in _CARD_COUNT_PATTERNS:
        if requires_lot and not has_lot_signal:
            continue
        m = rx.search(title)
        if not m:
            continue
        start, end = m.start(1), m.end(1)
        if _is_card_minimum_context(title, start, end):
            continue
        if _is_serial_fraction_context(title, start, end):
            continue
        if _is_breakdown_suffix_count(title, start):
            continue
        count = _parse_count(m.group(1))
        if count is None:
            continue
        if _is_product_year_count(count):
            continue
        return count
    return None


def _detect_is_lot(title: str, card_count: Optional[int]) -> bool:
    if _RX_LOTISH.search(title):
        return True
    if card_count is not None and card_count > 1:
        return True
    return False


def extract_card_count(title: str) -> Dict[str, Any]:
    """
    Returns is_lot and card_count.

    Singles default to card_count=1. Lots without a parseable count use null.
    """
    count = _extract_card_count_value(title)
    is_lot = _detect_is_lot(title, count)

    if count is not None:
        card_count: Optional[int] = count
    elif is_lot:
        card_count = None
    else:
        card_count = 1

    return {
        "is_lot": is_lot,
        "card_count": card_count,
    }


def _title_for_team_scan(title: str) -> str:
    """Remove 'team lot' selling phrases before club-name matching."""
    scrubbed = _RX_TEAM_LOT_SCRUB.sub(" ", title)
    return re.sub(r"\s+", " ", scrubbed).strip()


def extract_team_name(title: str) -> Dict[str, Any]:
    """Return whether the title mentions an MLB team (allowlist, longest match first)."""
    scan = _title_for_team_scan(title)
    for rx in _TEAM_PATTERNS:
        if rx.search(scan):
            return {"has_team_name": True}
    return {"has_team_name": False}


EXTRACTORS: List[Extractor] = [
    extract_card_count,
    extract_team_name,
]


def parse_listing_title(title: str) -> Dict[str, Any]:
    normalized = normalize_title(title)
    out: Dict[str, Any] = {"title": normalized}
    for extract in EXTRACTORS:
        out.update(extract(normalized))
    return out


def _run_self_tests() -> None:
    cases: List[Tuple[str, bool, Optional[int]]] = [
        ("2025 Bowman Draft LOT 10 cards Eli Willits", True, 10),
        ("lot of 5", True, 5),
        ("10-card lot rookie autos", True, 10),
        ("10 cards lot shipping included", True, 10),
        ("bundle of 3 cards", True, 3),
        ("complete 200 card set factory sealed", True, 200),
        ("2025 Topps Update US175 RC Rainbow Foil 12/99", False, 1),
        ("bdc1-bdc200,6 card minimum,20% off", False, 1),
        ("LOT rookie prospects you pick", True, None),
        ("player lot bowman chrome", True, None),
        (
            "2026 Bowman - Toronto Blue Jays LARGE Team Lot - 49 Cards Inserts Chrome Paper",
            True,
            49,
        ),
        (
            "3x Lot of 2025 Bowman Draft Paper & Prospect Chrome & Axis Insert Arjun Nimmala",
            True,
            3,
        ),
        ("lot of 2025 Bowman Draft rookie lot", True, None),
        ("lot of 2025 cards vintage warehouse", True, None),
        ("2026 card lot bowman draft", True, None),
        ("2020 cards lot bowman chrome", True, None),
        (
            "(10) 2024 2025 Bowman Draft Theo Gillen 1st Rookie Lot Tampa Bay Rays RC #BD-73",
            True,
            10,
        ),
        (
            "2025 1st Bowman Draft Steele Hall Lot of (8) - 1st Chrome and Axis Inserts",
            True,
            8,
        ),
        (
            "8x 2025 Bowman Draft MAX WILLIAMS Lot: 8x Chrome 1st Marlins",
            True,
            8,
        ),
        (
            "Lot (10) Jefferson Rojas 2025 Bowman Draft Chrome Refractor-2, Chrome-8",
            True,
            10,
        ),
        (
            "2025 Bowman Draft Liam Doyle 1st Bowman Chrome Lot (2)",
            True,
            2,
        ),
        (
            "Lot-10 Kane Kepley 2025 Bowman Draft 1st Refractor-1, 1st Chrome-4, 1st Paper-5",
            True,
            10,
        ),
        (
            "2026 Topps Bowman Chrome Top 100 Hagen Smith Braden Montgomery Lot*36 HA26",
            True,
            36,
        ),
        ("", False, 1),
        (
            "#032 - 1x Bowman+1x Chrome Black+1x Platinum Hobby+ 1x Honey Pack Break #01",
            False,
            1,
        ),
        (
            "#026 - 2026 BOWMAN SAPPHIRE BASEBALL - 1 BOX - RANDOM TEAM BREAK #7",
            False,
            1,
        ),
    ]
    for title, want_lot, want_count in cases:
        got = extract_card_count(normalize_title(title))
        assert got["is_lot"] is want_lot, (
            f"is_lot mismatch for {title!r}: got {got['is_lot']!r}, want {want_lot!r}"
        )
        assert got["card_count"] == want_count, (
            f"card_count mismatch for {title!r}: got {got['card_count']!r}, want {want_count!r}"
        )

    team_cases: List[Tuple[str, bool]] = [
        (
            "2026 Bowman - Toronto Blue Jays LARGE Team Lot - 49 Cards Inserts Chrome Paper",
            True,
        ),
        (
            "(10) 2024 2025 Bowman Draft Theo Gillen 1st Rookie Lot Tampa Bay Rays RC #BD-73",
            True,
        ),
        ("8x 2025 Bowman Draft MAX WILLIAMS Lot: 8x Chrome 1st Marlins", True),
        ("Lot (10) Jefferson Rojas 2025 Bowman Draft Chrome Refractor-2, Chrome-8", False),
        ("player lot bowman chrome", False),
        ("2025 Bowman Draft Eli Willits 1st #BD-1", False),
        ("JoJo Parker 1st Bowman Base #BD-8 - Blue Jays", True),
        ("Spencer Jones #BD-9 New York Yankees RC", True),
    ]
    for title, want_team in team_cases:
        got = extract_team_name(normalize_title(title))
        assert got["has_team_name"] is want_team, (
            f"has_team_name mismatch for {title!r}: got {got['has_team_name']!r}, "
            f"want {want_team!r}"
        )


def _emit(obj: Dict[str, Any], *, pretty: bool) -> None:
    if pretty:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(obj, ensure_ascii=False))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Parse an eBay listing title into structured flat JSON."
    )
    ap.add_argument("--title", default="", help="Listing title string.")
    ap.add_argument(
        "--file",
        default="",
        help="Path to a text file with one title per line (outputs JSONL).",
    )
    ap.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON (single title) or indented JSONL objects.",
    )
    ap.add_argument(
        "--test",
        action="store_true",
        help="Run built-in extractor self-tests and exit.",
    )
    args = ap.parse_args(argv)

    if args.test:
        _run_self_tests()
        print("ok", file=sys.stderr)
        return 0

    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            print(f"Could not read file: {e}", file=sys.stderr)
            return 1
        for line in lines:
            # One JSON object per input line (batch callers rely on 1:1 mapping).
            title = line.rstrip("\n\r")
            _emit(parse_listing_title(title.strip()), pretty=args.pretty)
        return 0

    title = (args.title or "").strip()
    if not title and not sys.stdin.isatty():
        title = sys.stdin.read().strip()

    if not title:
        ap.print_help(file=sys.stderr)
        return 2

    _emit(parse_listing_title(title), pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
