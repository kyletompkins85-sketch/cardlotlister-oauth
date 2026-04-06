# Cmd+F: GH_ANCHOR_BOWMAN_LISTING_CLASSIFIER_3F8A2C11
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


def _re(pat: str) -> re.Pattern:
    return re.compile(pat, re.IGNORECASE)

def _has(rx: re.Pattern, s: str) -> bool:
    return rx.search(s) is not None

def _clean(s: str) -> str:
    return (s or "").strip()


# Cmd+F: GH_ANCHOR_BOWMAN_PATTERNS_9C21A0B3

# Selling formats (incl. "Complete 200 Card … Chrome Set", "Complete Base Set BDC1-BDC200")
RX_COMPLETE_SET = _re(
    r"\bcomplete\s+set\b|\bset\s+complete\b|\bcomplete\b.*\bset\b"
)
RX_PICK         = _re(r"\b(pick\s*your|you\s*pick|pick\s*one|pick)\b|\b(choose\s*your|choose\s*one|choose)\b")
RX_LOT          = _re(r"\blot\b|\blots\b")
RX_SET_BUILDER  = _re(r"\bset\s*builder\b|\bcomplete\s+your\s+set\b")
RX_PRESALE      = _re(r"\bpre[\s-]?sale\b|\bpre[\s-]?order\b|\bpresale\b|\bpreorder\b")

# Stock
RX_CHROME = _re(r"\bchrome\b")
RX_PAPER  = _re(r"\bpaper\b|\bbase\b")

# “1st”
RX_FIRST = _re(r"\b1st\b|\bfirst\b")

# Autos (“Autographs” plural did not match \bautograph\b)
RX_AUTO = _re(r"\bauto\b|\bautographs?\b|\ba/u\b|\bon-card\b")

# Chrome Prospect Autographs (insert line + CPA sticker codes, e.g. CPA-EW)
RX_CPA_STICKER = _re(r"\bCPA-[A-Z]{2,}\b")
RX_CHROME_PROSPECT_AUTOGRAPHS = _re(
    r"\bchrome\s+prospect\s+autographs?\b"
    r"|\bchrome\s+prospect\s+auto\b"
    r"|\bprospect\s+autographs?\b"
)

# Refractor family
RX_REFRACTOR     = _re(r"\brefractor\b")
RX_SUPERFRACTOR  = _re(r"\bsuper\s*fractor\b|\bsuperfractor\b|\b1\/1\b.*\bsuper\b|\bsuper\b.*\b1\/1\b")
# X-Fractor is not plain chrome base (distinct from “refractor” word match)
# Listings say "X Refractor" (full word) or "X-Fractor"; old pattern only matched "X fractor".
RX_X_FRACTOR = _re(
    r"\bx[\s-]?(?:refractor|fractor)\b"
    r"|\bxfractor\b"
)
RX_SHIMMER       = _re(r"\bshimmer\b")
RX_SPECKLE       = _re(r"\bspeckle\b")
RX_WAVE          = _re(r"\bwave\b|\bray\s*wave\b|\braywave\b")
RX_MOJO          = _re(r"\bmojo\b")
RX_LAVA          = _re(r"\blava\b")
RX_SAPPHIRE      = _re(r"\bsapphire\b")
# Crystallized insert (checklist may spell “Crystalized”; listings often “Crystallized”)
RX_CRYSTALLIZED = _re(r"\bcrystallized\b|\bcrystalized\b")

# 1/1 plates
RX_PRINTING_PLATE = _re(r"\bprinting\s*plate\b|\bplate\b")

# Paper BD-* colored parallels (not plain stock; e.g. Base-Orange / Orange Border)
RX_ORANGE_BORDER = _re(
    r"\borange\s+border\b"
    r"|\borange\s+parallel\b"
    r"|\borange\s+wave\b"
    r"|\borange\s+foil\b"
    r"|\bbase\s*[-\s]?\s*orange\b"
    r"|\borange\s+paper\b"
)

# Chrome / BDC Sky Blue parallel (not standard BDC chrome base)
# Sellers also write "BLUE SKY" (word order reversed).
RX_SKY_BLUE = _re(r"\bsky\s+blue\b|\bblue\s+sky\b")

