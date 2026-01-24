#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_TOPPS_LISTING_CLASSIFIER_0C9F3A21
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
# Core patterns (edit as needed)
# -----------------------------

# Cmd+F: GH_ANCHOR_TOPPS_PATTERNS_7A1B2C3D

RX_ROOKIE = _re(r"\b(rookie\s*card|rookie|rc)\b")
RX_DEBUT  = _re(r"\bdebut\b")

# Important: check SSP before SP so SSP doesn't accidentally trigger SP via sloppy patterns
RX_SSP = _re(r"\bssp\b")
RX_SP  = _re(r"\bsp\b")

# Colors (you can add more later)
RX_COLOR = {
    "gold":   _re(r"\bgold\b"),
    "rainbow":_re(r"\brainbow\b"),
    "pink":   _re(r"\bpink\b"),
    "purple": _re(r"\bpurple\b"),
    "blue":   _re(r"\bblue\b"),
    "orange": _re(r"\borange\b"),
    "black":  _re(r"\bblack\b"),
    "green":  _re(r"\bgreen\b"),
    "silver": _re(r"\bsilver\b"),
    "red":    _re(r"\bred\b"),
}

# Finishes
RX_FINISH = {
    "foil":     _re(r"\bfoil\b"),
    "holo":     _re(r"\bholo\b"),
    "holofoil": _re(r"\bholo\s*foil\b|\bholofoil\b"),
}

# Variants
RX_HOLIDAY     = _re(r"\bholiday\b")
RX_SANDGLITTER = _re(r"\bsand\s*glitter\b|\bsandglitter\b")
RX_DIAMANTE    = _re(r"\bdiamante\b")
RX_XFRACTOR    = _re(r"\bx[\s-]?fractor\b")  # matches "X-Fractor", "X Fractor", "Xfractor"
RX_PARALLEL    = _re(r"\bparallel\b")
RX_GOLDEN_MIRROR = _re(r"\bgolden\s+mirror\b(?:\s+ssp)?(?:\s+image\s+variation)?")
RX_INDEPENDENCE_DAY = _re(r"\bindependence\s+day\b")
RX_CLEAR_VARIANT    = _re(r"\bclear\b")     # avoids "clearance" because of word boundary
RX_VINTAGE          = _re(r"\bvintage\b")
RX_PHOTO_VARIATION = _re(r"\bphoto\s*variation\b|\bimage\s*variation\b|\bvariation\s*photo\b|\btrue\s*photo\b")
RX_OWN_THE_NAME    = _re(r"\bown\s+the\s+name\b|\botn\b")
RX_FOIL_FRACTOR = _re(r"\bfoil\s*[-\s]?\s*fractor\b|\bfoilfractor\b")
RX_PRINTING_PLATE = _re(r"\bprinting\s*plate\b|\bplate\b")
RX_CANVAS_VARIANT = _re(r"(?:^|[^a-z])canv(?:a|i)s{1,2}(?:$|[^a-z])")
RX_FIRST_CARD = _re(r"\bfirst\s+card\b")
RX_PLATINUM   = _re(r"\bplatinum\b")
RX_WOOD = _re(r"\bwood\b|\bwood\s*grain\b|\bwoodgrain\b")
RX_CAMO = _re(r"\bcamo\b|\bcamouflage\b")
RX_ACETATE = _re(r"\bacetate\b")
RX_FLAGSHIP = _re(r"\bflagship\b")
RX_REAL_ONE = _re(r"\breal\s*one\b")
RX_PATCH = _re(r"\bpatch\b")
RX_AUTO = _re(r"\bauto\b|\bautograph\b|\ba/u\b")
RX_PATCH_AUTO = _re(
    r"\b("
    # explicit slash forms first (your failing case)
    r"auto\s*[\/\\]\s*patch|"
    r"patch\s*[\/\\]\s*auto|"

    # common word forms
    r"patch\s*(?:&|\+|and)?\s*auto(?:graph)?|"
    r"auto(?:graph)?\s*(?:&|\+|and)?\s*patch|"
    r"patch\s*(?:&|\+|and)?\s*autograph|"
    r"autograph\s*(?:&|\+|and)?\s*patch"
    r")\b"
)
RX_SKETCH = _re(r"\bsketch\b")
RX_SHAPED_SKETCH = _re(r"\bshaped\s+sketch\b")
RX_1990 = _re(r"\b1990\b|\b1990s\b")


