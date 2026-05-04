# Cmd+F: GH_ANCHOR_BOWMAN_2025_LISTING_DISPLAY
"""
Human-facing ``listing_display`` text for 2025 Bowman retail review CSVs.

Phrases are applied **longest first** so longer team strings win before shorter nicknames/cities.
Order: (1) team / city phrases, (2) RC / rookie fluff, (3) drop low-signal whole words (``2025``,
``Bowman`` / ``Bowman's``, ``Prospects`` / ``Prospect``, standalone ``1st``, ``baseball``, ``shipping``,
``edition``, ``Topps``) while **keeping** ``Chrome``; (4) remove ``!`` and hyphen-with-spaces glue
(`` - ``); (5) when ``card_number`` is passed, prefix ``card_number``, then an optional **Chrome**
cue (``Chrome`` plus **product** follow-ons Mega / Mojo / Anime only — parallel modifiers like
Sapphire stay in the tail), then ``/serial``, then the cleaned remainder.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Final, Optional, Tuple

from cardmatch.bowman_2025_retail_flags import checklist_slot_int, serial_out_of_for_title

_WS_COLLAPSE = re.compile(r"\s+")

# One phrase per line; sorted longest-first at import so subsets (e.g. *Sox*, *San Diego*) run after wholes.
_RAW_TEAM_AND_CITY_PHRASES: Final[str] = """
Los Angeles Dodgers
Los Angeles Angels
New York Yankees
New York Mets
Chicago White Sox
Chicago Cubs
Kansas City Royals
San Francisco Giants
San Diego Padres
Tampa Bay Rays
St. Louis Cardinals
St Louis Cardinals
Toronto Blue Jays
Boston Red Sox
Baltimore Orioles
Washington Nationals
Philadelphia Phillies
Pittsburgh Pirates
Cleveland Guardians
Cleveland Indians
Cincinnati Reds
Detroit Tigers
Milwaukee Brewers
Minnesota Twins
Houston Astros
Texas Rangers
Atlanta Braves
Miami Marlins
Florida Marlins
Oakland Athletics
Seattle Mariners
Colorado Rockies
Arizona Diamondbacks
Los Angeles
San Francisco
San Diego
Kansas City
Tampa Bay
St. Louis
St Louis
New York
Philadelphia
Pittsburgh
Cleveland
Cincinnati
Baltimore
Milwaukee
Minneapolis
Houston
Oakland
Seattle
Denver
Phoenix
Arlington
Atlanta
Boston
Miami
Toronto
Chicago
Detroit
Blue Jays
White Sox
Red Sox
Diamondbacks
Nationals
Cardinals
Rockies
Athletics
Braves
Brewers
Dodgers
Angels
Giants
Indians
Guardians
Mariners
Marlins
Mets
Orioles
Padres
Phillies
Pirates
Rangers
Rays
Reds
Royals
Tigers
Twins
Yankees
Cubs
Sox
Nats
Jays
O's
"""

_RX_ROOKIE_FLUFF = re.compile(
    r"\b(?:RC|Rookie\s+Card|1st\s+Bowman)\b",
    re.IGNORECASE,
)

_RX_YEAR_2025 = re.compile(r"\b2025\b", re.IGNORECASE)
_RX_BOWMAN_WORD = re.compile(r"\bBowman(?:'s)?\b", re.IGNORECASE)
_RX_PROSPECTS_WORD = re.compile(r"\bProspects\b", re.IGNORECASE)
_RX_PROSPECT_WORD = re.compile(r"\bProspect\b", re.IGNORECASE)
_RX_1ST_STANDALONE = re.compile(r"\b1st\b", re.IGNORECASE)
_RX_BASEBALL = re.compile(r"\bbaseball\b", re.IGNORECASE)
_RX_SHIPPING = re.compile(r"\bshipping\b", re.IGNORECASE)
_RX_EDITION = re.compile(r"\bedition\b", re.IGNORECASE)
_RX_TOPPS = re.compile(r"\bTopps\b", re.IGNORECASE)
_RX_SPACED_HYPHEN = re.compile(r"\s+-\s+")
_RX_BANG = re.compile(r"!+")
_RX_LEADING_GLUE_HYPHEN = re.compile(r"^\s*-\s+")


def _phrase_regex(phrase: str) -> re.Pattern[str]:
    """Whole phrase, flexible internal whitespace, case-insensitive."""
    parts = phrase.split()
    if not parts:
        return re.compile(r"(?!x)x")
    core = r"\s+".join(re.escape(p) for p in parts)
    return re.compile(rf"(?i)\b{core}\b")


def _sorted_unique_phrases(lines: str) -> Tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for ln in lines.splitlines():
        p = ln.strip()
        if not p or p in seen:
            continue
        seen.add(p)
        out.append(p)
    out.sort(key=len, reverse=True)
    return tuple(out)


_TEAM_RX: Tuple[re.Pattern[str], ...] = tuple(
    _phrase_regex(p) for p in _sorted_unique_phrases(_RAW_TEAM_AND_CITY_PHRASES)
)


def _collapse_ws(s: str) -> str:
    return _WS_COLLAPSE.sub(" ", s).strip()


def _compile_code_strip_patterns(card_number: str) -> Tuple[re.Pattern[str], ...]:
    """Remove checklist code spellings from the cleaned body when prefixing that code."""
    cn = card_number.strip().upper()
    if not cn:
        return ()
    pats: list[str] = []
    m = re.match(r"^([A-Z]{1,12})-(.+)$", cn)
    if m:
        pre, suf = m.group(1), m.group(2)
        pe = re.escape(pre)
        if suf.isdigit():
            d = int(suf)
            pats.extend(
                [
                    rf"(?i)#?\s*{pe}\s*-\s*{d}\b",
                    rf"(?i)\b{pe}\s*-\s*{d}\b",
                    rf"(?i)\b{pe}{d}\b",
                ]
            )
        else:
            se = re.escape(suf.upper())
            pats.extend([rf"(?i)\b{pe}\s*-\s*{se}\b", rf"(?i)\b{pe}{se}\b"])
    elif cn.isdigit():
        n = int(cn)
        pats.append(rf"(?i)#\s*{n}(?!\s*[\/／⁄]\s*\d)")
    return tuple(re.compile(p) for p in pats)


def _strip_card_code_mentions(body: str, card_number: str) -> str:
    s = body
    for rx in _compile_code_strip_patterns(card_number):
        s = rx.sub(" ", s)
    return _collapse_ws(s)


def _strip_serial_mentions(body: str, denom: int) -> str:
    de = str(int(denom))
    s = re.sub(rf"(?i)#\s*/\s*{re.escape(de)}\b", " ", body)
    s = re.sub(rf"(?i)\b\d{{1,6}}\s*/\s*{re.escape(de)}\b", " ", s)
    s = re.sub(rf"(?<![\d/])\s*/\s*{re.escape(de)}\b", " ", s)
    return _collapse_ws(s)


_RX_CHROME_PHRASE = re.compile(
    r"(?i)\bchrome\b(?:\s+(?:mega|mojo|anime)\b)?"
)


def _title_case_words(s: str) -> str:
    parts = s.split()
    return " ".join((w[:1].upper() + w[1:].lower()) if w else w for w in parts)


def _peel_chrome_segment(body: str) -> tuple[str, str]:
    """First ``Chrome`` (optional Mega / Mojo / Anime product line only); remove that span from body."""
    m = _RX_CHROME_PHRASE.search(body)
    if not m:
        return "", body
    seg = _title_case_words(m.group(0))
    left = body[: m.start()] + " " + body[m.end() :]
    return seg, _collapse_ws(left)


def _reorder_with_card_and_serial(body: str, card_number: str, raw_title: str) -> str:
    cn = card_number.strip()
    if not cn:
        return body
    slot = checklist_slot_int(cn)
    denom = serial_out_of_for_title(raw_title, slot)
    chrome_seg, after_chrome = _peel_chrome_segment(body)
    rest = _strip_card_code_mentions(after_chrome, cn)
    if denom is not None:
        rest = _strip_serial_mentions(rest, denom)
    head: list[str] = [cn]
    if chrome_seg:
        head.append(chrome_seg)
    if denom is not None:
        head.append(f"/{denom}")
    if not rest:
        return " ".join(head)
    return " ".join([*head, rest])


def listing_display_from_title(title: str, *, card_number: Optional[str] = None) -> str:
    """
    Strip low-signal wording for review CSV ``listing_display`` (full ``title`` stays in ``listing``).

    1. Remove MLB team / common city fragments (longest matching phrases first).
    2. Remove ``RC``, ``Rookie Card``, ``1st Bowman``.
    3. Remove whole words ``2025``, ``Bowman`` / ``Bowman's``, ``Prospects``, ``Prospect``,
       standalone ``1st``, ``baseball``, ``shipping``, ``edition``, ``Topps`` — ``Chrome`` is never
       removed by these rules.
    4. Remove ``!`` and spaced-hyphen glue (`` - `` → space).
    5. When ``card_number`` is set, output ``<card_number> <Chrome…?> [/serial] <rest>`` using the
       same serial parse as the step-3 column (raw ``title`` + slot-aware ``serial_out_of_for_title``).
    """
    raw = unicodedata.normalize("NFKC", (title or "").strip())
    if not raw:
        return ""
    s = raw
    for rx in _TEAM_RX:
        s = rx.sub(" ", s)
    s = _RX_ROOKIE_FLUFF.sub(" ", s)
    s = _RX_1ST_STANDALONE.sub(" ", s)
    s = _RX_YEAR_2025.sub(" ", s)
    s = _RX_BOWMAN_WORD.sub(" ", s)
    s = _RX_PROSPECTS_WORD.sub(" ", s)
    s = _RX_PROSPECT_WORD.sub(" ", s)
    s = _RX_BASEBALL.sub(" ", s)
    s = _RX_SHIPPING.sub(" ", s)
    s = _RX_EDITION.sub(" ", s)
    s = _RX_TOPPS.sub(" ", s)
    s = _RX_BANG.sub(" ", s)
    s = _RX_SPACED_HYPHEN.sub(" ", s)
    s = _collapse_ws(s)
    s = _RX_LEADING_GLUE_HYPHEN.sub("", s)
    s = s.strip()
    if not s:
        return ""
    cn = (card_number or "").strip()
    if cn:
        return _reorder_with_card_and_serial(s, cn, raw)
    return s
