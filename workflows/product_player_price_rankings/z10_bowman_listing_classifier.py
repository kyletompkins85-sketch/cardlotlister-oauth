# Cmd+F: GH_ANCHOR_BOWMAN_LISTING_CLASSIFIER_3F8A2C11
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


# -----------------------------
# Regex helpers
# -----------------------------
def _re(pat: str) -> re.Pattern:
    return re.compile(pat, re.IGNORECASE)

def _has(rx: re.Pattern, s: str) -> bool:
    return rx.search(s) is not None

def _clean(s: str) -> str:
    return (s or "").strip()


# -----------------------------
# Core patterns (Bowman-focused)
# -----------------------------
# Cmd+F: GH_ANCHOR_BOWMAN_PATTERNS_9C21A0B3

# Selling formats (exclude/bucket)
RX_COMPLETE_SET = _re(r"\bcomplete\s+set\b|\bset\s+complete\b")
RX_PICK         = _re(r"\b(pick\s*your|you\s*pick|pick\s*one|pick)\b|\b(choose\s*your|choose\s*one|choose)\b")
RX_LOT          = _re(r"\blot\b|\blots\b")
RX_SET_BUILDER  = _re(r"\bset\s*builder\b|\bcomplete\s+your\s+set\b")
RX_PRESALE      = _re(r"\bpre[\s-]?sale\b|\bpre[\s-]?order\b|\bpresale\b|\bpreorder\b")

# Bowman / card stock cues
RX_CHROME = _re(r"\bchrome\b")
RX_PAPER  = _re(r"\bpaper\b|\bbase\b")  # Bowman listings often omit "paper"; base can help

# Bowman “1st”
RX_FIRST = _re(r"\b1st\b|\bfirst\b")

# Autos
RX_AUTO = _re(r"\bauto\b|\bautograph\b|\ba/u\b|\bon-card\b")

# Bowman-ish refractor family
RX_REFRACTOR = _re(r"\brefractor\b")
RX_SUPERFRACTOR = _re(r"\bsuper\s*fractor\b|\bsuperfractor\b|\b1\/1\b.*\bsuper\b|\bsuper\b.*\b1\/1\b")
RX_SHIMMER = _re(r"\bshimmer\b")
RX_SPECKLE = _re(r"\bspeckle\b")
RX_WAVE = _re(r"\bwave\b|\bray\s*wave\b|\braywave\b")
RX_MOJO = _re(r"\bmojo\b")
RX_LAVA = _re(r"\blava\b")

# Printing plate / 1/1
RX_PRINTING_PLATE = _re(r"\bprinting\s*plate\b|\bplate\b")

# Cmd+F: GH_ANCHOR_BOWMAN_COLORS_REMOVED_2A7D1C90
# Colors REMOVED entirely per requirements:
# remove atomic, aqua, black, blue, gold, green, orange, pink, purple, rainbow, red, silver, sapphire
# (No RX_COLOR, no WF_color, no CT_color, no color-derived logic anywhere.)
# ---------------------------------------------------------------

# Grading (optional bucket)
RX_GRADED = _re(r"\bpsa\b|\bbgs\b|\bsgc\b|\bcgc\b|\b10\b|\b9\.5\b|\bgem\s*mint\b")


# -----------------------------
# Serial / numbered detection
# -----------------------------
RX_SERIAL_FRACTION = _re(r"(?<!\d)(\d{1,4})\s*[\/／⁄]\s*(\d{1,4}(?:,\d{3})?)(?!\d)")
RX_SERIAL_BARE_DENOM = _re(r"(?<!\d)[\/／⁄]\s*(\d{1,4}(?:,\d{3})?)(?!\d)")
RX_SERIAL_OUTOF = _re(r"\bout\s*of\s*(\d{1,4}(?:,\d{3})?)\b|\boutof\s*(\d{1,4}(?:,\d{3})?)\b")
RX_SERIAL_N_OF_M = _re(r"\b(\d{1,4})\s*of\s*(\d{1,4})\b")


def extract_serial(title: str) -> Tuple[bool, Optional[int], Optional[int]]:
    """
    Returns: (is_numbered, serial_number, serial_out_of)
    """
    s = _clean(title)

    m = RX_SERIAL_FRACTION.search(s)
    if m:
        a = int(m.group(1).replace(",", ""))
        b = int(m.group(2).replace(",", ""))
        if 1 <= b <= 5000 and 0 <= a <= b:
            return True, a, b

    m = RX_SERIAL_BARE_DENOM.search(s)
    if m:
        b = int(m.group(1).replace(",", ""))
        if 1 <= b <= 5000:
            return True, None, b

    m = RX_SERIAL_N_OF_M.search(s)
    if m:
        a = int(m.group(1))
        b = int(m.group(2))
        if 1 <= b <= 5000 and 0 <= a <= b:
            return True, a, b

    m = RX_SERIAL_OUTOF.search(s)
    if m:
        denom = m.group(1) or m.group(2)
        if denom:
            b = int(denom.replace(",", ""))
            if 1 <= b <= 5000:
                return True, None, b

    return False, None, None


