# NEW FILE
# workflows/pull_comps_for_largest_listings/_title_features.py

from __future__ import annotations

import re
from typing import Optional

# Matches common “numbered/serial” patterns seen in card titles:
# - "/99", "/ 99", " /99"
# - "#/50", "# / 50"
# - "No. 12/99" (still contains /99)
# - We intentionally avoid matching dates like 2024/25 by requiring small-ish denom.
#
# Tweak denom_max if you want stricter/looser.
_DENOM_MAX_DEFAULT = 5000

_RE_HASH_SLASH = re.compile(r"#\s*/\s*(\d{1,5})", re.IGNORECASE)         # "#/50", "# / 50"
_RE_BARE_SLASH = re.compile(r"(?<!\d)\s*/\s*(\d{1,5})(?!\d)", re.IGNORECASE)  # "/99" not preceded by digit


def is_numbered(title: str, denom_max: int = _DENOM_MAX_DEFAULT) -> bool:
    t = (title or "").strip()
    if not t:
        return False

    # 1) Prefer explicit "#/NN"
    m = _RE_HASH_SLASH.search(t)
    if m:
        denom = _safe_int(m.group(1))
        return bool(denom and 1 <= denom <= denom_max)

    # 2) Otherwise, accept a bare "/NN" where denom looks plausible.
    #    This catches "/10", "/25", "/99", etc.
    m = _RE_BARE_SLASH.search(t)
    if m:
        denom = _safe_int(m.group(1))
        return bool(denom and 1 <= denom <= denom_max)

    return False


def _safe_int(x: Optional[str]) -> Optional[int]:
    if not x:
        return None
    try:
        return int(str(x).strip())
    except Exception:
        return None
