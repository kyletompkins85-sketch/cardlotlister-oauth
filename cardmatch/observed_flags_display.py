"""
Human-readable card type strings for observed-flags API responses.

Internal classification still uses full taxonomy strings; this layer only shapes labels
returned to clients.
"""

from __future__ import annotations

from cardmatch.taxonomy import BDC_PRIMARY_FAMILY

_LEGACY_BDC_PREFIX = "BDC Chrome Prospect"
_DRAFT_NIGHT_PREFIX = "Bowman Draft Night"


def _is_chrome_primary_bdc(t: str) -> bool:
    """True for canonical **Chrome · …** / **Chrome /…** BDC lines (not **Chrome Prospect College Variations**)."""
    if t.startswith("Chrome Prospect College Variations"):
        return False
    return t == BDC_PRIMARY_FAMILY or t.startswith(f"{BDC_PRIMARY_FAMILY} · ") or t.startswith(
        f"{BDC_PRIMARY_FAMILY} /"
    )


def short_card_type_display_for_api(card_type: str) -> str:
    """
    Shorten verbose product labels for API responses (internal taxonomy unchanged).

    - ``Base-Paper`` → ``base``; ``Base-Paper · …`` → ``base · …``
    - ``Bowman Draft Night · …`` → ``Draft Night …`` (drops redundant **Bowman**)
    - ``Chrome · Base`` → ``Chrome``; ``Chrome · Auto`` / ``Chrome · Auto · …`` → ``Chrome Auto`` /
      ``Chrome Auto …``; other parallels → ``Chrome …``
    """
    t = (card_type or "").strip()
    if not t:
        return ""
    if t.startswith(_LEGACY_BDC_PREFIX):
        t = BDC_PRIMARY_FAMILY + t[len(_LEGACY_BDC_PREFIX) :]
    if t == "Base-Paper":
        return "base"
    if t.startswith("Base-Paper · "):
        return "base · " + t[len("Base-Paper · ") :]
    if t.startswith(_DRAFT_NIGHT_PREFIX):
        rest = t[len(_DRAFT_NIGHT_PREFIX) :].lstrip()
        if rest.startswith("·"):
            rest = rest[1:].lstrip()
        if not rest:
            return "Draft Night"
        return f"Draft Night {rest}"
    if t.startswith("Chrome Prospect College Variations"):
        return t
    if not _is_chrome_primary_bdc(t):
        return t
    rest = t[len(BDC_PRIMARY_FAMILY) :].lstrip()
    if rest.startswith("·"):
        rest = rest[1:].lstrip()
    if not rest:
        return "Chrome"
    if rest == "Base":
        return "Chrome"
    if rest == "Auto":
        return "Chrome Auto"
    if rest.startswith("Auto · "):
        tail = rest[len("Auto · ") :].lstrip()
        return f"Chrome Auto {tail}" if tail else "Chrome Auto"
    if rest.startswith("Auto "):
        return "Chrome Auto " + rest[len("Auto ") :].lstrip()
    return f"Chrome {rest}"
