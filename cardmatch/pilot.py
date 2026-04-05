from __future__ import annotations

from typing import Any, Dict, List, Tuple

from cardmatch.bowman_z10 import classify_bowman_title
from cardmatch.normalize import normalize_title
from cardmatch.player_match import guess_player_from_title
from cardmatch.types import MATCHER_VERSION, PilotResult, PlayerStatus


# Below this fuzzy score, treat player as unknown (tunable).
PLAYER_MATCH_MIN_SCORE = 55.0

# Second-best within this gap => ambiguous (if we tracked second best — skip for v0.1)


def _likely_base_from_flags(flags: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    True when title looks like a base stock card (paper or chrome) without
    inserts/parallels/autos/serials. Graded slabs still allowed.
    """
    reasons: List[str] = []

    if flags.get("WF_lot"):
        reasons.append("lot")
    if flags.get("WF_pick") or flags.get("WF_set_builder"):
        reasons.append("pick_or_set_builder")
    if flags.get("WF_complete_set"):
        reasons.append("complete_set")
    if flags.get("WF_presale"):
        reasons.append("presale")
    if flags.get("WF_auto"):
        reasons.append("auto")
    if flags.get("WF_prized_prospect"):
        reasons.append("prized_prospect")
    if flags.get("WF_refractor"):
        reasons.append("refractor")
    if flags.get("WF_superfractor"):
        reasons.append("superfractor")
    if flags.get("WF_shimmer"):
        reasons.append("shimmer")
    if flags.get("WF_speckle"):
        reasons.append("speckle")
    if flags.get("WF_wave"):
        reasons.append("wave")
    if flags.get("WF_mojo"):
        reasons.append("mojo")
    if flags.get("WF_lava"):
        reasons.append("lava")
    if flags.get("WF_printing_plate"):
        reasons.append("printing_plate")
    if flags.get("is_numbered"):
        reasons.append("numbered_serial")

    likely = len(reasons) == 0
    return likely, reasons


def match_pilot(
    title: str,
    names: List[str],
    last_index: Dict[str, List[int]],
) -> PilotResult:
    s = normalize_title(title)
    flags = classify_bowman_title(s)
    likely_base, nb_reasons = _likely_base_from_flags(flags)

    guess, score, win = guess_player_from_title(s, names, last_index)

    reason_codes: List[str] = []
    pstatus: PlayerStatus
    if not guess or score < PLAYER_MATCH_MIN_SCORE:
        pstatus = "unknown"
        reason_codes.append("player_below_threshold")
        if not guess:
            reason_codes.append("no_player_candidate")
    else:
        pstatus = "matched"
        if score < 85.0:
            reason_codes.append("player_low_confidence")

    if not likely_base:
        reason_codes.append("not_likely_base")
        for r in nb_reasons:
            reason_codes.append(f"nb_{r}")

    return PilotResult(
        player_guess=guess if pstatus == "matched" else "",
        player_score=score,
        player_status=pstatus,
        matched_window=win,
        is_likely_base=likely_base,
        reason_codes=reason_codes,
        matcher_version=MATCHER_VERSION,
        bowman_flags=dict(flags),
    )
