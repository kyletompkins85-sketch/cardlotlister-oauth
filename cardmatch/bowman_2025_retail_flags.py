# Cmd+F: GH_ANCHOR_BOWMAN_2025_RETAIL_FLAGS_A1B2C3D4
"""
2025 Bowman **retail** listing word flags (``WF_*``) and group placeholders (``grp_*``).

**Source of truth:** ``docs/classification/2025_bowman_classifier_notes.md`` only — exclusions,
paper vs chrome clues, the card vs modifiers mental model, and insert **names** from the set
distinction section. This module does **not** mirror Bowman Draft (``z10_bowman_listing_classifier``)
parallel taxonomy or old CT-style groupings.

``grp_*`` keys exist as **reserved slots** (all false) until retail-specific combination rules
are defined; they are not copied from Draft.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, Mapping, Sequence

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


def word_flags_for_title(title: str) -> Dict[str, bool]:
    """Return every ``WF_*`` flag for ``title`` (NFKC-normalized)."""
    s = _norm_title(title)
    out: Dict[str, bool] = {k: False for k in WF_FLAG_KEYS}
    if not s:
        return out

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


def word_and_group_flags_for_title(title: str) -> tuple[Dict[str, bool], Dict[str, bool]]:
    wf = word_flags_for_title(title)
    return wf, group_flags_for_word_flags(wf)


def wf_grp_as_flat_str_dict(wf: Mapping[str, bool], grp: Mapping[str, bool]) -> Dict[str, str]:
    """``1`` / ``0`` strings for CSV export (all ``WF_*`` then all ``grp_*``)."""
    out: Dict[str, str] = {}
    for k in WF_FLAG_KEYS:
        out[k] = "1" if wf.get(k, False) else "0"
    for k in GROUP_FLAG_KEYS:
        out[k] = "1" if grp.get(k, False) else "0"
    return out
