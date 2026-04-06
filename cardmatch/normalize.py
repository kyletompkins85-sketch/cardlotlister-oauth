from __future__ import annotations

import re
from typing import List, Tuple

# Longer phrases first so we do not leave half-phrases behind.
_ABRIDGE_PATTERNS: List[Tuple[str, str]] = [
    (r"(?i)\b2025\s+bowman\s+draft\s+baseball\b", ""),
    (r"(?i)\b2025\s+bowman\s+draft\s+chrome\b", ""),
    (r"(?i)\b2025\s+bowman\s+chrome\s+draft\b", ""),
    (r"(?i)\b2025\s+bowman\s+draft\b", ""),
    # "2025 Bowman Draft1st" (no space before "1st")
    (r"(?i)\b2025\s+bowman\s+draft(?=\d)", ""),
    (r"(?i)\bbowman\s+chrome\s+draft\b", ""),
    (r"(?i)\bbowman\s+draft\b", ""),
]


def normalize_title(s: str) -> str:
    return (s or "").strip()


def abridge_listing_title(s: str) -> str:
    """
    Shorten seller titles for review CSVs by dropping repeated product boilerplate
    (e.g. '2025 Bowman Draft') while keeping the rest of the wording.
    """
    t = (s or "").strip()
    for pat, rep in _ABRIDGE_PATTERNS:
        t = re.sub(pat, rep, t)
    t = re.sub(r"^\s*[|•·\-\s–—]+", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -–—|")
    return t.strip()
