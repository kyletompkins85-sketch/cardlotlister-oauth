"""
Structured card taxonomy: product group, color, finish, auto → composite card_type string.

The word **Refractor** appears only in **Chrome · Refractor** (plain silver parallel vs
chrome base). Elsewhere—insert lines, Axis, CPA, colors—do not use *Refractor*; colored parallels
are implied refractors, and Axis uses **Parallel** for the non-base silver parallel.

Stock (Chrome vs Paper) is omitted for named insert lines (Axis, Draft Night, In Action,
Chrome Prospect Autographs / CPA (same **Chrome** family as chrome parallels),
Prized Prospects, etc.) — they are chrome products by definition. Stock remains in pilot flags
for base/chrome-base rows handled outside this composite (BDC · Base, Base-Paper).

Group priority is loaded from cardmatch/product_groups.json (kept in sync with product_groups.yaml).

Insert-line product groups (Draft Night, In Action, etc.) use ``insert_line_parallel_taxonomy.json``
to opt into the same Bowman hobby color + print-run ladder as BDC (collapse + color serial), not only
a generic `` /N`` suffix on the last segment.

Colored chrome parallels: Wave / Lava / Shimmer / Sapphire / … stack on the same Bowman print run;
those collapse to one label per color (**Green /99**, **Gold /50**, **Blue /150**, …) via
`_collapse_bdc_colored_parallel_parts`. Aqua wave/lava stacks still use `_collapse_bdc_aqua_parallel_parts`
first (same **Aqua /125** family). Listing-count CSVs omit lot/pick/graded/complete-set — see
`cardmatch.card_type.LISTING_COUNT_EXCLUDED_CARD_TYPES`.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cardmatch.bowman_z10 import classify_bowman_title
from cardmatch.normalize import normalize_title

_PACKAGE_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=200000)
def flags_for_title(title: str) -> Dict[str, Any]:
    """Classifier output for a listing title (memoized)."""
    return classify_bowman_title(normalize_title(title))


def _load_group_priority() -> List[Tuple[str, str, str]]:
    """[(slug, display_name, wf_key), ...] in priority order."""
    path = _PACKAGE_DIR / "product_groups.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: List[Tuple[str, str, str]] = []
    for g in raw.get("groups", []):
        slug = str(g.get("slug", "")).strip()
        disp = str(g.get("display_name", "")).strip()
        wf = str(g.get("wf", "")).strip()
        if slug and disp and wf:
            out.append((slug, disp, wf))
    return out


_GROUP_PRIORITY: List[Tuple[str, str, str]] = _load_group_priority()

# Canonical first segment for Bowman Draft chrome stock (BDC # parallels, base, CPA). Legacy CSVs may
# still say **BDC Chrome Prospect**; :func:`finalize_bdc_composite_string` normalizes that to **Chrome**.
BDC_PRIMARY_FAMILY = "Chrome"
_LEGACY_BDC_PRIMARY_PREFIX = "BDC Chrome Prospect"


@lru_cache(maxsize=1)
def _insert_line_parallel_taxonomy_slugs() -> frozenset[str]:
    """Slugs that use BDC-style ladder finalize for product-group composites (see insert_line_parallel_taxonomy.json)."""
    path = _PACKAGE_DIR / "insert_line_parallel_taxonomy.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    slugs = raw.get("slugs", {})
    return frozenset(str(k).strip() for k in slugs if str(k).strip())


# Standard Bowman Chrome prospect colored refractor print runs (hobby ladder). Single source for
# collapse (`finalize`) and denominator-only inference (e.g. "1/5" → Red, "/99" → Green).
_BDC_COLOR_SERIAL: Dict[str, str] = {
    "Purple": "/250",
    "Green": "/99",
    "Yellow": "/75",
    "Black": "/73",
    "Red": "/5",
    "Gold": "/50",
    "Orange": "/25",
    "Blue": "/150",
    "Aqua": "/125",
    "Sky Blue": "/499",
}

# Extra finish words that sit on the same color serial (do not become separate card_type dimensions).
_BDC_MERGE_FINISHES = frozenset(
    {"Wave", "Lava", "Shimmer", "Sapphire", "Speckle", "Sparkle"}
)


def _inverse_bdc_serial_ladder() -> Dict[int, str]:
    """Map print-run denominator → color name (inverse of `_BDC_COLOR_SERIAL`)."""
    out: Dict[int, str] = {}
    for color, denom_s in _BDC_COLOR_SERIAL.items():
        m = re.match(r"\/(\d+)", denom_s)
        if m:
            out[int(m.group(1))] = color
    return out


# Shared: CPA/college autos, BDC parallel titles with only "1/5" or "/150" (no color word).
_SERIAL_DENOM_TO_BDC_COLOR: Dict[int, str] = _inverse_bdc_serial_ladder()
# Steel Metal /100 is not in the colored collapse ladder but appears as a bare /100 in titles.
_SERIAL_DENOM_TO_BDC_COLOR[100] = "Steel Metal"
# Fuchsia Reptilian parallel is /199 only (not in the standard hobby color ladder dict).
_SERIAL_DENOM_TO_BDC_COLOR[199] = "Fuchsia Reptilian"
# Logo / Logofractor parallel (Bowman "Logo Refractor" /35 — not the standard color ladder).
_SERIAL_DENOM_TO_BDC_COLOR[35] = "Logo Refractor"
_SERIAL_OUT_TO_COLOR = _SERIAL_DENOM_TO_BDC_COLOR


def bdc_serial_denominator_color_map() -> Dict[int, str]:
    """
    Bowman Chrome BDC standard print runs: denominator (e.g. 5, 99, 150) → color name.
    Same ladder as `_BDC_COLOR_SERIAL` plus 100 → Steel Metal. Used for titles with 1/5, /99, etc.
    """
    return dict(_SERIAL_DENOM_TO_BDC_COLOR)


def _bdc_parallel_detail_from_serial_denominator(so: int) -> Optional[str]:
    """Map print-run denominator to BDC parallel slice label (includes Steel Metal /100)."""
    c = _SERIAL_DENOM_TO_BDC_COLOR.get(so)
    if not c:
        return None
    if c == "Steel Metal":
        return "Steel Metal /100"
    if c == "Fuchsia Reptilian":
        return "Fuchsia Reptilian /199"
    if c == "Logo Refractor":
        return "Logo Refractor /35"
    return c

# Product lines that share BDC-style color + serial normalization (finalize/collapse).
_BDC_FAMILY_PREFIXES: Tuple[str, ...] = (BDC_PRIMARY_FAMILY, "Chrome Prospect College Variations")

# Axis color words (same intent as card_type._axis).
_RE_AXIS_GREEN = re.compile(r"\bgreen\b", re.I)
_RE_AXIS_GOLD = re.compile(r"\bgold\b", re.I)
_RE_AXIS_ORANGE = re.compile(r"\borange\b", re.I)
_RE_AXIS_BLACK = re.compile(r"\bblack\b", re.I)
_RE_AXIS_RED = re.compile(r"\bred\b", re.I)

_RE_BLUE_REFRACTOR_PHRASE = re.compile(r"\bblue\s+refractor\b", re.I)
_RE_BLUE_MOJO_REFRACTOR = re.compile(r"\bblue\s+mojo\s+refractor\b", re.I)
_RE_AQUA_WAVE_REFRACTOR = re.compile(r"\baqua\s+wave\s+refractor\b", re.I)
_RE_AQUA_REPTILIAN_REFRACTOR = re.compile(r"\baqua\s+reptilian\b", re.I)
_RE_FUCHSIA_REPTILIAN_REFRACTOR = re.compile(
    r"\b(?:fuchsia|fuschia|pink)\s+reptilian\b",
    re.I,
)
_RE_STEEL_METAL_REFRACTOR = re.compile(
    r"\bsteel\s+metal\s+refractor\b|\bchrome\s+steel\s+metal\s+refractor\b", re.I
)
_RE_ETCHED_IN_GLASS = re.compile(r"\betched\s+in\s+glass\b", re.I)
_RE_IMAGE_VARIATION = re.compile(r"\bimage\s+variation\b", re.I)
# Match "X Refractor", "X-Fractor", "X Fractor", "Xfractor" (align with `z10_bowman_listing_classifier.RX_X_FRACTOR`).
_RE_X_FRACTOR_PHRASE = re.compile(
    r"\bx[\s-]?(?:refractor|fractor)\b|\bxfractor\b",
    re.I,
)
# Sellers put "1st", team, SSP between finish and "refractor" — require both tokens, any order.
_RE_SPARKLE_REFRACTOR = re.compile(
    r"(?=.*\b(?:sparkle|sparkly)\b)(?=.*\brefractor\b)",
    re.I | re.DOTALL,
)
_RE_SPECKLE_REFRACTOR = re.compile(
    r"(?=.*\bspeckle\b)(?=.*\brefractor\b)",
    re.I | re.DOTALL,
)
# Classifier sometimes misses chrome BDC# in noisy titles; still needed for serial→color ladder.
_RE_BDC_CARD_TOKEN = re.compile(r"#?\s*BDC-?\d+", re.I)
# Bowman Draft chrome black parallels (serial /10 — not the standard /73 Black ladder).
_RE_TRUE_BLACK = re.compile(r"\btrue\s+black\b", re.I)
_RE_GEOMETRIC_BLACK = re.compile(r"\bgeometric\s+black\b|\bblack\s+geometric\b", re.I)
# Paper BD black-border parallels (distinct from chrome True Black / geometric black).
_RE_BLACK_BORDER_BD = re.compile(r"\bblack\s+border\b", re.I)
_RE_BD_CARD_NUMBER = re.compile(r"#?\s*BD-\d+", re.I)


def _bdc_printing_plate_detail_from_title(title: str) -> str:
    """Magenta / Cyan / Yellow / Black printing plate vs generic."""
    tl = (title or "").lower()
    if "printing plate" not in tl:
        return "Printing Plate"
    for name in ("magenta", "cyan", "yellow", "black"):
        if re.search(rf"\b{name}\b", tl):
            return f"{name.title()} Printing Plate"
    return "Printing Plate"


def _flags_with_bdc_card_token(title: str, flags: Dict[str, Any]) -> Dict[str, Any]:
    """Treat `#BDC-…` / `BDC-…` in the title as chrome prospect context when `WF_bdc` was not set."""
    if flags.get("WF_bdc"):
        return flags
    if _RE_BDC_CARD_TOKEN.search(title or ""):
        out = dict(flags)
        out["WF_bdc"] = True
        return out
    return flags


_CHROME_REFRACTOR_COLOR_ORDER: List[Tuple[str, str]] = [
    ("purple", "Purple"),
    ("green", "Green"),
    ("yellow", "Yellow"),
    ("black", "Black"),
    ("red", "Red"),
    ("gold", "Gold"),
    ("orange", "Orange"),
]

# Title color hints (most specific first). Avoid matching team names where possible.
_COLOR_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("Sky Blue", re.compile(r"\bsky\s+blue\b|\bblue\s+sky\b", re.I)),
    # Blue parallel (refractor or mojo — mojo is the same Blue parallel for labeling).
    ("Blue", re.compile(r"\bblue\s+refractor\b|\bblue\s+mojo\b", re.I)),
    ("Blue", re.compile(r"\bblue\s+(?:border|paper|parallel|mega|geometric)\b", re.I)),
    # CPA / autos: "Blue /150" often omits "refractor" or "mojo".
    ("Blue", re.compile(r"\bblue\s*/\s*\d+|\bblue\s+/\s*\d+", re.I)),
    ("Aqua Reptilian", re.compile(r"\baqua\s+reptilian\b", re.I)),
    ("Aqua Wave", re.compile(r"\baqua\s+wave\b", re.I)),
    ("Fuchsia Reptilian", re.compile(r"\bfuchsia\s+reptilian\b|\bfuschia\s+reptilian\b", re.I)),
    ("Green Reptilian", re.compile(r"\bgreen\s+reptilian\b", re.I)),
    ("Yellow Reptilian", re.compile(r"\byellow\s+reptilian\b", re.I)),
    ("Purple", re.compile(r"\bpurple\b", re.I)),
    ("Green", re.compile(r"\bgreen\b", re.I)),
    ("Yellow", re.compile(r"\byellow\b", re.I)),
    ("Orange", re.compile(r"\borange\b", re.I)),
    ("Red", re.compile(r"\bred\b", re.I)),
    ("Gold", re.compile(r"\bgold\b", re.I)),
    ("Black", re.compile(r"\bblack\b", re.I)),
    ("Aqua", re.compile(r"\baqua\b", re.I)),
    ("Fuchsia", re.compile(r"\bfuchsia\b|\bfuschia\b", re.I)),
]


def _infer_stock(flags: Dict[str, Any], row: Dict[str, Any]) -> str:
    if (row.get("pilot_is_likely_chrome_base") or "") == "1":
        return "Chrome"
    if (row.get("pilot_is_likely_base") or "") == "1":
        return "Paper"
    if flags.get("WF_bdc"):
        return "Chrome"
    if flags.get("WF_chrome") and not flags.get("WF_paper"):
        return "Chrome"
    if flags.get("WF_paper"):
        return "Paper"
    if flags.get("WF_chrome"):
        return "Chrome"
    return "Unknown"


def _infer_color(title: str, flags: Dict[str, Any]) -> Optional[str]:
    if flags.get("WF_sky_blue"):
        return "Sky Blue"
    if flags.get("WF_orange_border"):
        return "Orange"
    tl = title.lower()
    for label, rx in _COLOR_PATTERNS:
        if rx.search(tl):
            return label
    # Number-only denominators (e.g. "/499" = Sky Blue, "1/5" → /5 = Red) when BDC/CPA context applies.
    so = flags.get("serial_out_of")
    if so is not None and (
        flags.get("WF_chrome_prospect_autographs")
        or flags.get("WF_college_variation")
        or (flags.get("WF_bdc") and (flags.get("WF_refractor") or flags.get("WF_chrome")))
    ):
        try:
            c = _SERIAL_DENOM_TO_BDC_COLOR.get(int(so))
        except (TypeError, ValueError):
            c = None
        if c:
            return c
    return None


def _infer_finish(flags: Dict[str, Any], title: str) -> Optional[str]:
    tl = title.lower()
    if flags.get("WF_superfractor"):
        return "Superfractor"
    if flags.get("WF_printing_plate"):
        return "Printing Plate"
    if flags.get("WF_mini_diamond"):
        return "Mini Diamond"
    if _RE_X_FRACTOR_PHRASE.search(title) or flags.get("WF_x_fractor"):
        return "X-Fractor"
    if flags.get("WF_crystallized"):
        return "Crystallized"
    if flags.get("WF_sapphire"):
        return "Sapphire"
    if flags.get("WF_speckle"):
        return "Speckle"
    if _RE_SPECKLE_REFRACTOR.search(tl):
        return "Speckle"
    if _RE_SPARKLE_REFRACTOR.search(tl):
        return "Sparkle"
    if flags.get("WF_lava"):
        return "Lava"
    if flags.get("WF_shimmer"):
        return "Shimmer"
    if flags.get("WF_wave"):
        return "Wave"
    if flags.get("WF_aqua") and not flags.get("WF_refractor"):
        return "Aqua"
    if flags.get("WF_sparkle"):
        return "Sparkle"
    # Never return "Refractor" here — only BDC plain parallel uses that token (see _bdc_parallel_detail).
    if flags.get("WF_blue_geometric"):
        return "Blue Geometric"
    return None


def _pick_product_group(flags: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    for slug, disp, wf in _GROUP_PRIORITY:
        if flags.get(wf):
            return slug, disp
    return None


def _should_apply_chrome_bdc_parallel_taxonomy(row: Dict[str, Any], flags: Dict[str, Any]) -> bool:
    """
    Chrome prospect parallel line (BDC-* or refractor without #BDC in title).
    Sellers often omit BDC#; generic WF_refractor alone should still map to Chrome (BDC) composites.
    A standard print run alone (e.g. 1/5, /99) implies the matching Bowman color when **WF_bdc** is set.
    Superfractor / printing plate / True Black /10 / geometric black often omit *chrome* in the title;
    **WF_bdc** alone implies the BDC chrome line (sellers only show the BDC#).
    """
    if (row.get("pilot_is_axis") or "") == "1":
        return False
    if (row.get("pilot_is_likely_chrome_base") or "") == "1":
        return False
    title = (row.get("title") or "")
    tl = title.lower()
    if flags.get("WF_superfractor") or flags.get("WF_printing_plate"):
        return True
    so = flags.get("serial_out_of")
    if so == 10:
        if _RE_TRUE_BLACK.search(tl) and (
            "bowman" in tl
            or flags.get("WF_first")
            or flags.get("WF_bdc")
            or flags.get("WF_chrome")
        ):
            return True
        if _RE_GEOMETRIC_BLACK.search(tl) and (flags.get("WF_chrome") or flags.get("WF_bdc")):
            return True
    if so is not None and flags.get("WF_bdc"):
        try:
            if int(so) in _SERIAL_DENOM_TO_BDC_COLOR:
                return True
        except (TypeError, ValueError):
            pass
    if not flags.get("WF_bdc"):
        if flags.get("WF_sky_blue") and flags.get("WF_refractor"):
            pass
        elif flags.get("WF_refractor"):
            pass
        else:
            return False
    if not (
        flags.get("WF_chrome")
        or flags.get("WF_refractor")
        or flags.get("WF_x_fractor")
        or flags.get("WF_sky_blue")
        or flags.get("WF_bdc")
    ):
        return False
    return True


def _bdc_parallel_detail(row: Dict[str, Any], flags: Dict[str, Any]) -> Optional[str]:
    """Human-readable BDC parallel slice (color/finish) or None."""
    if not _should_apply_chrome_bdc_parallel_taxonomy(row, flags):
        return None
    title = (row.get("title") or "").lower()
    raw_title = row.get("title") or ""
    if flags.get("WF_superfractor"):
        return "Superfractor"
    if flags.get("WF_printing_plate"):
        return _bdc_printing_plate_detail_from_title(raw_title)
    if _RE_TRUE_BLACK.search(title) and (
        flags.get("serial_out_of") == 10 or re.search(r"\b10/10\b", raw_title)
    ):
        return "True Black /10"
    if _RE_GEOMETRIC_BLACK.search(title) and flags.get("serial_out_of") == 10:
        return "Black Geometric /10"
    if flags.get("WF_x_fractor") or _RE_X_FRACTOR_PHRASE.search(raw_title):
        return "X-Fractor"
    if flags.get("WF_sky_blue"):
        return "Sky Blue"
    if flags.get("WF_mini_diamond"):
        return "Mini Diamond"
    if flags.get("WF_sapphire"):
        return "Sapphire"
    if flags.get("WF_refractor") and _RE_SPECKLE_REFRACTOR.search(title):
        return "Speckle Refractor"
    if flags.get("WF_refractor") and _RE_SPARKLE_REFRACTOR.search(title):
        return "Sparkle"
    if flags.get("WF_refractor") and (
        _RE_BLUE_MOJO_REFRACTOR.search(title) or _RE_BLUE_REFRACTOR_PHRASE.search(title)
    ):
        return "Blue"
    if flags.get("WF_refractor") and _RE_AQUA_WAVE_REFRACTOR.search(title):
        return "Aqua /125"
    if flags.get("WF_refractor") and _RE_AQUA_REPTILIAN_REFRACTOR.search(title):
        return "Aqua Reptilian"
    if flags.get("WF_refractor") and _RE_FUCHSIA_REPTILIAN_REFRACTOR.search(title):
        return "Fuchsia Reptilian /199"
    if flags.get("WF_refractor") and _RE_STEEL_METAL_REFRACTOR.search(title):
        return "Steel Metal /100"
    if flags.get("WF_refractor"):
        # Sellers reverse word order: "Refractor Aqua", "Refractor Blue", "Blue … Refractor".
        if (re.search(r"\brefractor\b.*\baqua\b", title) or re.search(r"\baqua\b.*\brefractor\b", title)) and not (
            re.search(r"\baqua\s+wave\b", title) or re.search(r"\baqua\s+reptilian\b", title)
        ):
            return "Aqua /125"
        if re.search(r"\brefractor\b.*\bblue\b", title) or re.search(r"\bblue\b.*\brefractor\b", title):
            return "Blue"
        for word, _ in _CHROME_REFRACTOR_COLOR_ORDER:
            if re.search(rf"\b{re.escape(word)}\b", title):
                return word.capitalize()
        so = flags.get("serial_out_of")
        if so is not None:
            try:
                d = _bdc_parallel_detail_from_serial_denominator(int(so))
                if d:
                    return d
            except (TypeError, ValueError):
                pass
        return "Refractor"
    so = flags.get("serial_out_of")
    if so is not None:
        try:
            d = _bdc_parallel_detail_from_serial_denominator(int(so))
            if d:
                return d
        except (TypeError, ValueError):
            pass
    return None


def _join_parts(parts: List[str]) -> str:
    return " · ".join(p for p in parts if p)


def _serial_denominator_for_product_group_taxonomy(flags: Dict[str, Any]) -> Optional[int]:
    """
    Print run for suffixing insert-line (product group) composites; excludes year-shaped false positives.
    """
    so = flags.get("serial_out_of")
    if so is None:
        return None
    try:
        n = int(so)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    if 2000 <= n <= 2035:
        return None
    return n


def _any_mid_segment_has_print_run(parts: List[str]) -> bool:
    """True if any segment after the insert-line prefix (before optional Auto) contains ``/digits``."""
    if len(parts) < 2:
        return False
    has_auto = parts[-1] == "Auto"
    mid = parts[1:-1] if has_auto else parts[1:]
    return any(re.search(r"/\d+\b", seg) for seg in mid)


def _append_serial_suffix_to_product_group_parts(
    parts: List[str], flags: Dict[str, Any]
) -> List[str]:
    """
    Fallback: when ``serial_out_of`` is set but no mid segment yet carries a print run (e.g. generic
    ``Bowman Draft Night /99`` with no color), append `` /N`` to the last non-Auto segment.

    Skips when any mid segment already has ``/digits`` (from ladder collapse or color apply).
    """
    n = _serial_denominator_for_product_group_taxonomy(flags)
    if n is None or not parts:
        return parts
    if _any_mid_segment_has_print_run(parts):
        return parts
    out = list(parts)
    if out[-1] == "Auto":
        if len(out) < 2:
            return out
        idx = -2
    else:
        idx = -1
    last = out[idx]
    if re.search(r"/\d+\b", last):
        return out
    out[idx] = f"{last} /{n}"
    return out


def _apply_color_ladder_serial_from_flags(parts: List[str], flags: Dict[str, Any]) -> List[str]:
    """
    When ``serial_out_of`` matches a Bowman hobby color's ladder denominator, rewrite that color
    segment to ``Color /N`` (same token shape as BDC collapse).
    """
    so = _serial_denominator_for_product_group_taxonomy(flags)
    if so is None or len(parts) < 2:
        return parts
    has_auto = parts[-1] == "Auto"
    body = parts[:-1] if has_auto else parts[:]
    out: List[str] = [body[0]]
    for seg in body[1:]:
        if re.search(r"/\d+\b", seg):
            out.append(seg)
            continue
        if seg in _BDC_COLOR_SERIAL:
            suf = _BDC_COLOR_SERIAL[seg]
            m = re.search(r"/(\d+)", suf)
            if m and int(m.group(1)) == so:
                out.append(f"{seg} {suf}")
                continue
        out.append(seg)
    if has_auto:
        out.append("Auto")
    return out


def _finalize_product_group_parallel_parts(
    parts: List[str], slug: str, flags: Dict[str, Any]
) -> List[str]:
    """
    Product-group insert lines: reuse BDC aqua + colored collapse on a temporary BDC prefix, then
    apply ladder serial to color segments, then generic suffix for lines without a color (e.g. bare ``… /99``).
    """
    if slug not in _insert_line_parallel_taxonomy_slugs() or len(parts) < 2:
        return _append_serial_suffix_to_product_group_parts(parts, flags)
    orig = parts[0]
    fake = [BDC_PRIMARY_FAMILY] + parts[1:]
    fake = _collapse_bdc_aqua_parallel_parts(fake)
    fake = _collapse_bdc_colored_parallel_parts(fake)
    fake[0] = orig
    parts = fake
    parts = _apply_color_ladder_serial_from_flags(parts, flags)
    return _append_serial_suffix_to_product_group_parts(parts, flags)


def _collapse_bdc_colored_parallel_parts(parts: List[str]) -> List[str]:
    """
    Collapse e.g. **Green · Lava**, **Green · Sapphire**, **Gold · Wave · Shimmer** into **Green /99**,
    **Gold /50**, etc. Leaves plain **Refractor**, reptilian / steel / X-Fractor lines, and unknown stacks unchanged.
    """
    if len(parts) < 2 or parts[0] not in _BDC_FAMILY_PREFIXES:
        return parts
    prefix = parts[0]
    has_auto = parts[-1] == "Auto"
    mid = parts[1:-1] if has_auto else parts[1:]
    if not mid:
        return parts
    jm = " · ".join(mid)
    if any(
        x in jm
        for x in (
            "Reptilian",
            "Steel Metal",
            "X-Fractor",
            "Printing Plate",
            "Geometric",
            "Mini Diamond",
            "Logo Refractor",
        )
    ):
        return parts
    if mid[0] in ("Refractor", "Parallel", "Sparkle"):
        return parts
    color = mid[0]
    if color not in _BDC_COLOR_SERIAL:
        return parts
    for seg in mid[1:]:
        if seg not in _BDC_MERGE_FINISHES:
            return parts
    suffix = _BDC_COLOR_SERIAL[color]
    token = f"{color} {suffix}"
    out = [prefix, token]
    if has_auto:
        out.append("Auto")
    return out


def _collapse_bdc_aqua_parallel_parts(parts: List[str]) -> List[str]:
    """
    Bowman Draft aqua /125 parallel line: sellers and classifiers stack color + finish (Aqua Wave,
    Wave, Lava, etc.). Collapse those to a single **Aqua /125** slice (same serial family).
    Does not alter **Aqua Reptilian** (different parallel).
    """
    if len(parts) < 2 or parts[0] not in _BDC_FAMILY_PREFIXES:
        return parts
    prefix = parts[0]
    has_auto = parts[-1] == "Auto"
    mid = parts[1:-1] if has_auto else parts[1:]
    if not mid:
        return parts
    jm = " · ".join(mid)
    if "Reptilian" in jm:
        return parts
    if not any("aqua" in seg.lower() for seg in mid):
        return parts
    if len(mid) == 1:
        only = mid[0]
        if only in ("Aqua Wave", "Aqua Wave /125", "Aqua /125"):
            out = [prefix, "Aqua /125"]
            if has_auto:
                out.append("Auto")
            return out
        return parts
    out = [prefix, "Aqua /125"]
    if has_auto:
        out.append("Auto")
    return out


def finalize_bdc_composite_string(s: str) -> str:
    """
    Normalize Bowman Draft **Chrome** (BDC stock) labels: aqua /125 family, then standard color + print-run buckets
    (Green /99, Gold /50, Blue /150, …) with mergeable finish noise (Wave, Lava, Shimmer, …).
    Same collapse applies to **Chrome Prospect College Variations · …** (team photo SP line).
    Accepts legacy strings beginning with **BDC Chrome Prospect** and rewrites them to **Chrome**.
    """
    if s.startswith(_LEGACY_BDC_PRIMARY_PREFIX):
        s = BDC_PRIMARY_FAMILY + s[len(_LEGACY_BDC_PRIMARY_PREFIX) :]
    if s.startswith("Chrome Prospect College Variations"):
        parts = s.split(" · ")
        parts = _collapse_bdc_aqua_parallel_parts(parts)
        parts = _collapse_bdc_colored_parallel_parts(parts)
        return _join_parts(parts)
    if s == BDC_PRIMARY_FAMILY or s.startswith(f"{BDC_PRIMARY_FAMILY} · ") or s.startswith(
        f"{BDC_PRIMARY_FAMILY} /"
    ):
        parts = s.split(" · ")
        parts = _collapse_bdc_aqua_parallel_parts(parts)
        parts = _collapse_bdc_colored_parallel_parts(parts)
        return _join_parts(parts)
    return s


def format_axis_card_type(row: Dict[str, Any]) -> str:
    """Bowman Axis insert: Base vs Parallel (silver parallel), color parallels, X-Fractor, Superfractor, Auto."""
    title = row.get("title") or ""
    flags = flags_for_title(title)
    is_auto = bool(flags.get("WF_auto"))
    parts: List[str] = ["Bowman Axis"]

    if flags.get("WF_superfractor"):
        parts.append("Superfractor")
    elif flags.get("WF_mini_diamond"):
        parts.append("Mini Diamond")
    else:
        so = flags.get("serial_out_of")
        s = title.lower()
        color: Optional[str] = None
        if so == 99 or _RE_AXIS_GREEN.search(s):
            color = "Green"
        elif so == 50 or _RE_AXIS_GOLD.search(s):
            color = "Gold"
        elif _RE_AXIS_ORANGE.search(s):
            color = "Orange"
        elif _RE_AXIS_BLACK.search(s):
            color = "Black"
        elif _RE_AXIS_RED.search(s):
            color = "Red"
        if color:
            parts.append(color)
        elif flags.get("WF_x_fractor"):
            parts.append("X-Fractor")
        elif flags.get("WF_refractor"):
            parts.append("Parallel")
        else:
            parts.append("Base")

    if is_auto:
        parts.append("Auto")
    return _join_parts(parts)


def build_composite_card_type(row: Dict[str, Any]) -> Optional[str]:
    """
    Return composite card type, or None to fall back to legacy nb_* labeling.
    """
    title = row.get("title") or ""
    flags = _flags_with_bdc_card_token(title, flags_for_title(title))

    # Selling / noise — let legacy handle reason-code buckets.
    if flags.get("WF_lot") or flags.get("WF_complete_set") or flags.get("WF_pick") or flags.get("WF_set_builder"):
        return None
    if flags.get("WF_presale"):
        return None

    is_auto = bool(flags.get("WF_auto"))

    # Paper BD black-border parallels (not chrome True Black / geometric).
    tl0 = title.lower()
    if _RE_BLACK_BORDER_BD.search(title) and not flags.get("WF_chrome"):
        if _RE_BD_CARD_NUMBER.search(title) or (
            flags.get("WF_paper") and "bowman" in tl0
        ):
            parts = ["Base-Paper", "Black Border"]
            if is_auto:
                parts.append("Auto")
            return _join_parts(parts)

    # Title-only overrides (classifier gaps).
    if _RE_ETCHED_IN_GLASS.search(title):
        c = _infer_color(title, flags)
        fin = _infer_finish(flags, title)
        parts = ["Etched in Glass", c, fin]
        if is_auto:
            parts.append("Auto")
        return _join_parts([p for p in parts if p])

    if _RE_IMAGE_VARIATION.search(title):
        c = _infer_color(title, flags)
        fin = _infer_finish(flags, title)
        parts = ["Image Variations", c, fin]
        if is_auto:
            parts.append("Auto")
        return _join_parts([p for p in parts if p])

    if _RE_X_FRACTOR_PHRASE.search(title) and not flags.get("WF_axis"):
        parts = [BDC_PRIMARY_FAMILY, "X-Fractor"]
        if is_auto:
            parts.append("Auto")
        return _join_parts(parts)

    tl = title.lower()
    if _RE_SPECKLE_REFRACTOR.search(tl):
        parts = [BDC_PRIMARY_FAMILY, "Speckle Refractor"]
        if is_auto:
            parts.append("Auto")
        return _join_parts(parts)
    if _RE_SPARKLE_REFRACTOR.search(tl):
        parts = [BDC_PRIMARY_FAMILY, "Sparkle"]
        if is_auto:
            parts.append("Auto")
        return _join_parts(parts)

    group = _pick_product_group(flags)
    color = _infer_color(title, flags)

    if group:
        slug, gdisp = group
        parts = [gdisp]
        if color:
            parts.append(color)
        fin = _infer_finish(flags, title)
        if slug == "crystallized" and fin == "Crystallized":
            fin = None
        if fin:
            parts.append(fin)
        if is_auto:
            parts.append("Auto")
        parts = _finalize_product_group_parallel_parts(parts, slug, flags)
        return _join_parts(parts)

    # No insert line matched: BDC chrome parallels (colors / refractor ladder — stock omitted).
    if _should_apply_chrome_bdc_parallel_taxonomy(row, flags):
        detail = _bdc_parallel_detail(row, flags)
        parts = [BDC_PRIMARY_FAMILY]
        if detail:
            parts.append(detail)
        if is_auto:
            parts.append("Auto")
        return _join_parts(parts)

    return None

