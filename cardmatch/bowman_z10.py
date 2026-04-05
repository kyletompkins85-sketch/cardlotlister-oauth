"""Load Bowman listing classifier from workflows (no duplication of regex tables)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Callable

_CLASSIFY: Callable[[str], Dict[str, Any]] | None = None


def classify_bowman_title(title: str) -> Dict[str, Any]:
    global _CLASSIFY
    if _CLASSIFY is None:
        root = Path(__file__).resolve().parents[1]
        wf = root / "workflows" / "product_player_price_rankings"
        p = str(wf)
        if p not in sys.path:
            sys.path.insert(0, p)
        from z10_bowman_listing_classifier import classify_title  # type: ignore

        _CLASSIFY = classify_title
    return _CLASSIFY(title)