# Cmd+F: GH_ANCHOR_RX_HOLIDAY_VARIANTS_71C2A9D0
RX_HOLIDAY_WORD = _re(r"\bholiday\b")
RX_HOLIDAY_JACKOLANTERN = _re(r"\bjack(?:\s*[-']?\s*o\s*[-']?\s*)?lantern\b|\bjackolantern\b")
RX_HOLIDAY_JACKOLANTERN_LANTERN = _re(r"\blantern\b")
RX_HOLIDAY_GHOST = _re(r"\bghost\b")
RX_HOLIDAY_MUMMY = _re(r"\bmummy\b")
# black cat / blackcat
RX_HOLIDAY_BLACK_CAT = _re(r"\bblack\s*cat\b|\bblackcat\b")
RX_HOLIDAY_WITCH_HAT = _re(
    r"\b(?:witch|wich)(?:'s|es)?\s*hats?\b|\b(?:witch|wich)hat\b"
)
RX_HOLIDAY_BATS = _re(r"\bbats?\b")  # matches bat OR bats

# Formats / selling style
RX_COMPLETE_SET = _re(r"\bcomplete\s+set\b|\bset\s+complete\b")
RX_SINGLES      = _re(r"\bsingle\b|\bsingles\b")
RX_PICK         = _re(r"\b(pick\s*your|you\s*pick|pick\s*one|pick)\b|\b(choose\s*your|choose\s*one|choose)\b")
RX_LOTS         = _re(r"\blot\b|\blots\b|\blotting\b")  # "lotting" is rare; adjust/remove if noisy
RX_PRESALE      = _re(r"\bpre[\s-]?sale\b|\bpre[\s-]?sell\b|\bpre[\s-]?order\b|\bpresale\b|\bpreorder\b")
# Cmd+F: GH_ANCHOR_RX_PICK_YOUR_CARD_6C1A9D20
RX_PICK_YOUR_CARD = _re(
    r"\b("
    # pick/choose language
    r"pick\s*your\s*(card|base|cards|base\s*card)|"
    r"pick\s*(a|any)\s*(card|base|cards)|"
    r"pick\s*from\s*list|pick\s*from\s*the\s*list|"
    r"choose\s*(your|any|a)\s*(card|base|cards)|"
    r"you\s*pick|u\s*pick|"

    # list/builder language
    r"set\s*builder|set\s*[-\s]?builder|"
    r"complete\s*your\s*set|complete\s*the\s*set|"

    # explicit list callouts
    r"pick\s*from\s*(my\s*)?list|"
    r"from\s*list\b|"

    # range + "buy any N cards" style (your example)
    r"cards?\s*\d{1,4}\s*[-–]\s*\d{1,4}|"
    r"buy\s*\"?any\"?\s*\d{1,3}\s*cards?"
    r")\b"
)


# ============================================================
# Pick-Your-Card extra rules (append-only)
# Add ONE new RX per example at the bottom of this list.
# IMPORTANT: every line MUST end with a comma.
# ============================================================
# Cmd+F: GH_ANCHOR_PICK_YOUR_CARD_EXTRA_RULES_9A2C1D80
RX_PICK_YOUR_CARD_EXTRA = [
    #overfit
    _re(r"\bbase\b.*#?\s*us\d+\s*[-–]\s*us\d+"),          # BASE #US1-US350 style
    _re(r"\binserts?\s+and\s+parallels?\b"),              # INSERTS AND PARALLELS
    _re(r"\bsingles\b"),                                  # SINGLES
    _re(r"\bpick\s+your\s+rainbow\s+foil\b"),             # Pick Your Rainbow Foil
    _re(r"\bpick\s+list\b|\bpick\s+from\s+list\b"),       # Pick List / Pick From List
    _re(r"\byou\s+choose\b"),                             # You Choose
    _re(r"\b\d{1,3}\s*card\s+minimum\b"),                 # 4 CARD MINIMUM
    _re(r"\bparallels?\s*&\s*inserts?\b"),                # Parallels & Inserts
    _re(r"\bbase\b.*#?\s*us\d+\s*[-–]\s*us\b"),           # BASE #US1-US (truncated/short form)
    _re(r"\bpick\s+your\s+player\b"),
    _re(r"\bpick\s*-\s*a\s*-\s*card\b|\bpick\s*a\s*card\b"),
    _re(r"\bcomplete\s+base\s+set\b|\bstars\s+of\s+mlb\s+set\b"),
    _re(r"\bcomplete\s+set\b.*#?\s*us\d+\s*[-–]\s*us\d+"),
]



