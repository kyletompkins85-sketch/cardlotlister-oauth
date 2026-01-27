# workflows/pull_comps_for_largest_listings/99_title_features.py

from __future__ import annotations

import re
from typing import Optional

# Matches common serial-number cues in card titles, e.g.
# "/99", " / 99", "#/50", "No. 12/25", "12 / 25", etc.
_NUMBERED_RE = re.compile(
    r"""
    (?ix)                            # ignore case, verbose
    (?:\#\s*/\s*\d{1,5})              # "#/50"
    |
    (?:\b\d{1,5}\s*/\s*\d{1,5}\b)     # "12/25" or "12 / 25"
    |
    (?:\b/\s*\d{1,5}\b)              # "/99" (standalone slash form)
    """,
    re.VERBOSE | re.IGNORECASE,
)

def is_numbered(title: Optional[str]) -> bool:
    """
    Returns True if title looks like a serial-numbered card.
    Designed to be fast and conservative (few false positives).
    """
    t = (title or "").strip()
    if not t:
        return False
    return _NUMBERED_RE.search(t) is not None
