"""Serial scarcity index from Bowman classifier flags (lower print run => higher scarcity)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


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


def is_serial_listing_from_bowman_flags(flags: Dict[str, Any]) -> bool:
    """
    True when the classifier treats the listing as **numbered / serial** (e.g. /99).

    Uses ``serial_out_of`` when valid, else ``is_numbered``.
    """
    _, numbered = serial_scarcity_from_flags(flags)
    if numbered:
        return True
    return bool(flags.get("is_numbered"))
