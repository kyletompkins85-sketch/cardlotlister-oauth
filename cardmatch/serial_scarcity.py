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