# Mini Diamond(s) parallel (not standard BDC chrome base)
RX_MINI_DIAMOND = _re(r"\bmini\s*[-\s]?\s*diamonds?\b")

# Aqua parallel (e.g. Aqua Geometric, Chrome Aqua — not standard BDC chrome base)
RX_AQUA = _re(
    r"\baqua\s+geometric\b"
    r"|\bchrome\s+aqua\b"
    r"|\baqua\b"
)

# Sparkle parallel (not standard BDC chrome base)
RX_SPARKLE = _re(r"\bsparkle\b")

# Blue Geometric parallel (not standard BDC chrome base)
RX_BLUE_GEOMETRIC = _re(r"\bblue\s+geometric\b")

# Snack Pack insert / parallel (not standard BDC chrome base).
# Sellers often list by line name only: Popcorn, Sunflower Seed, Bubble Gum — same product family as "Snack Pack".
RX_SNACK_PACK = _re(
    r"\bsnack\s*pack\b"
    r"|\bsnackpack\b"
    r"|\bpopcorn\b"
    r"|\bsunflower\s+seeds?\b"
    r"|\bbubble\s*gum\b"
    r"|\bbubblegum\b"
    r"|\bgum\s*ball\b"
    r"|\bgumball\b"
    r"|\bpeanuts?\b"
)

# Grading (slab / grading company / explicit “graded”; “ungraded” does not match \bgraded\b)
RX_GRADED = _re(r"\bpsa\b|\bbgs\b|\bsgc\b|\bcgc\b|\bgem\s*mint\b|\bgraded\b")

# Prized Prospects (Bowman insert)
# Matches:
#  - "Prized Prospects", "Prized Prospect"
#  - "#PP", "# PP"
#  - "PP-12", "PP12", "PP 12"
#  - "prized" (you explicitly asked for this)
RX_PRIZED_PROSPECT = _re(
    r"\bprized\s+prospects?\b"          # prized prospects / prized prospect
    r"|#\s*pp\b"                        # #PP / # PP
    r"|\bpp\s*[- ]?\s*\d{1,4}\b"        # PP-12 / PP 12 / PP12
    r"|\bprized\b"                      # prized (broad, per request)
)

# Axis insert (2025 Bowman Draft: A-1 … A-20; titles often say "Axis" and/or #A-12)
RX_AXIS = _re(
    r"\baxis\b"
    r"|#\s*A-\d{1,3}\b"
)

# Bowman Draft Night insert (#BDN-1 …) — distinct from paper BD-* base
# Sellers often say "Draft Day" for the same product line.
RX_DRAFT_NIGHT = _re(
    r"\bbowman\s+draft\s+nights?\b"
    r"|\bbowman[-\s]+draft[-\s]+night\b"
    r"|\bdraft\s+nights?\b"
    r"|\bdraft\s+day\b"
    r"|#\s*BDN-\d{1,3}\b"
    r"|\bBDN-\d{1,3}\b"
    r"|\bdraft\s+night\s+insert\b"
    r"|\bnight\s+insert\b"
    r"|\bchrome\s+draft\s+night\b"
    r"|\bdraftnight\b"
)

# Final Draft insert (#FD-1 …)
RX_FINAL_DRAFT = _re(
    r"\bfinal\s+draft\b"
    r"|#\s*FD-\d{1,3}\b"
    r"|\bFD-\d{1,3}\b"
)

# Bowman Draft Chrome prospect base (#BDC-1 …); not paper BD- base
RX_BDC = _re(
    r"#\s*BDC-\d{1,4}\b"
    r"|\bBDC-\d{1,4}\b"
    r"|\bBDC\d{1,4}\b"
)

# Bowman In Action insert (#BIA-1 …)
RX_BOWMAN_IN_ACTION = _re(
    r"\bbowman\s+in\s+action\b"
    r"|\bin\s+action\s+insert\b"
    r"|#\s*BIA-\d{1,3}\b"
    r"|\bBIA-\d{1,3}\b"
    r"|\bBIA\d{1,3}\b"
    r"|\bin\s+action\b"
)

# Image Variation (incl. Image Variation Auto / Autograph — not paper base)
RX_IMAGE_VARIATION = _re(
    r"\bimage\s+variations?\b"
    r"|\bimage\s+variation\s+autos?\b"
    r"|\bimage\s+variation\s+autographs?\b"
)

