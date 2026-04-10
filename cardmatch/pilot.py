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
    True when title looks like **paper** base (BD-*) only — not Chrome product/stock.
    Any Chrome branding (WF_chrome) or BDC-# (WF_bdc) is out of scope for this “base”.
    Chrome prospect base (BDC-*) is excluded — parallels/inserts flags as before.
    Graded slabs (PSA/BGS/SGC/… or explicit “graded”) are out of scope for likely base.
    Multi-unit / lot listings (WF_lot) are out of scope — not a single raw card review target.
    Bowman Draft Night inserts (WF_draft_night) are a separate product — not paper BD-* base.
    Paper orange-border / Base-Orange style parallels (WF_orange_border) are not plain paper base.
    """
    reasons: List[str] = []

    if flags.get("WF_graded"):
        reasons.append("graded")
    if flags.get("WF_orange_border"):
        reasons.append("orange_border")
    if flags.get("WF_sky_blue"):
        reasons.append("sky_blue")
    if flags.get("WF_snack_pack"):
        reasons.append("snack_pack")
    if flags.get("WF_mini_diamond"):
        reasons.append("mini_diamond")
    if flags.get("WF_aqua"):
        reasons.append("aqua")
    if flags.get("WF_sparkle"):
        reasons.append("sparkle")
    if flags.get("WF_blue_geometric"):
        reasons.append("blue_geometric")
    if flags.get("WF_chrome"):
        reasons.append("chrome")
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
    if flags.get("WF_chrome_prospect_autographs"):
        reasons.append("chrome_prospect_autographs")
    if flags.get("WF_prized_prospect"):
        reasons.append("prized_prospect")
    if flags.get("WF_axis"):
        reasons.append("axis")
    if flags.get("WF_draft_night"):
        reasons.append("draft_night")
    if flags.get("WF_final_draft"):
        reasons.append("final_draft")
    if flags.get("WF_bdc"):
        reasons.append("bdc")
    if flags.get("WF_bowman_in_action"):
        reasons.append("bowman_in_action")
    if flags.get("WF_image_variation"):
        reasons.append("image_variation")
    if flags.get("WF_college_variation"):
        reasons.append("college_variation")
    if flags.get("WF_bowman_spotlight"):
        reasons.append("bowman_spotlight")
    if flags.get("WF_etched_in_glass"):
        reasons.append("etched_in_glass")
    if flags.get("WF_sapphire"):
        reasons.append("sapphire")
    if flags.get("WF_crystallized"):
        reasons.append("crystallized")
    if flags.get("WF_x_fractor"):
        reasons.append("x_fractor")
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
    # WF_mojo is intentionally not appended — nb_mojo was mislabeled as Blue in card_type legacy.
    if flags.get("WF_lava"):
        reasons.append("lava")
    if flags.get("WF_printing_plate"):
        reasons.append("printing_plate")
    if flags.get("is_numbered"):
        reasons.append("numbered_serial")

    likely = len(reasons) == 0
    return likely, reasons


# BDC chrome prospect base (no parallels / inserts beyond chrome + BDC stock).
_CHROME_BASE_REASONS_OK = frozenset({"chrome", "bdc"})


def _is_likely_chrome_base(nb_reasons: List[str]) -> bool:
    s = set(nb_reasons)
    if "bdc" not in s:
        return False
    return s <= _CHROME_BASE_REASONS_OK


def match_pilot(
    title: str,
    names: List[str],
    last_index: Dict[str, List[int]],
) -> PilotResult:
    s = normalize_title(title)
    flags = classify_bowman_title(s)
    is_graded = bool(flags.get("WF_graded"))
    is_lot = bool(flags.get("WF_lot"))
    is_draft_night = bool(flags.get("WF_draft_night"))
    is_chrome = bool(flags.get("WF_chrome"))
    is_orange_border = bool(flags.get("WF_orange_border"))
    likely_base, nb_reasons = _likely_base_from_flags(flags)
    if flags.get("WF_mojo"):
        likely_base = False
    is_likely_chrome_base = _is_likely_chrome_base(nb_reasons)
    is_snack_pack = bool(flags.get("WF_snack_pack"))
    is_axis = bool(flags.get("WF_axis"))

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
        is_graded=is_graded,
        is_lot=is_lot,
        is_draft_night=is_draft_night,
        is_chrome=is_chrome,
        is_orange_border=is_orange_border,
        is_likely_chrome_base=is_likely_chrome_base,
        is_snack_pack=is_snack_pack,
        is_axis=is_axis,
        reason_codes=reason_codes,
        matcher_version=MATCHER_VERSION,
        bowman_flags=dict(flags),
    )
