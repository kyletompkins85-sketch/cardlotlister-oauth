# Cmd+F: GH_ANCHOR_BOWMAN_2025_RETAIL_FLAGS_A1B2C3D4
"""
2025 Bowman **retail** listing word flags (``WF_*``) and group placeholders (``grp_*``).

**Source of truth:** ``docs/classification/2025_bowman_classifier_notes.md`` only — exclusions,
paper vs chrome clues, the card vs modifiers mental model, **serials** (``WF_serial_fraction`` for
``a/b``; ``WF_serial_out_of`` + ``serial_out_of_for_title()`` for parsed denominators; lone ``/N`` is
ignored when ``N`` equals the checklist slot from ``checklist_slot_int`` (avoids ``/15`` vs card ``#15``).
Print-run hash style requires ``#/`` (e.g. ``#/99``), not plain ``#99``. Parallel **colors** (``WF_color_*``), named **patterns** (``WF_pattern_*`` vs
generic ``WF_pattern`` for the word *pattern*), named **prints** (``WF_print_*`` plus ``WF_refractor``
/ ``WF_printing_plate``), and insert **names** from the set distinction section. This module does **not** mirror Bowman Draft (``z10_bowman_listing_classifier``)
parallel taxonomy or old CT-style groupings.

``grp_*`` keys exist as **reserved slots** (all false) until retail-specific combination rules
are defined; they are not copied from Draft.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, Mapping, Optional, Sequence

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------


def _re(pat: str) -> re.Pattern[str]:
    return re.compile(pat, re.IGNORECASE)


def _has(rx: re.Pattern[str], s: str) -> bool:
    return rx.search(s) is not None


def _norm_title(title: str) -> str:
    return unicodedata.normalize("NFKC", (title or "").strip())


# ---------------------------------------------------------------------------
# Excluded listings (notes §Excluded listings) — no Draft-only seller headers
# ---------------------------------------------------------------------------

_RX_COMPLETE_SET = _re(
    r"\bcomplete\s+set\b|\bset\s+complete\b|\bcomplete\b.*\bset\b"
)
_RX_PICK = _re(
    r"\b(pick\s*your|you\s*pick|u\s*pick|pick\s*one)\b"
    r"|\b(choose\s*your|choose\s*one)\b"
    r"|\bpick\s*&\s*choose\b"
    r"|\bchoose\s+from\b"
    r"|\b\d+\s+card\s+minimum\b"
    r"|\bminimum\s+\d+\s+cards?\b"
    r"|\binserts\s*-\s*.+,.+"
    r"|\bSingles\s*-\s*(?:volume|discount)"
)
_RX_LOT = _re(r"\blot\b|\blots\b")
_RX_SET_BUILDER = _re(
    r"\bset\s*builder\b|\bcomplete\s+your\s+set\b|\bbuild\s+your\s+set\b"
)
_RX_PRESALE = _re(r"\bpre[\s-]?sale\b|\bpre[\s-]?order\b|\bpresale\b|\bpreorder\b")
_RX_GRADED = _re(r"\bpsa\b|\bbgs\b|\bsgc\b|\bcgc\b|\bgem\s*mint\b|\bgraded\b")

# ---------------------------------------------------------------------------
# Paper vs Chrome (notes §Paper vs Chrome — explicit heuristics)
# ---------------------------------------------------------------------------
# ``WF_chrome``: literal ``chrome`` **or** chrome-line checklist codes (BCP / CPA / CRA), with the
# same strict hyphen / glued-digit rules as checklist code extraction (no ``ROY``+``als`` false hits).
# ``WF_paper``: literal ``paper`` **or** paper-line checklist codes (BPA / PRV / BP), ``BPA`` before
# ``BP`` in the alternation so ``BPA-…`` is not read as ``BP``.

_RX_CHROME = _re(r"\bchrome\b")
_RX_CHROME_CHECKLIST_HYPHEN = _re(
    r"\b(BCP|CPA|CRA)\s*-\s*(\d{1,4}|[A-Za-z]{2,5})(?!\d|[A-Za-z])\b"
)
_RX_CHROME_CHECKLIST_GLUED = _re(r"\b(BCP|CPA|CRA)(\d{1,4})(?!\d)\b")

_RX_PAPER = _re(r"\bpaper\b")
_RX_PAPER_CHECKLIST_HYPHEN = _re(
    r"\b(BPA|PRV|BP)\s*-\s*(\d{1,4}|[A-Za-z]{2,5})(?!\d|[A-Za-z])\b"
)
_RX_PAPER_CHECKLIST_GLUED = _re(r"\b(BPA|PRV|BP)(\d{1,4})(?!\d)\b")

_RX_TRUE_BLUE = _re(r"\btrue\s+blue\b")
_RX_TRUE_RED = _re(r"\btrue\s+red\b")


def _title_suggests_chrome_stock(s: str) -> bool:
    return (
        _has(_RX_CHROME, s)
        or _has(_RX_CHROME_CHECKLIST_HYPHEN, s)
        or _has(_RX_CHROME_CHECKLIST_GLUED, s)
    )


def _title_suggests_paper_stock(s: str) -> bool:
    return (
        _has(_RX_PAPER, s)
        or _has(_RX_PAPER_CHECKLIST_HYPHEN, s)
        or _has(_RX_PAPER_CHECKLIST_GLUED, s)
    )

# ---------------------------------------------------------------------------
# Card vs modifiers (notes §Mental model — keywords only, not a Draft parallel stack)
# ---------------------------------------------------------------------------

_RX_REFRACTOR = _re(r"\brefractor\b")
_RX_PRINTING_PLATE = _re(r"\bprinting\s*plates?\b")
_RX_PATTERN = _re(r"\bpattern\b")
_RX_SERIAL_FRACTION = _re(r"(?<!\d)\d{1,4}\s*[\/／⁄]\s*\d{1,4}(?:,\d{3})?(?!\d)")
# Serial denominator extraction (``serial_out_of_for_title``): ``a/b`` then ``#/N`` (slash required)
# then lone ``/N`` (same year skip as ``cardmatch.serial_scarcity`` for ``/2025``-style titles).
_RX_SERIAL_PAIR = _re(r"(?:^|[^\d/])(\d{1,6})\s*[\/／⁄]\s*(\d{1,6})(?:,\d{3})?(?!\d)")
_RX_SERIAL_SLASH_DENOM = _re(r"[\/／⁄]\s*(\d{1,6})(?:,\d{3})?(?!\d)")
_RX_SERIAL_HASH = _re(r"#\s*/\s*(\d{2,6})\b")

_SLASH_TRANSLATION = str.maketrans({"\uFF0F": "/", "\u2044": "/"})


def _title_for_serial_scan(title: str) -> str:
    s = _norm_title(title).translate(_SLASH_TRANSLATION)
    return s


def checklist_slot_int(card_number: Optional[str]) -> Optional[int]:
    """
    Numeric roster slot from a checklist key when unambiguous: plain ``99``, or hyphen suffix
    ``HS-11`` → ``11``, ``BP-15`` → ``15``. Letter-only auto codes (``CPA-JW``) → ``None``.
    """
    cn = (card_number or "").strip().upper()
    if not cn:
        return None
    if cn.isdigit():
        return int(cn)
    m = re.match(r"^[A-Z]{1,12}-(\d+)$", cn)
    if m:
        return int(m.group(1))
    return None


def serial_out_of_for_title(title: str, checklist_slot: Optional[int] = None) -> Optional[int]:
    """
    Best-effort print-run / serial **denominator** from the title (e.g. ``/499`` → ``499``,
    ``116/199`` → ``199``, ``#/99`` → ``99``).

    When ``checklist_slot`` is set, a **lone** ``/N`` (not from an ``a/b`` fraction) matching that
    slot is ignored so ``/15`` is not read as serial ``15`` for card ``BP-15``.

    Skips ``/N`` when ``N`` is in ``2000..2035`` (year noise). Returns ``None`` when nothing matches.
    """
    s = _title_for_serial_scan(title)
    if not s:
        return None
    m_pair = _RX_SERIAL_PAIR.search(s)
    if m_pair:
        try:
            return int(m_pair.group(2).replace(",", ""))
        except ValueError:
            pass
    m_hash = _RX_SERIAL_HASH.search(s)
    if m_hash:
        try:
            v = int(m_hash.group(1).replace(",", ""))
        except ValueError:
            pass
        else:
            if checklist_slot is None or v != checklist_slot:
                return v
    for m in _RX_SERIAL_SLASH_DENOM.finditer(s):
        try:
            n = int(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if 2000 <= n <= 2035:
            continue
        if checklist_slot is not None and n == checklist_slot:
            continue
        return n
    return None


# ---------------------------------------------------------------------------
# Parallel colors (notes §Base card parallel — colors, §Paper/base auto, §Chrome — colors)
# ---------------------------------------------------------------------------

_RX_COLOR_SKY_BLUE = _re(r"\bsky\s+blue\b")
_RX_COLOR_NEON_GREEN = _re(r"\bneon\s+green\b")
_RX_COLOR_FUCHSIA = _re(r"\bfuchsia\b")
_RX_COLOR_PURPLE = _re(r"\bpurple\b")
_RX_COLOR_PINK = _re(r"\bpink\b")
_RX_COLOR_BLUE = _re(r"\bblue\b")
_RX_COLOR_GREEN = _re(r"\bgreen\b")
_RX_COLOR_YELLOW = _re(r"\byellow\b")
_RX_COLOR_GOLD = _re(r"\bgold\b")
_RX_COLOR_ORANGE = _re(r"\borange\b")
_RX_COLOR_BLACK = _re(r"\bblack\b")
_RX_COLOR_RED = _re(r"\bred\b")
_RX_COLOR_PLATINUM = _re(r"\bplatinum\b")
_RX_COLOR_AQUA = _re(r"\baqua\b")
_RX_COLOR_ROSE_GOLD = _re(r"\brose\s+gold\b")

# ---------------------------------------------------------------------------
# Named parallel patterns (notes §Chrome variation — patterns; ``WF_pattern`` = word "pattern")
# ---------------------------------------------------------------------------

_RX_PATTERN_GEOMETRIC = _re(r"\bgeometric\b")
_RX_PATTERN_LAVA = _re(r"\blava\b")
_RX_PATTERN_REPTILIAN = _re(r"\breptilian\b")
_RX_PATTERN_SHIMMER = _re(r"\bshimmer\b")
_RX_PATTERN_GRASS = _re(r"\bgrass\b")
_RX_PATTERN_RAYWAVE = _re(r"\braywave\b")
_RX_PATTERN_WAVE = _re(r"\bwave\b")
_RX_PATTERN_MINI_DIAMOND = _re(r"\bmini\s+diamond\b")

# ---------------------------------------------------------------------------
# Named prints (notes §Base unique prints + §Chrome — unique prints; excludes generic refractor / plate)
# ---------------------------------------------------------------------------

_RX_PRINT_RETRO_LOGO_FOIL = _re(r"\bretro\s+logo\s+foil\b")
_RX_PRINT_XFRACTOR = _re(r"\bx[\s-]?fractor\b")
_RX_PRINT_SPECKLE = _re(r"\bspeckle\b")
_RX_PRINT_STEEL_METAL = _re(r"\bsteel\s+metal\b")
_RX_PRINT_PEARL = _re(r"\bpearl\b")
_RX_PRINT_SNACKPACK = _re(
    r"\bsnack\s*pack\b|\bgumball\b|\bpopcorn\b|\bpeanuts?\b|\bsunflower\s+seeds?\b"
)
_RX_PRINT_FIREFRACTOR = _re(r"\bfire\s*fractors?\b")
_RX_PRINT_SUPERFRACTOR = _re(r"\bsuper\s*fractors?\b")

# ---------------------------------------------------------------------------
# Auto language + CPA sticker example from notes (CPA-JW)
# ---------------------------------------------------------------------------

_RX_AUTO = _re(
    r"\bauto\b|\bautographs?\b|\ba/u\b|\bon-card\b|\bsigned\b|\bsignatures?\b"
)
_RX_CPA_STICKER = _re(r"\bCPA-[A-Z]{2,5}\b")

# ---------------------------------------------------------------------------
# Product words that show up in real titles (not a Draft taxonomy)
# ---------------------------------------------------------------------------

_RX_BOWMAN = _re(r"\bbowman\b")
_RX_BOWMANS_BEST = _re(r"\bbowman'?s\s+best\b|\bbowmans\s+best\b")
_RX_BOWMAN_DRAFT = _re(r"\bbowman\s+draft\b")
_RX_SAPPHIRE_EDITION = _re(r"\bsapphire\s+edition\b|\bbowman\s+sapphire\b")

# ---------------------------------------------------------------------------
# Set distinction section — **phrases** from the doc (avoid ROY- vs Royals substring bugs)
# ---------------------------------------------------------------------------

_RX_INSERT_HOBBY_STARS = _re(r"\bhobby\s+stars\b")
_RX_INSERT_SCOUTS_TOP_100 = _re(r"\bscouts\s+top\s*100\b")
_RX_INSERT_TOP_100 = _re(r"\btop\s*100\b")
_RX_INSERT_SPOTLIGHTS = _re(r"\bbowman\s+spotlights?\b|\bspotlights?\b")
_RX_INSERT_ROY_FAVORITES = _re(r"\brookie\s+of\s+the\s+year\s+favorites\b")
# Phrase + strict ROY-… / #ROY-… codes (hyphen required so ``Royals`` is not a hit).
_RX_ROOKIE_OF_THE_YEAR = _re(
    r"\brookie\s+of\s+the\s+year\b"
    r"|#\s*ROY-\d{1,3}\b"
    r"|\bROY-\d{1,3}\b"
)
_RX_INSERT_VIP = _re(r"\bvery\s+important\s+prospects\b")
_RX_INSERT_ANIME = _re(r"\banime\b")
_RX_INSERT_GREATNESS_LOADING = _re(r"\bgreatness\s+loading\b")
_RX_INSERT_ROCKSTAR_ROOKIES = _re(r"\brockstar\s+rookies\b|\brockstart\s+rookies\b")
_RX_INSERT_CRYSTALIZED = _re(r"\bcrystalized\b|\bcrystalised\b")
_RX_INSERT_ETCHED_GLASS = _re(
    r"\betched\s+in\s+glass\b"
    r"|\bstained\s+glass\b"
    r"|\bethced\s+in\s+glass\b"
)
_RX_LINE_BOWMAN_PROSPECTS = _re(r"\bbowman\s+prospects?\b")
_RX_LINE_CHROME_PROSPECTS = _re(r"\bchrome\s+prospects?\b")

# ---------------------------------------------------------------------------
# Insert / product lines **not** in 2025 Bowman retail (exclude from retail pipeline)
# ---------------------------------------------------------------------------

_RX_INSERT_MELT_MASHERS = _re(r"\bmelt\s+mashers\b")
_RX_INSERT_ASCENSIONS = _re(r"\bascensions\b")
_RX_INSERT_GPK = _re(r"\bGPK\b")
_RX_INSERT_IT_CAME_TO_THE_LEAGUE = _re(r"\bit\s+came\s+to\s+the\s+league\b")
_RX_INSERT_METEORIC_RISE = _re(r"\bmeteoric\s+rise\b")
_RX_INSERT_MAX_VOLUME = _re(r"\bmax\s+volume\b")
_RX_INSERT_ADIOS = _re(r"\badios\b")

# ---------------------------------------------------------------------------
# Stable key order
# ---------------------------------------------------------------------------

WF_FLAG_KEYS: Sequence[str] = (
    # Exclusions (notes §Excluded listings)
    "WF_complete_set",
    "WF_pick",
    "WF_set_builder",
    "WF_presale",
    "WF_graded",
    "WF_lot",
    # Paper vs Chrome (notes §Paper vs Chrome)
    "WF_chrome",
    "WF_paper",
    "WF_true_blue",
    "WF_true_red",
    # Product
    "WF_bowman",
    "WF_bowmans_best",
    "WF_bowman_draft",
    "WF_sapphire_edition",
    # Modifiers (notes §Mental model)
    "WF_refractor",
    "WF_printing_plate",
    "WF_pattern",
    "WF_serial_fraction",
    "WF_serial_out_of",
    # Parallel colors (notes — base + chrome + auto color lists)
    "WF_color_aqua",
    "WF_color_black",
    "WF_color_blue",
    "WF_color_fuchsia",
    "WF_color_gold",
    "WF_color_green",
    "WF_color_neon_green",
    "WF_color_orange",
    "WF_color_pink",
    "WF_color_platinum",
    "WF_color_purple",
    "WF_color_red",
    "WF_color_rose_gold",
    "WF_color_sky_blue",
    "WF_color_yellow",
    # Named parallel patterns (notes §Chrome — patterns)
    "WF_pattern_geometric",
    "WF_pattern_grass",
    "WF_pattern_lava",
    "WF_pattern_mini_diamond",
    "WF_pattern_raywave",
    "WF_pattern_reptilian",
    "WF_pattern_shimmer",
    "WF_pattern_wave",
    # Named prints (notes — retro logo foil, xfractor, speckle, steel metal, pearl, snackpack, fire/super)
    "WF_print_firefractor",
    "WF_print_pearl",
    "WF_print_retro_logo_foil",
    "WF_print_snackpack",
    "WF_print_speckle",
    "WF_print_steel_metal",
    "WF_print_superfractor",
    "WF_print_xfractor",
    # Auto (notes §Auto vs non-auto + CPA example)
    "WF_auto",
    "WF_cpa_sticker",
    # Rookie of the Year (phrase or ROY insert code; ``WF_insert_roy_favorites`` is the named insert line only)
    "WF_rookie_of_the_year",
    # Insert / line phrases (notes §Set Distinction Sections)
    "WF_insert_hobby_stars",
    "WF_insert_scouts_top_100",
    "WF_insert_top_100",
    "WF_insert_spotlights",
    "WF_insert_roy_favorites",
    "WF_insert_vip",
    "WF_insert_anime",
    "WF_insert_greatness_loading",
    "WF_insert_rockstar_rookies",
    "WF_insert_crystalized",
    "WF_insert_etched_glass",
    "WF_line_bowman_prospects",
    "WF_line_chrome_prospects",
    # Not in Bowman retail checklist (pipeline exclusion)
    "WF_insert_adios",
    "WF_insert_ascensions",
    "WF_insert_gpk",
    "WF_insert_it_came_to_the_league",
    "WF_insert_max_volume",
    "WF_insert_melt_mashers",
    "WF_insert_meteoric_rise",
)

# Reserved for future combinator maps — **not** populated from Draft logic.
GROUP_FLAG_KEYS: Sequence[str] = tuple(f"grp_reserved_{i:02d}" for i in range(1, 21))


def word_flags_for_title(title: str, checklist_slot: Optional[int] = None) -> Dict[str, bool]:
    """Return every ``WF_*`` flag for ``title`` (NFKC-normalized).

    Pass ``checklist_slot`` when the matched roster slot is known so ``WF_serial_out_of`` ignores
    lone ``/N`` that only echo the card number (see :func:`serial_out_of_for_title`).
    """
    s = _norm_title(title)
    out: Dict[str, bool] = {k: False for k in WF_FLAG_KEYS}
    if not s:
        return out

    _so = serial_out_of_for_title(title, checklist_slot)
    out.update(
        {
            "WF_complete_set": _has(_RX_COMPLETE_SET, s),
            "WF_pick": _has(_RX_PICK, s),
            "WF_set_builder": _has(_RX_SET_BUILDER, s),
            "WF_presale": _has(_RX_PRESALE, s),
            "WF_graded": _has(_RX_GRADED, s),
            "WF_lot": _has(_RX_LOT, s),
            "WF_chrome": _title_suggests_chrome_stock(s),
            "WF_paper": _title_suggests_paper_stock(s),
            "WF_true_blue": _has(_RX_TRUE_BLUE, s),
            "WF_true_red": _has(_RX_TRUE_RED, s),
            "WF_bowman": _has(_RX_BOWMAN, s),
            "WF_bowmans_best": _has(_RX_BOWMANS_BEST, s),
            "WF_bowman_draft": _has(_RX_BOWMAN_DRAFT, s),
            "WF_sapphire_edition": _has(_RX_SAPPHIRE_EDITION, s),
            "WF_refractor": _has(_RX_REFRACTOR, s),
            "WF_printing_plate": _has(_RX_PRINTING_PLATE, s),
            "WF_pattern": _has(_RX_PATTERN, s),
            "WF_serial_fraction": _has(_RX_SERIAL_FRACTION, s),
            "WF_serial_out_of": _so is not None,
            "WF_color_aqua": _has(_RX_COLOR_AQUA, s),
            "WF_color_black": _has(_RX_COLOR_BLACK, s),
            "WF_color_blue": _has(_RX_COLOR_BLUE, s),
            "WF_color_fuchsia": _has(_RX_COLOR_FUCHSIA, s),
            "WF_color_gold": _has(_RX_COLOR_GOLD, s),
            "WF_color_green": _has(_RX_COLOR_GREEN, s),
            "WF_color_neon_green": _has(_RX_COLOR_NEON_GREEN, s),
            "WF_color_orange": _has(_RX_COLOR_ORANGE, s),
            "WF_color_pink": _has(_RX_COLOR_PINK, s),
            "WF_color_platinum": _has(_RX_COLOR_PLATINUM, s),
            "WF_color_purple": _has(_RX_COLOR_PURPLE, s),
            "WF_color_red": _has(_RX_COLOR_RED, s),
            "WF_color_rose_gold": _has(_RX_COLOR_ROSE_GOLD, s),
            "WF_color_sky_blue": _has(_RX_COLOR_SKY_BLUE, s),
            "WF_color_yellow": _has(_RX_COLOR_YELLOW, s),
            "WF_pattern_geometric": _has(_RX_PATTERN_GEOMETRIC, s),
            "WF_pattern_grass": _has(_RX_PATTERN_GRASS, s),
            "WF_pattern_lava": _has(_RX_PATTERN_LAVA, s),
            "WF_pattern_mini_diamond": _has(_RX_PATTERN_MINI_DIAMOND, s),
            "WF_pattern_raywave": _has(_RX_PATTERN_RAYWAVE, s),
            "WF_pattern_reptilian": _has(_RX_PATTERN_REPTILIAN, s),
            "WF_pattern_shimmer": _has(_RX_PATTERN_SHIMMER, s),
            "WF_pattern_wave": _has(_RX_PATTERN_WAVE, s),
            "WF_print_firefractor": _has(_RX_PRINT_FIREFRACTOR, s),
            "WF_print_pearl": _has(_RX_PRINT_PEARL, s),
            "WF_print_retro_logo_foil": _has(_RX_PRINT_RETRO_LOGO_FOIL, s),
            "WF_print_snackpack": _has(_RX_PRINT_SNACKPACK, s),
            "WF_print_speckle": _has(_RX_PRINT_SPECKLE, s),
            "WF_print_steel_metal": _has(_RX_PRINT_STEEL_METAL, s),
            "WF_print_superfractor": _has(_RX_PRINT_SUPERFRACTOR, s),
            "WF_print_xfractor": _has(_RX_PRINT_XFRACTOR, s),
            "WF_auto": _has(_RX_AUTO, s),
            "WF_cpa_sticker": _has(_RX_CPA_STICKER, s),
            "WF_rookie_of_the_year": _has(_RX_ROOKIE_OF_THE_YEAR, s),
            "WF_insert_hobby_stars": _has(_RX_INSERT_HOBBY_STARS, s),
            "WF_insert_scouts_top_100": _has(_RX_INSERT_SCOUTS_TOP_100, s),
            "WF_insert_top_100": _has(_RX_INSERT_TOP_100, s),
            "WF_insert_spotlights": _has(_RX_INSERT_SPOTLIGHTS, s),
            "WF_insert_roy_favorites": _has(_RX_INSERT_ROY_FAVORITES, s),
            "WF_insert_vip": _has(_RX_INSERT_VIP, s),
            "WF_insert_anime": _has(_RX_INSERT_ANIME, s),
            "WF_insert_greatness_loading": _has(_RX_INSERT_GREATNESS_LOADING, s),
            "WF_insert_rockstar_rookies": _has(_RX_INSERT_ROCKSTAR_ROOKIES, s),
            "WF_insert_crystalized": _has(_RX_INSERT_CRYSTALIZED, s),
            "WF_insert_etched_glass": _has(_RX_INSERT_ETCHED_GLASS, s),
            "WF_line_bowman_prospects": _has(_RX_LINE_BOWMAN_PROSPECTS, s),
            "WF_line_chrome_prospects": _has(_RX_LINE_CHROME_PROSPECTS, s),
            "WF_insert_adios": _has(_RX_INSERT_ADIOS, s),
            "WF_insert_ascensions": _has(_RX_INSERT_ASCENSIONS, s),
            "WF_insert_gpk": _has(_RX_INSERT_GPK, s),
            "WF_insert_it_came_to_the_league": _has(_RX_INSERT_IT_CAME_TO_THE_LEAGUE, s),
            "WF_insert_max_volume": _has(_RX_INSERT_MAX_VOLUME, s),
            "WF_insert_melt_mashers": _has(_RX_INSERT_MELT_MASHERS, s),
            "WF_insert_meteoric_rise": _has(_RX_INSERT_METEORIC_RISE, s),
        }
    )
    return out


def group_flags_for_word_flags(wf: Mapping[str, bool]) -> Dict[str, bool]:
    """
    Placeholder: all ``grp_*`` false. Define retail-specific combination rules here later
    (``wf`` is unused until then).
    """
    _ = wf
    return {k: False for k in GROUP_FLAG_KEYS}


def word_and_group_flags_for_title(
    title: str, checklist_slot: Optional[int] = None
) -> tuple[Dict[str, bool], Dict[str, bool]]:
    wf = word_flags_for_title(title, checklist_slot)
    return wf, group_flags_for_word_flags(wf)


def wf_grp_as_flat_str_dict(wf: Mapping[str, bool], grp: Mapping[str, bool]) -> Dict[str, str]:
    """``1`` / ``0`` strings for CSV export (all ``WF_*`` then all ``grp_*``)."""
    out: Dict[str, str] = {}
    for k in WF_FLAG_KEYS:
        out[k] = "1" if wf.get(k, False) else "0"
    for k in GROUP_FLAG_KEYS:
        out[k] = "1" if grp.get(k, False) else "0"
    return out