# College / team photo variation (SP) — not standard BDC chrome base
# Sellers often write the school only (e.g. "LSU") without "College Variation".
RX_COLLEGE_VARIATION = _re(
    r"\bcollege\s+variation\b"
    r"|\bvariation\s+sp\b"
    r"|\bcollege\s+sp\b"
    r"|\bLSU\b"
)

# Bowman Spotlight(s) insert (#BS-1 …)
RX_BOWMAN_SPOTLIGHT = _re(
    r"\bbowman\s+spotlights?\b"
    r"|\bchrome\s+spotlights?\b"
    r"|\bspotlights?\b"
    r"|#\s*BS-\d{1,3}\b"
    r"|\bBS-\d{1,3}\b"
)

# Etched in Glass variation / case hits (incl. informal “etch glass”; Stained Glass parallel in same family)
RX_ETCHED_IN_GLASS = _re(
    r"\betched\s+in\s+glass\b"
    r"|\betched\s+in\s+glass\s+variations?\b"
    r"|\bethced\s+in\s+glass\b"  # common eBay typo for “Etched”
    r"|\bethced\s+in\s+glass\s+variations?\b"
    r"|\betched\s+in\s+class\b"  # common eBay typo for “Glass”
    r"|\bethced\s+in\s+class\b"
    r"|\betch\s+glass\b"
    r"|\bstained\s+glass\b"
)


# -----------------------------
# Serial / numbered detection
# -----------------------------
RX_SERIAL_FRACTION = _re(r"(?<!\d)(\d{1,4})\s*[\/／⁄]\s*(\d{1,4}(?:,\d{3})?)(?!\d)")
RX_SERIAL_BARE_DENOM = _re(r"(?<!\d)[\/／⁄]\s*(\d{1,4}(?:,\d{3})?)(?!\d)")
RX_SERIAL_OUTOF = _re(r"\bout\s*of\s*(\d{1,4}(?:,\d{3})?)\b|\boutof\s*(\d{1,4}(?:,\d{3})?)\b")
RX_SERIAL_N_OF_M = _re(r"\b(\d{1,4})\s*of\s*(\d{1,4})\b")


def extract_serial(title: str) -> Tuple[bool, Optional[int], Optional[int]]:
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


