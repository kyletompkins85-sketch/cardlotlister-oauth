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
# Cmd+F: GH_ANCHOR_RX_XFRACTOR_2F7A1C90
RX_XFRACTOR    = _re(r"\bx[\s-]?fractor\b")  # matches "X-Fractor", "X Fractor", "Xfractor"
RX_PARALLEL    = _re(r"\bparallel\b")

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



# Card number extraction
RX_US_CARDNUM_1 = _re(r"\bUS\s*[-#]?\s*(\d{1,4})\b")   # "US175", "US 175", "US-175", "US#175"
RX_US_CARDNUM_2 = _re(r"\b(US\d{1,4})\b")              # "US175"

# Serial / numbered detection
#  - captures "12/99", "12 / 99", "#12/99", "No. 12/99"
RX_SERIAL_FRACTION = _re(r"(?<!\d)(\d{1,4})\s*/\s*(\d{1,4})(?!\d)")
# Cmd+F: GH_ANCHOR_RX_SERIAL_BARE_DENOM_1C7A2D90
RX_SERIAL_BARE_DENOM = _re(r"(?<!\d)/\s*(\d{1,4})(?!\d)")  # matches "/250" (no numerator)
#  - captures "out of 99", "outof 99"
RX_SERIAL_OUTOF = _re(r"\bout\s*of\s*(\d{1,4})\b|\boutof\s*(\d{1,4})\b")
# Cmd+F: GH_ANCHOR_RX_OUTOF_250_8B1C2D3E
RX_OUTOF_250 = _re(r"(?<!\d)/\s*250\b|\bout\s*of\s*250\b")


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
        "WF_holiday": _has(RX_HOLIDAY, s),
        "WF_sandglitter": _has(RX_SANDGLITTER, s),
        "WF_diamante": _has(RX_DIAMANTE, s),
        "WF_x_fractor": _has(RX_XFRACTOR, s),

        # formats / selling style
        "WF_complete_set": _has(RX_COMPLETE_SET, s),
        "WF_singles": _has(RX_SINGLES, s),
        "WF_pick": _has(RX_PICK, s),
        "WF_lot": _has(RX_LOTS, s),
        "WF_presale": _has(RX_PRESALE, s),
        "WF_pick_your_card": _has(RX_PICK_YOUR_CARD, s),
        # Cmd+F: GH_ANCHOR_WF_OUTOF_250_FROM_SERIAL_2D7A1C90
        "WF_outof_150": (serial_out_of == 150),
        "WF_outof_250": (serial_out_of == 250),   
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