# Card number extraction
RX_US_CARDNUM_1 = _re(r"\bUS\s*[-#]?\s*(\d{1,4})\b")   # "US175", "US 175", "US-175", "US#175"
RX_US_CARDNUM_2 = _re(r"\b(US\d{1,4})\b")              # "US175"

# Serial / numbered detection
RX_SERIAL_FRACTION = _re(r"(?<!\d)(\d{1,4})\s*/\s*(\d{1,4})(?!\d)")
RX_SERIAL_BARE_DENOM = _re(r"(?<!\d)/\s*(\d{1,4})(?!\d)")  # matches "/250" (no numerator)
RX_SERIAL_OUTOF = _re(r"\bout\s*of\s*(\d{1,4})\b|\boutof\s*(\d{1,4})\b")
RX_OUTOF_1    = _re(r"(?:^|[^\d])(?:\d{1,4}\s*[\/／⁄]\s*1|[\/／⁄]\s*1)(?:$|[^\d])|\bout\s*of\s*1\b")
RX_OUTOF_5    = _re(r"(?:^|[^\d])(?:\d{1,4}\s*[\/／⁄]\s*5|[\/／⁄]\s*5)(?:$|[^\d])|\bout\s*of\s*5\b")
RX_OUTOF_10   = _re(r"(?:^|[^\d])(?:\d{1,4}\s*[\/／⁄]\s*10|[\/／⁄]\s*10)(?:$|[^\d])|\bout\s*of\s*10\b")
RX_OUTOF_25   = _re(r"(?:^|[^\d])(?:\d{1,4}\s*[\/／⁄]\s*25|[\/／⁄]\s*25)(?:$|[^\d])|\bout\s*of\s*25\b")
RX_OUTOF_50 = _re(r"\b\d{1,4}\s*[\/／⁄]\s*50\b|(?<!\d)[\/／⁄]\s*50\b|\bout\s*of\s*50\b")
RX_OUTOF_76 = _re(r"(?:^|[^\d])(?:\d{1,4}\s*[\/／⁄]\s*76|[\/／⁄]\s*76)(?:$|[^\d])|\bout\s*of\s*76\b")
RX_OUTOF_99   = _re(r"(?:^|[^\d])(?:\d{1,4}\s*[\/／⁄]\s*99|[\/／⁄]\s*99)(?:$|[^\d])|\bout\s*of\s*99\b")
RX_OUTOF_150  = _re(r"(?:^|[^\d])(?:\d{1,4}\s*[\/／⁄]\s*150|[\/／⁄]\s*150)(?:$|[^\d])|\bout\s*of\s*150\b")
RX_OUTOF_250 = _re(r"(?<!\d)/\s*250\b|\bout\s*of\s*250\b")
RX_OUTOF_2025 = _re(r"(?:^|[^\d])(?:\d{1,4}\s*[\/／⁄]\s*2025|[\/／⁄]\s*2025)(?:$|[^\d])|\bout\s*of\s*2025\b")
RX_SERIAL_N_OF_M = _re(r"\b(\d{1,4})\s*of\s*(\d{1,4})\b")



def extract_card_number(title: str) -> Optional[str]:
    """
    Returns something like 'US175' or None.
    Priority: US### patterns only (per your request).
    """
    s = _clean(title)
    m = RX_US_CARDNUM_1.search(s)
    if m:
        return f"US{m.group(1)}"
    m = RX_US_CARDNUM_2.search(s)
    if m:
        return m.group(1).upper()
    return None


def extract_serial(title: str) -> Tuple[bool, Optional[int], Optional[int]]:
    """
    Returns: (is_numbered, serial_number, serial_out_of)

    Examples:
      "12/99" -> (True, 12, 99)
      "out of 50" -> (True, None, 50)
      no serial -> (False, None, None)
    """
    s = _clean(title)

    # Prefer fraction form: 12/99
    m = RX_SERIAL_FRACTION.search(s)
    if m:
        a = int(m.group(1))
        b = int(m.group(2))
        # Heuristics to avoid grabbing years like 2025/2026 (rare but possible)
        # and avoid absurd denominators.
        if 1 <= b <= 5000 and 0 <= a <= b:
            return True, a, b

    # Bare denom form: "/250"
    m = RX_SERIAL_BARE_DENOM.search(s)
    if m:
        b = int(m.group(1))
        if 1 <= b <= 5000:
            return True, None, b

    # "1 of 1" form: 1 of 1, 12 of 50, etc.
    m = RX_SERIAL_N_OF_M.search(s)
    if m:
        a = int(m.group(1))
        b = int(m.group(2))
        if 1 <= b <= 5000 and 0 <= a <= b:
            return True, a, b

    # Fallback: "out of 99"
    m = RX_SERIAL_OUTOF.search(s)
    if m:
        denom = m.group(1) or m.group(2)
        if denom:
            b = int(denom)
            if 1 <= b <= 5000:
                return True, None, b

    return False, None, None