def _ct_list_label(wf: Dict[str, Any], serial_out_of: Optional[int]) -> str:
    # Selling formats first
    if wf.get("WF_lot"):
        return "lot"
    if wf.get("WF_pick") or wf.get("WF_set_builder"):
        return "pick_your_card"
    if wf.get("WF_complete_set"):
        return "complete_set"
    if wf.get("WF_presale"):
        return "presale"

    if wf.get("WF_axis"):
        return "axis"

    if wf.get("WF_draft_night"):
        return "draft_night"

    if wf.get("WF_final_draft"):
        return "final_draft"

    if wf.get("WF_image_variation"):
        return "image_variation"

    if wf.get("WF_college_variation"):
        return "college_variation"

    if wf.get("WF_sky_blue"):
        return "sky_blue"

    if wf.get("WF_mini_diamond"):
        return "mini_diamond"

    if wf.get("WF_aqua"):
        return "aqua"

    if wf.get("WF_sparkle"):
        return "sparkle"

    if wf.get("WF_blue_geometric"):
        return "blue_geometric"

    if wf.get("WF_snack_pack"):
        return "snack_pack"

    if wf.get("WF_bowman_spotlight"):
        return "bowman_spotlight"

    if wf.get("WF_chrome_prospect_autographs"):
        return "chrome_prospect_autographs"

    if wf.get("WF_etched_in_glass"):
        return "etched_in_glass"

    # 1/1 special
    if wf.get("WF_printing_plate"):
        return "printing_plate_1of1"
    if wf.get("WF_superfractor"):
        return "superfractor_1of1"

    stock = "chrome" if wf.get("WF_chrome") else ("paper" if wf.get("WF_paper") else "unknown_stock")
    first = "first" if wf.get("WF_first") else "not_first"
    auto = "auto" if wf.get("WF_auto") else "no_auto"
    if wf.get("WF_prized_prospect"):
        return "prized_prospect"

    if wf.get("WF_bowman_in_action") and not (
        wf.get("WF_mojo")
        or wf.get("WF_shimmer")
        or wf.get("WF_speckle")
        or wf.get("WF_wave")
        or wf.get("WF_x_fractor")
        or wf.get("WF_refractor")
        or wf.get("WF_lava")
        or wf.get("WF_image_variation")
        or wf.get("WF_college_variation")
        or wf.get("WF_sky_blue")
        or wf.get("WF_mini_diamond")
        or wf.get("WF_aqua")
        or wf.get("WF_sparkle")
        or wf.get("WF_blue_geometric")
        or wf.get("WF_snack_pack")
        or wf.get("WF_bowman_spotlight")
        or wf.get("WF_chrome_prospect_autographs")
        or wf.get("WF_etched_in_glass")
        or wf.get("WF_sapphire")
        or wf.get("WF_crystallized")
        or wf.get("WF_final_draft")
    ):
        return "bowman_in_action"

    if wf.get("WF_bdc") and not (
        wf.get("WF_mojo")
        or wf.get("WF_shimmer")
        or wf.get("WF_speckle")
        or wf.get("WF_wave")
        or wf.get("WF_x_fractor")
        or wf.get("WF_refractor")
        or wf.get("WF_lava")
        or wf.get("WF_sapphire")
        or wf.get("WF_crystallized")
        or wf.get("WF_image_variation")
        or wf.get("WF_college_variation")
        or wf.get("WF_sky_blue")
        or wf.get("WF_mini_diamond")
        or wf.get("WF_aqua")
        or wf.get("WF_sparkle")
        or wf.get("WF_blue_geometric")
        or wf.get("WF_snack_pack")
        or wf.get("WF_bowman_spotlight")
        or wf.get("WF_chrome_prospect_autographs")
        or wf.get("WF_etched_in_glass")
        or wf.get("WF_final_draft")
    ):
        return "bdc"

    if wf.get("WF_mojo"):
        par = "mojo"
    elif wf.get("WF_shimmer"):
        par = "shimmer"
    elif wf.get("WF_speckle"):
        par = "speckle"
    elif wf.get("WF_wave"):
        par = "wave"
    elif wf.get("WF_sapphire"):
        par = "sapphire"
    elif wf.get("WF_crystallized"):
        par = "crystallized"
    elif wf.get("WF_x_fractor"):
        par = "x_fractor"
    elif wf.get("WF_refractor"):
        par = "refractor"
    else:
        par = "base"

    outof = f"outof_{int(serial_out_of)}" if serial_out_of else "unnumbered"
    return f"{stock}_{first}_{auto}_{par}_{outof}"