# -----------------------------
# CT_list builder (single label)
# -----------------------------
def _ct_list_label(wf: Dict[str, Any], serial_out_of: Optional[int]) -> str:
    """
    Deterministic single label for simulation grouping.
    IMPORTANT: must NOT contain commas.
    """
    # Selling formats take precedence (we want to exclude/bucket these)
    if wf.get("WF_lot"):
        return "lot"
    if wf.get("WF_pick") or wf.get("WF_set_builder"):
        return "pick_your_card"
    if wf.get("WF_complete_set"):
        return "complete_set"
    if wf.get("WF_presale"):
        return "presale"

    # 1/1 special
    if wf.get("WF_printing_plate"):
        return "printing_plate_1of1"
    if wf.get("WF_superfractor"):
        return "superfractor_1of1"

    # Base type
    stock = "chrome" if wf.get("WF_chrome") else ("paper" if wf.get("WF_paper") else "unknown_stock")
    first = "first" if wf.get("WF_first") else "not_first"
    auto = "auto" if wf.get("WF_auto") else "no_auto"

    # Parallel / finish family (priority order)
    if wf.get("WF_mojo"):
        par = "mojo"
    elif wf.get("WF_shimmer"):
        par = "shimmer"
    elif wf.get("WF_speckle"):
        par = "speckle"
    elif wf.get("WF_wave"):
        par = "wave"
    elif wf.get("WF_refractor"):
        par = "refractor"
    else:
        # Cmd+F: GH_ANCHOR_BOWMAN_NO_COLOR_PARALLEL_FALLBACK_6C2A1D12
        # Colors removed => no "{color}_parallel" output. If no refractor-family hit, call it base.
        par = "base"

    outof = f"outof_{int(serial_out_of)}" if serial_out_of else "unnumbered"
    return f"{stock}_{first}_{auto}_{par}_{outof}"


def classify_title(title: str) -> Dict[str, Any]:
    """
    Bowman classifier output modeled after your Topps classifier:
      - WF_* word flags
      - CT_* booleans
      - extracted: is_numbered, serial_number, serial_out_of
      - CT_list: single label string for simulation grouping (no commas)

    NOTE: Colors removed entirely (no WF_color / CT_color / RX_COLOR usage).
    """
    s = _clean(title)

    is_numbered, serial_number, serial_out_of = extract_serial(s)

    wf: Dict[str, Any] = {
        # selling formats
        "WF_complete_set": _has(RX_COMPLETE_SET, s),
        "WF_pick": _has(RX_PICK, s),
        "WF_lot": _has(RX_LOT, s),
        "WF_set_builder": _has(RX_SET_BUILDER, s),
        "WF_presale": _has(RX_PRESALE, s),

        # stock / core
        "WF_chrome": _has(RX_CHROME, s),
        "WF_paper": _has(RX_PAPER, s),
        "WF_first": _has(RX_FIRST, s),

        # auto
        "WF_auto": _has(RX_AUTO, s),

        # refractor families
        "WF_refractor": _has(RX_REFRACTOR, s),
        "WF_superfractor": _has(RX_SUPERFRACTOR, s),
        "WF_shimmer": _has(RX_SHIMMER, s),
        "WF_speckle": _has(RX_SPECKLE, s),
        "WF_wave": _has(RX_WAVE, s),
        "WF_mojo": _has(RX_MOJO, s),
        "WF_lava": _has(RX_LAVA, s),

        # 1/1 plates
        "WF_printing_plate": _has(RX_PRINTING_PLATE, s),

        # graded bucket
        "WF_graded": _has(RX_GRADED, s),
    }

    # CT booleans
    ct: Dict[str, Any] = {
        "CT_chrome": bool(wf["WF_chrome"]),
        "CT_paper": bool(wf["WF_paper"]),
        "CT_first": bool(wf["WF_first"]),
        "CT_auto": bool(wf["WF_auto"]),
        "CT_refractor": bool(wf["WF_refractor"]),
        "CT_superfractor_1of1": bool(wf["WF_superfractor"]) or (serial_out_of == 1 and _has(_re(r"\bsuper\b"), s)),
        "CT_printing_plate_1of1": bool(wf["WF_printing_plate"]) or (serial_out_of == 1 and _has(_re(r"\bplate\b"), s)),
        "CT_mojo": bool(wf["WF_mojo"]),
        "CT_shimmer": bool(wf["WF_shimmer"]),
        "CT_speckle": bool(wf["WF_speckle"]),
        "CT_wave": bool(wf["WF_wave"]),
        "CT_lot": bool(wf["WF_lot"]),
        "CT_pick_your_card": bool(wf["WF_pick"] or wf["WF_set_builder"]),
        "CT_complete_set": bool(wf["WF_complete_set"]),
        "CT_presale": bool(wf["WF_presale"]),
        "CT_graded": bool(wf["WF_graded"]),
    }

    out: Dict[str, Any] = {}
    out.update(wf)
    out.update(ct)
    out.update({
        "is_numbered": is_numbered,
        "serial_number": serial_number,
        "serial_out_of": serial_out_of,
    })

    out["CT_list"] = _ct_list_label(wf, serial_out_of)
    return out