def classify_title(title: str) -> Dict[str, Any]:
    """
    Main entrypoint.
    Output order is: WF_* (word flags), CT_* (card types), then extraction fields.
    """
    s = _clean(title)

    is_numbered, serial_number, serial_out_of = extract_serial(s)
    card_number = extract_card_number(s)

    # ============================================================
    # WORD FLAGS (WF_*) — presence / keyword detection only
    # ============================================================
    # Cmd+F: GH_ANCHOR_WORD_FLAGS_SECTION_1A2B3C4D
    wf: Dict[str, Any] = {
        # rookie / debut
        "WF_rookie": _has(RX_ROOKIE, s),
        "WF_debut": _has(RX_DEBUT, s),

        # SP / SSP (separate)
        "WF_ssp": _has(RX_SSP, s),
        "WF_sp": (not _has(RX_SSP, s)) and _has(RX_SP, s),  # suppress SP if SSP present

        # variants / terms
        "WF_parallel": _has(RX_PARALLEL, s),
        "WF_sandglitter": _has(RX_SANDGLITTER, s),
        "WF_diamante": _has(RX_DIAMANTE, s),
        "WF_x_fractor": _has(RX_XFRACTOR, s),
        "WF_golden_mirror": _has(RX_GOLDEN_MIRROR, s),
        "WF_independence_day": _has(RX_INDEPENDENCE_DAY, s),
        "WF_clear": _has(RX_CLEAR_VARIANT, s),
        "WF_vintage": _has(RX_VINTAGE, s),
        "WF_photo_variation": _has(RX_PHOTO_VARIATION, s),
        "WF_own_the_name": _has(RX_OWN_THE_NAME, s),
        "WF_foil_fractor": _has(RX_FOIL_FRACTOR, s),
        "WF_printing_plate": _has(RX_PRINTING_PLATE, s),
        "WF_canvas": _has(RX_CANVAS_VARIANT, s),
        "WF_first_card": _has(RX_FIRST_CARD, s),
        "WF_platinum": _has(RX_PLATINUM, s),
        "WF_wood": _has(RX_WOOD, s),
        "WF_camo": _has(RX_CAMO, s),
        "WF_acetate": _has(RX_ACETATE, s),
        "WF_flagship": _has(RX_FLAGSHIP, s),
        "WF_real_one": _has(RX_REAL_ONE, s),
        "WF_patch": _has(RX_PATCH, s),
        "WF_auto": _has(RX_AUTO, s),
        "WF_patch_auto": _has(RX_PATCH_AUTO, s),
        "WF_sketch": _has(RX_SKETCH, s),
        "WF_shaped_sketch": _has(RX_SHAPED_SKETCH, s),
        "WF_1990": _has(RX_1990, s),

        # Holiday family (word flags)
        "WF_holiday": _has(RX_HOLIDAY_WORD, s),
        "WF_holiday_jackolantern": (_has(RX_HOLIDAY_JACKOLANTERN, s) or _has(RX_HOLIDAY_JACKOLANTERN_LANTERN, s)),
        "WF_holiday_ghost": _has(RX_HOLIDAY_GHOST, s),
        "WF_holiday_mummy": _has(RX_HOLIDAY_MUMMY, s),
        "WF_holiday_black_cat": _has(RX_HOLIDAY_BLACK_CAT, s),
        "WF_holiday_witch_hat": _has(RX_HOLIDAY_WITCH_HAT, s),
        "WF_holiday_bats": _has(RX_HOLIDAY_BATS, s),


        # formats / selling style
        "WF_complete_set": _has(RX_COMPLETE_SET, s),
        "WF_singles": _has(RX_SINGLES, s),
        "WF_pick": _has(RX_PICK, s),
        "WF_lot": _has(RX_LOTS, s),
        "WF_presale": _has(RX_PRESALE, s),
        # Cmd+F: GH_ANCHOR_WF_PICK_YOUR_CARD_WITH_EXTRAS_3F7A1C20
        "WF_pick_your_card": (
            _has(RX_PICK_YOUR_CARD, s)
            or any(_has(rx, s) for rx in RX_PICK_YOUR_CARD_EXTRA)
        ),

        # Cmd+F: GH_ANCHOR_WF_OUTOF_250_FROM_SERIAL_2D7A1C90
        "WF_outof_1": (serial_out_of == 1) or _has(RX_OUTOF_1, s),
        "WF_outof_5": (serial_out_of == 5) or _has(RX_OUTOF_5, s),
        "WF_outof_10": (serial_out_of == 10) or _has(RX_OUTOF_10, s),
        "WF_outof_25": (serial_out_of == 25) or _has(RX_OUTOF_25, s),
        "WF_outof_50": (serial_out_of == 50) or _has(RX_OUTOF_50, s),
        "WF_outof_76": (serial_out_of == 76) or _has(RX_OUTOF_76, s),
        "WF_outof_99": (serial_out_of == 99) or _has(RX_OUTOF_99, s),
        "WF_outof_150": (serial_out_of == 150) or _has(RX_OUTOF_150, s),
        "WF_outof_250": (serial_out_of == 250) or _has(RX_OUTOF_250, s),
        "WF_outof_2025": (serial_out_of == 2025) or _has(RX_OUTOF_2025, s),
    }

    # Colors as WF_color_<name>
    for color, rx in RX_COLOR.items():
        wf[f"WF_color_{color}"] = _has(rx, s)

    # Finishes as WF_finish_<name>
    for fin, rx in RX_FINISH.items():
        wf[f"WF_finish_{fin}"] = _has(rx, s)

    # ============================================================
    # CARD TYPE (CT_*) — higher-level classifications
    # ============================================================
    # Cmd+F: GH_ANCHOR_CARD_TYPE_SECTION_5E6F7A8B
    ct: Dict[str, Any] = {
        # Only requested card type variable:
        # Directly driven by word flag WF_diamante
        "CT_diamante": bool(wf.get("WF_diamante", False)),
        "CT_x_fractor": bool(wf.get("WF_x_fractor", False)),
        "CT_pick_your_card": bool(wf.get("WF_pick_your_card", False)),
        "CT_purple_rainbow": bool(
            wf.get("WF_color_purple", False) and
            (wf.get("WF_color_rainbow", False) or wf.get("WF_outof_250", False))
        ),
        "CT_blue_rainbow": bool(
            wf.get("WF_color_blue", False) and
            (wf.get("WF_color_rainbow", False) or wf.get("WF_outof_150", False))
        ),
        "CT_green_foil": bool(
            wf.get("WF_color_green", False) and
            (wf.get("WF_color_rainbow", False) or wf.get("WF_outof_99", False))
        ),
        "CT_foil_fractor_1of1": bool(wf.get("WF_foil_fractor", False) and wf.get("WF_outof_1", False)),
        "CT_first_card_1of1": bool(wf.get("WF_first_card", False) and wf.get("WF_outof_1", False)),
        "CT_platinum_1of1": bool(wf.get("WF_platinum", False) and wf.get("WF_outof_1", False)),
        "CT_red_5": bool(wf.get("WF_color_red", False) and wf.get("WF_outof_5", False)),
        "CT_gold_2025": bool(wf.get("WF_color_gold", False) and wf.get("WF_outof_2025", False)), 
        "CT_gold_50": bool(wf.get("WF_color_gold", False) and wf.get("WF_outof_50", False)),
        "CT_black_10": bool(wf.get("WF_color_black", False) and wf.get("WF_outof_10", False)),
        "CT_clear_10": bool(wf.get("WF_clear", False) and wf.get("WF_outof_10", False)),
        "CT_orange_25": bool(wf.get("WF_color_orange", False) and wf.get("WF_outof_25", False)),
        "CT_independence_day_76": bool(
            wf.get("WF_outof_76", False) or wf.get("WF_independence_day", False)
        ),
        "CT_vintage_99": bool(wf.get("WF_vintage", False) and wf.get("WF_outof_99", False)),
        "CT_printing_plate_1of1": bool(wf.get("WF_printing_plate", False) and wf.get("WF_outof_1", False)),
        "CT_canvas_50": bool(wf.get("WF_canvas", False) and wf.get("WF_outof_50", False)),
        "CT_wood_25": bool(wf.get("WF_wood", False) and wf.get("WF_outof_25", False)),
        "CT_holiday_witch_hat_5": bool(wf.get("WF_holiday_witch_hat", False) and wf.get("WF_outof_5", False)),
        "CT_camo_25": bool(wf.get("WF_camo", False) and wf.get("WF_outof_25", False)),
        "CT_holiday_mummy_50": bool(wf.get("WF_holiday_mummy", False) and wf.get("WF_outof_50", False)),
        "CT_acetate_10": bool(wf.get("WF_acetate", False) and wf.get("WF_outof_10", False)),
        
        "CT_sandglitter": bool(wf.get("WF_sandglitter", False)),
        "CT_golden_mirror": bool(wf.get("WF_golden_mirror", False)),
        "CT_photo_variation": bool(wf.get("WF_photo_variation", False)),
        "CT_own_the_name": bool(wf.get("WF_own_the_name", False)),
        "CT_ssp": bool(wf.get("WF_ssp", False)),
        "CT_flagship_real_one": bool(wf.get("WF_real_one", False)),
        "CT_flagship_patch_auto": bool(
            (
                (wf.get("WF_flagship", False) and not wf.get("WF_real_one", False))  # what you used to call "base"
                or wf.get("WF_patch_auto", False)  # patch auto even if it doesn't say flagship
            )
            and not wf.get("WF_real_one", False)
        ),
        "CT_shaped_sketch": bool(wf.get("WF_shaped_sketch", False)),
        "CT_sketch": bool(wf.get("WF_sketch", False) and not wf.get("WF_shaped_sketch", False)),
        "CT_1990": bool(wf.get("WF_1990", False)),
        
        # Holiday card types (mutually exclusive by construction)
        "CT_holiday_jackolantern": bool(wf.get("WF_holiday_jackolantern", False)),
        "CT_holiday_ghost": bool(wf.get("WF_holiday", False) and wf.get("WF_holiday_ghost", False)),
        "CT_holiday_mummy": bool(wf.get("WF_holiday", False) and wf.get("WF_holiday_mummy", False)),
        "CT_holiday_black_cat": bool(wf.get("WF_holiday", False) and wf.get("WF_holiday_black_cat", False)),
        "CT_holiday_witch_hat": bool(wf.get("WF_holiday", False) and wf.get("WF_holiday_witch_hat", False)),
        "CT_holiday_bats": bool(
            # Way 1: explicitly holiday + bats
            (wf.get("WF_holiday", False) and wf.get("WF_holiday_bats", False))
            # Way 2: bats + 1/1 (even if "holiday" isn't present)
            or (wf.get("WF_holiday_bats", False) and wf.get("WF_outof_1", False))
        ),
        "CT_holiday_base": bool(
            wf.get("WF_holiday", False)
            and not wf.get("WF_holiday_jackolantern", False)
            and not wf.get("WF_holiday_ghost", False)
            and not wf.get("WF_holiday_mummy", False)
            and not wf.get("WF_holiday_black_cat", False)
            and not wf.get("WF_holiday_witch_hat", False)
            and not wf.get("WF_holiday_bats", False)
        ),
        "CT_lot": bool(wf.get("WF_lot", False)),
    }

    # Non-word extraction fields (kept from previous requirements)
    extracted: Dict[str, Any] = {
        "card_number": card_number,
        "is_numbered": is_numbered,
        "serial_number": serial_number,
        "serial_out_of": serial_out_of,
    }

    # Final output: word flags first, then card type, then extracted fields
    out: Dict[str, Any] = {}
    out.update(wf)
    out.update(ct)
    out.update(extracted)
    return out



# Cmd+F: GH_ANCHOR_TOPPS_LISTING_CLASSIFIER_DEMO_5F1A3B8D
if __name__ == "__main__":
    # quick local sanity check if you ever run it
    tests = [
        "2025 Topps Update US175 RC Rainbow Foil 12/99",
        "2025 Topps Update Complete Set Factory Sealed",
        "2025 Topps Update Holiday Sand Glitter SSP US350",
        "2025 Topps Update You Pick Singles Blue Parallel out of 50",
        "2025 Topps Update Diamante Gold SP #US1",
        "2025 Topps Update Presale Rookie Debut Holofoil /25",
    ]
    for t in tests:
        print(t)
        print(classify_title(t))
        print("-" * 60)