def classify_title(title: str) -> Dict[str, Any]:
    """
    NO COLORS. No CT_color_* keys. No WF_color. Nothing.
    """
    s = _clean(title)
    is_numbered, serial_number, serial_out_of = extract_serial(s)

    wf: Dict[str, Any] = {
        "WF_complete_set": _has(RX_COMPLETE_SET, s),
        "WF_pick": _has(RX_PICK, s),
        "WF_lot": _has(RX_LOT, s),
        "WF_set_builder": _has(RX_SET_BUILDER, s),
        "WF_presale": _has(RX_PRESALE, s),

        "WF_chrome": _has(RX_CHROME, s),
        "WF_paper": _has(RX_PAPER, s),
        "WF_first": _has(RX_FIRST, s),

        "WF_auto": _has(RX_AUTO, s),

        "WF_refractor": _has(RX_REFRACTOR, s),
        "WF_x_fractor": _has(RX_X_FRACTOR, s),
        "WF_superfractor": _has(RX_SUPERFRACTOR, s),
        "WF_shimmer": _has(RX_SHIMMER, s),
        "WF_speckle": _has(RX_SPECKLE, s),
        "WF_wave": _has(RX_WAVE, s),
        "WF_mojo": _has(RX_MOJO, s),
        "WF_lava": _has(RX_LAVA, s),
        "WF_sapphire": _has(RX_SAPPHIRE, s),
        "WF_crystallized": _has(RX_CRYSTALLIZED, s),
        "WF_prized_prospect": _has(RX_PRIZED_PROSPECT, s),
        "WF_axis": _has(RX_AXIS, s),
        "WF_draft_night": _has(RX_DRAFT_NIGHT, s),
        "WF_final_draft": _has(RX_FINAL_DRAFT, s),
        "WF_bdc": _has(RX_BDC, s),
        "WF_bowman_in_action": _has(RX_BOWMAN_IN_ACTION, s),
        "WF_image_variation": _has(RX_IMAGE_VARIATION, s),
        "WF_college_variation": _has(RX_COLLEGE_VARIATION, s),
        "WF_bowman_spotlight": _has(RX_BOWMAN_SPOTLIGHT, s),
        "WF_chrome_prospect_autographs": _has(RX_CHROME_PROSPECT_AUTOGRAPHS, s)
        or _has(RX_CPA_STICKER, s),
        "WF_etched_in_glass": _has(RX_ETCHED_IN_GLASS, s),

        "WF_printing_plate": _has(RX_PRINTING_PLATE, s),
        "WF_graded": _has(RX_GRADED, s),
        "WF_orange_border": _has(RX_ORANGE_BORDER, s),
        "WF_sky_blue": _has(RX_SKY_BLUE, s),
        "WF_mini_diamond": _has(RX_MINI_DIAMOND, s),
        "WF_aqua": _has(RX_AQUA, s),
        "WF_sparkle": _has(RX_SPARKLE, s),
        "WF_blue_geometric": _has(RX_BLUE_GEOMETRIC, s),
        "WF_snack_pack": _has(RX_SNACK_PACK, s),
    }

    ct: Dict[str, Any] = {
        "CT_chrome": bool(wf["WF_chrome"]),
        "CT_paper": bool(wf["WF_paper"]),
        "CT_first": bool(wf["WF_first"]),
        "CT_auto": bool(wf["WF_auto"]),
        "CT_refractor": bool(wf["WF_refractor"]),
        "CT_x_fractor": bool(wf["WF_x_fractor"]),
        "CT_superfractor_1of1": bool(wf["WF_superfractor"]) or (serial_out_of == 1 and _has(_re(r"\bsuper\b"), s)),
        "CT_printing_plate_1of1": bool(wf["WF_printing_plate"]) or (serial_out_of == 1 and _has(_re(r"\bplate\b"), s)),
        "CT_mojo": bool(wf["WF_mojo"]),
        "CT_shimmer": bool(wf["WF_shimmer"]),
        "CT_speckle": bool(wf["WF_speckle"]),
        "CT_wave": bool(wf["WF_wave"]),
        "CT_sapphire": bool(wf["WF_sapphire"]),
        "CT_crystallized": bool(wf["WF_crystallized"]),
        "CT_prized_prospect": bool(wf["WF_prized_prospect"]),
        "CT_axis": bool(wf["WF_axis"]),
        "CT_draft_night": bool(wf["WF_draft_night"]),
        "CT_final_draft": bool(wf["WF_final_draft"]),
        "CT_bdc": bool(wf["WF_bdc"]),
        "CT_bowman_in_action": bool(wf["WF_bowman_in_action"]),
        "CT_image_variation": bool(wf["WF_image_variation"]),
        "CT_college_variation": bool(wf["WF_college_variation"]),
        "CT_bowman_spotlight": bool(wf["WF_bowman_spotlight"]),
        "CT_chrome_prospect_autographs": bool(wf["WF_chrome_prospect_autographs"]),
        "CT_etched_in_glass": bool(wf["WF_etched_in_glass"]),
        "CT_lot": bool(wf["WF_lot"]),
        "CT_pick_your_card": bool(wf["WF_pick"] or wf["WF_set_builder"]),
        "CT_complete_set": bool(wf["WF_complete_set"]),
        "CT_presale": bool(wf["WF_presale"]),
        "CT_graded": bool(wf["WF_graded"]),
        "CT_paper_orange_border": bool(wf["WF_orange_border"]),
        "CT_sky_blue_parallel": bool(wf["WF_sky_blue"]),
        "CT_mini_diamond_parallel": bool(wf["WF_mini_diamond"]),
        "CT_aqua_parallel": bool(wf["WF_aqua"]),
        "CT_sparkle_parallel": bool(wf["WF_sparkle"]),
        "CT_blue_geometric_parallel": bool(wf["WF_blue_geometric"]),
        "CT_snack_pack": bool(wf["WF_snack_pack"]),
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
