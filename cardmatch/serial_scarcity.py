"""Serial scarcity index from Bowman classifier flags (lower print run => higher scarcity)."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# eBay-style print runs: Green /99, Speckle /1, etc.
_RE_SLASH_PRINT_RUN = re.compile(r"/\s*(\d{1,6})\b")
# Fractional serials: 1/1, 5/5, 12/25, 37/50, 014/150
_RE_FRACTION_SERIAL = re.compile(r"(?:^|[^\d/])(\d{1,6})\s*/\s*(\d{1,6})\b")
# "#99", "# /99" style (print run without relying on classifier)
_RE_HASH_NUMBERED = re.compile(r"#\s*/?\s*(\d{2,6})\b")


def serial_scarcity_from_flags(flags: Dict[str, Any]) -> Tuple[Optional[float], bool]:
    """
    Return ``(1/serial_out_of, True)`` when numbered, else ``(None, False)``.
    Caller imputes missing values (e.g. median over training rows).
    """
    so = flags.get("serial_out_of")
    if so is None:
        return None, False
    try:
        n = int(so)
    except (TypeError, ValueError):
        return None, False
    if n <= 0:
        return None, False
    return 1.0 / float(n), True


def _normalize_title_for_serial_scan(title: str) -> str:
    """
    Copy-pasted listings often use fullwidth slash (U+FF0F) or fraction slash (U+2044) instead of
    ASCII ``/``, which would otherwise miss print-run patterns.
    """
    t = (title or "").strip()
    if not t:
        return ""
    t = t.replace("\uFF0F", "/")  # fullwidth solidus ／
    t = t.replace("\u2044", "/")  # fraction slash ⁄
    return t


def _title_suggests_serial_numbering(title: str) -> bool:
    """
    Heuristic when ``serial_out_of`` / ``is_numbered`` are missing: detect ``/N`` print runs and
    ``a/b`` serials (e.g. ``/1``, ``/10``, ``1/1``). Skips 4-digit values in 2000–2035 after
    ``/`` (common year noise in titles).
    """
    s = _normalize_title_for_serial_scan(title)
    if not s:
        return False
    if _RE_HASH_NUMBERED.search(s):
        return True
    if _RE_FRACTION_SERIAL.search(s):
        return True
    for m in _RE_SLASH_PRINT_RUN.finditer(s):
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        if 2000 <= n <= 2035:
            continue
        return True
    return False


def is_serial_listing_from_bowman_flags(
    flags: Dict[str, Any],
    title: Optional[str] = None,
) -> bool:
    """
    True when the listing is treated as **numbered / serial** (e.g. /99, 1/1).

    Uses ``serial_out_of`` when valid, then ``is_numbered``, then a **title** fallback
    (``/N`` print runs and ``a/b`` patterns) when ``title`` is provided.
    """
    _, numbered = serial_scarcity_from_flags(flags)
    if numbered:
        return True
    if bool(flags.get("is_numbered")):
        return True
    if title is not None and _title_suggests_serial_numbering(title):
        return True
    return False
