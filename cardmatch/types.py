from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

MATCHER_VERSION = "0.1.23-pilot"

PlayerStatus = Literal["matched", "unknown", "ambiguous"]


@dataclass
class PilotResult:
    """Phase-1 pilot: player guess + likely base (not a full checklist row)."""

    player_guess: str
    player_score: float
    player_status: PlayerStatus
    matched_window: str
    is_likely_base: bool
    is_graded: bool = False
    is_lot: bool = False
    is_draft_night: bool = False
    is_chrome: bool = False
    is_orange_border: bool = False
    is_likely_chrome_base: bool = False
    is_snack_pack: bool = False
    is_axis: bool = False
    reason_codes: List[str] = field(default_factory=list)
    matcher_version: str = MATCHER_VERSION
    bowman_flags: Dict[str, Any] = field(default_factory=dict)
