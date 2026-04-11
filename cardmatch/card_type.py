"""Primary card-type label per scored row + listing count reports."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cardmatch.player_index import load_bdc_player_rank
from cardmatch.taxonomy import (
    _bdc_parallel_detail,
    _bdc_parallel_detail_from_serial_denominator,
    _flags_with_bdc_card_token,
    _RE_SPECKLE_REFRACTOR,
    _RE_SPARKLE_REFRACTOR,
    _RE_X_FRACTOR_PHRASE,
    _should_apply_chrome_bdc_parallel_taxonomy,
    BDC_PRIMARY_FAMILY,
    build_composite_card_type,
    finalize_bdc_composite_string,
    flags_for_title,
    format_axis_card_type,
)

# Listing-count aggregates (`listing_counts_*.csv`): omit these primary labels (still used elsewhere).
LISTING_COUNT_EXCLUDED_CARD_TYPES = frozenset(
    {
        "Lot / multi-card",
        "Pick / set builder",
        "Graded",
        "Complete set",
        "Presale",
    }
)


def _strip_trailing_auto_suffixes(ct: str) -> str:
    """Remove trailing ' · Auto' segments so Lot/Graded/etc. match excluded buckets when autos are present."""
    out = ct
    while out.endswith(" · Auto"):
        out = out[: -len(" · Auto")]
    return out


def _card_group_from_type(ct: str) -> str:
    """First segment of card_type (product family), e.g. Chrome · Green /99 → Chrome."""
    if " · " in ct:
        return ct.split(" · ", 1)[0]
    return ct


def _card_type_has_auto_suffix(ct: str) -> bool:
    """True when the label includes a trailing **· Auto** (possibly stacked)."""
    return _strip_trailing_auto_suffixes(ct) != ct


def _listing_counts_by_card_type_sort_key(item: Tuple[str, int]) -> Tuple[Any, ...]:
    """
    Sort: card group (A–Z), then non-auto before auto, then listing count descending
    (parallel / color lines order by volume within each bucket).
    """
    ct, n = item
    return (
        _card_group_from_type(ct).lower(),
        1 if _card_type_has_auto_suffix(ct) else 0,
        -n,
    )


def row_excluded_from_listing_counts(row: Dict[str, Any], ct: Optional[str] = None) -> bool:
    """
    Skip aggregate listing-count rows for lot/pick/graded/complete-set/presale even when the
    primary label includes autographs (e.g. Lot / multi-card · Auto). Uses classifier flags first,
    then exact or auto-stripped label match.
    """
    flags = _flags_for_row(row)
    if (
        flags.get("WF_lot")
        or flags.get("WF_complete_set")
        or flags.get("WF_pick")
        or flags.get("WF_set_builder")
    ):
        return True
    if flags.get("WF_presale"):
        return True
    if row_is_graded_listing(row, flags):
        return True
    primary = ct if ct is not None else row_primary_card_type(row)
    if primary in LISTING_COUNT_EXCLUDED_CARD_TYPES:
        return True
    base = _strip_trailing_auto_suffixes(primary)
    if base in LISTING_COUNT_EXCLUDED_CARD_TYPES:
        return True
    return False


def _flags_for_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Classifier flags + synthetic `WF_bdc` when `#BDC-…` appears but the classifier missed it."""
    title = row.get("title") or ""
    return _flags_with_bdc_card_token(title, flags_for_title(title))


# Human labels for nb_* reason codes (most specific parallel / product wins when chosen as primary).
# Avoid bare finish/color/serial tokens as the full card type — prefix with product line where possible.
_NB_LABEL: Dict[str, str] = {
    "nb_graded": "Graded",
    "nb_orange_border": f"{BDC_PRIMARY_FAMILY} · Orange /25",
    "nb_sky_blue": f"{BDC_PRIMARY_FAMILY} · Sky Blue",
    "nb_snack_pack": "Snack-Pack",
    "nb_mini_diamond": f"{BDC_PRIMARY_FAMILY} · Mini Diamond",
    "nb_aqua": f"{BDC_PRIMARY_FAMILY} · Aqua",
    "nb_sparkle": f"{BDC_PRIMARY_FAMILY} · Sparkle",
    "nb_blue_geometric": f"{BDC_PRIMARY_FAMILY} · Blue Geometric",
    "nb_chrome": BDC_PRIMARY_FAMILY,
    "nb_lot": "Lot / multi-card",
    "nb_pick_or_set_builder": "Pick / set builder",
    "nb_complete_set": "Complete set",
    "nb_presale": "Presale",
    "nb_chrome_prospect_autographs": f"{BDC_PRIMARY_FAMILY} · Auto",
    "nb_prized_prospect": "Prized Prospect",
    "nb_axis": "axis plain",
    "nb_draft_night": "Draft Night",
    "nb_final_draft": "Final Draft",
    "nb_bdc": BDC_PRIMARY_FAMILY,
    "nb_bowman_in_action": "Bowman In Action",
    "nb_image_variation": "Image Variations",
    "nb_college_variation": "College Variation",
    "nb_bowman_spotlight": "Bowman Spotlight",
    "nb_etched_in_glass": "Etched in Glass",
    "nb_sapphire": "Sapphire",
    "nb_crystallized": "Crystallized",
    "nb_x_fractor": f"{BDC_PRIMARY_FAMILY} · X-Fractor",
    "nb_refractor": f"{BDC_PRIMARY_FAMILY} · Refractor",
    "nb_superfractor": f"{BDC_PRIMARY_FAMILY} · Superfractor",
    "nb_shimmer": f"{BDC_PRIMARY_FAMILY} · Shimmer Refractor",
    "nb_speckle": f"{BDC_PRIMARY_FAMILY} · Speckle Refractor",
    "nb_wave": f"{BDC_PRIMARY_FAMILY} · Wave",
    "nb_lava": f"{BDC_PRIMARY_FAMILY} · Lava",
    "nb_printing_plate": f"{BDC_PRIMARY_FAMILY} · Printing Plate",
    "nb_numbered_serial": f"{BDC_PRIMARY_FAMILY} · Parallel",
}


def _is_bdc_chrome_primary_base(base: str) -> bool:
    """True for canonical **Chrome · …** / **Chrome /…** BDC labels (not **Chrome Prospect College Variations**)."""
    if base.startswith("Chrome Prospect College Variations"):
        return False
    return base == BDC_PRIMARY_FAMILY or base.startswith(f"{BDC_PRIMARY_FAMILY} · ") or base.startswith(
        f"{BDC_PRIMARY_FAMILY} /"
    )


# Axis insert sub-types (mutually exclusive; WF_axis must already be true).
_RE_AXIS_GREEN = re.compile(r"\bgreen\b", re.I)
_RE_AXIS_GOLD = re.compile(r"\bgold\b", re.I)
_RE_AXIS_ORANGE = re.compile(r"\borange\b", re.I)
_RE_AXIS_BLACK = re.compile(r"\bblack\b", re.I)
_RE_AXIS_RED = re.compile(r"\bred\b", re.I)

_RE_ETCHED_IN_GLASS = re.compile(r"\betched\s+in\s+glass\b", re.I)
_RE_IMAGE_VARIATION = re.compile(r"\bimage\s+variation\b", re.I)
# X-Fractor even when BDC / chrome parallel path does not run (e.g. missing WF_bdc in title).
# Last-resort base stock when no product line matches: title word *chrome* → BDC base, else paper.
_RE_CHROME_WORD = re.compile(r"\bchrome\b", re.I)


def _fallback_base_or_paper_title(row: Dict[str, Any]) -> str:
    """Former legacy **Other**: infer stock from title only."""
    title = row.get("title") or ""
    if _RE_CHROME_WORD.search(title):
        return finalize_bdc_composite_string(f"{BDC_PRIMARY_FAMILY} · Base")
    return "Base-Paper"


def _recovered_print_run_denominator(title: str, serial_out_of: int) -> Optional[int]:
    """
    Classifier sometimes sets `serial_out_of` to a year (e.g. 2025) from titles like `/250/2025 Bowman`.
    Recover the real print run from slash patterns when the parsed value is year-shaped.
    """
    if serial_out_of not in range(2000, 2031):
        return None
    t = title or ""
    for denom in (250, 199, 150, 125, 100, 99, 75, 73, 50, 35, 25, 15, 10, 5):
        if re.search(rf"(?:#)?/\s*{denom}\b|/\s*{denom}\s*/", t, re.I):
            return denom
    return None


def _coerce_nb_numbered_serial_to_colored_parallel(row: Dict[str, Any]) -> str:
    """
    `nb_numbered_serial` is a generic pilot bucket; prefer a concrete colored refractor label
    when denominator or title+flags support the same logic as composite (non-auto ladder).
    """
    flags = _flags_for_row(row)
    so = flags.get("serial_out_of")
    if so is not None:
        try:
            n = int(so)
            d = _bdc_parallel_detail_from_serial_denominator(n)
            if not d:
                rec = _recovered_print_run_denominator(row.get("title") or "", n)
                if rec is not None:
                    d = _bdc_parallel_detail_from_serial_denominator(rec)
            if d:
                return finalize_bdc_composite_string(f"{BDC_PRIMARY_FAMILY} · {d}")
        except (TypeError, ValueError):
            pass
    if _should_apply_chrome_bdc_parallel_taxonomy(row, flags):
        detail = _bdc_parallel_detail(row, flags)
        if detail:
            return finalize_bdc_composite_string(f"{BDC_PRIMARY_FAMILY} · {detail}")
    tl = (row.get("title") or "").lower()
    if "refractor" in tl and not flags.get("WF_refractor"):
        f2 = _flags_with_bdc_card_token(
            row.get("title") or "",
            {**flags, "WF_refractor": True},
        )
        if _should_apply_chrome_bdc_parallel_taxonomy(row, f2):
            detail = _bdc_parallel_detail(row, f2)
            if detail:
                return finalize_bdc_composite_string(f"{BDC_PRIMARY_FAMILY} · {detail}")
    return f"{BDC_PRIMARY_FAMILY} · Parallel"


def _coerce_bare_bdc_product_line_to_base_or_paper(row: Dict[str, Any], ct: str) -> str:
    """
    Bare **Chrome** (no **· Base**, **· Refractor**, etc.) must never be a final label:
    same rule as legacy **Other** — *chrome* in title → **Chrome · Base**, else **Base-Paper**.
    Covers composite paths with no parallel slice, **nb_bdc** / **nb_chrome**, and CPA non-auto.
    """
    if ct == BDC_PRIMARY_FAMILY:
        return _fallback_base_or_paper_title(row)
    return ct


def _orange_border_bdc_card_type(flags: Dict[str, Any]) -> str:
    """
    Orange-border listings are chrome prospect orange parallels (/25), not a separate paper-base bucket.
    """
    parts = f"{BDC_PRIMARY_FAMILY} · Orange /25"
    if flags.get("WF_auto"):
        parts = f"{parts} · Auto"
    return finalize_bdc_composite_string(parts)


def _legacy_from_title_flags(row: Dict[str, Any], flags: Dict[str, Any]) -> Optional[str]:
    """Product line from classifier/title only (no pilot_reason_codes nb_*). Used before nb chain and for auto-only fallback."""
    title = row.get("title") or ""
    if flags.get("WF_college_variation"):
        return None
    if flags.get("WF_chrome_prospect_autographs"):
        return f"{BDC_PRIMARY_FAMILY} · Auto" if flags.get("WF_auto") else BDC_PRIMARY_FAMILY
    if flags.get("WF_bowman_spotlight"):
        return "Bowman Spotlight"
    if flags.get("WF_final_draft"):
        return "Final Draft"
    if _RE_ETCHED_IN_GLASS.search(title):
        return "Etched in Glass"
    if _RE_IMAGE_VARIATION.search(title):
        return "Image Variations"
    if _RE_X_FRACTOR_PHRASE.search(title) or flags.get("WF_x_fractor"):
        return f"{BDC_PRIMARY_FAMILY} · X-Fractor"
    if _RE_SPECKLE_REFRACTOR.search(title.lower()):
        return f"{BDC_PRIMARY_FAMILY} · Speckle Refractor"
    if _RE_SPARKLE_REFRACTOR.search(title.lower()):
        return f"{BDC_PRIMARY_FAMILY} · Sparkle"
    chrome_parallel = _chrome_bdc_parallel_primary_type(row, flags)
    if chrome_parallel is not None:
        return chrome_parallel
    return None


def _augment_label_with_auto(
    base: str, row: Dict[str, Any], flags: Dict[str, Any], want_auto: bool
) -> str:
    """When nb_auto / WF_auto is set, attach Auto to the product line (Axis uses full axis formatter)."""
    if not want_auto:
        if base.startswith("Chrome Prospect College Variations") or _is_bdc_chrome_primary_base(base):
            return finalize_bdc_composite_string(base)
        return base
    if flags.get("WF_axis"):
        return format_axis_card_type(row)
    if base.startswith("axis ") or base == "axis plain":
        return format_axis_card_type(row)
    if base.startswith("Chrome Prospect College Variations"):
        if " · Auto" in base:
            return finalize_bdc_composite_string(base)
        return finalize_bdc_composite_string(f"{base} · Auto")
    if _is_bdc_chrome_primary_base(base):
        if " · Auto" in base:
            return finalize_bdc_composite_string(base)
        return finalize_bdc_composite_string(f"{base} · Auto")
    if " · Auto" not in base:
        return f"{base} · Auto"
    return base


def _resolve_autograph_only_nb(row: Dict[str, Any], flags: Dict[str, Any]) -> Optional[str]:
    """pilot_reason_codes only nb_auto: resolve product from title flags (same signals as composite)."""
    if flags.get("WF_college_variation"):
        from cardmatch.taxonomy import build_composite_card_type

        c = build_composite_card_type(row)
        if c:
            return finalize_bdc_composite_string(c)
        return finalize_bdc_composite_string(
            _augment_label_with_auto("Chrome Prospect College Variations", row, flags, True)
        )
    p = _legacy_from_title_flags(row, flags)
    if p is not None:
        return _augment_label_with_auto(p, row, flags, True)
    if flags.get("WF_bdc") or flags.get("WF_chrome") or flags.get("WF_refractor"):
        return finalize_bdc_composite_string(f"{BDC_PRIMARY_FAMILY} · Auto")
    return None


def _chrome_bdc_parallel_primary_type(row: Dict[str, Any], flags: Dict[str, Any]) -> Optional[str]:
    """
    Same strings as composite BDC line (when composite is skipped e.g. lot/presale rows).
    """
    if not _should_apply_chrome_bdc_parallel_taxonomy(row, flags):
        return None
    detail = _bdc_parallel_detail(row, flags)
    if not detail:
        return None
    return f"{BDC_PRIMARY_FAMILY} · {detail}"


def _axis_card_type_label(row: Dict[str, Any]) -> str:
    """
    Bowman Axis line: Base vs Parallel (legacy string axis parallel), mini-diamond, superfractor, /99 colors.
    Uses classifier flags on the listing title (same source as pilot_is_axis).
    """
    title = row.get("title") or ""
    flags = flags_for_title(title)
    if not flags.get("WF_axis"):
        return "axis plain"

    if flags.get("WF_superfractor"):
        return "axis superfractor"
    if flags.get("WF_mini_diamond"):
        return "axis mini-diamond"

    # Bowman Chrome: green parallel is typically /99; gold is typically /50 (titles often omit "Gold").
    so = flags.get("serial_out_of")
    if so == 99:
        return "axis green"
    if so == 50:
        return "axis gold"

    s = title.lower()
    if _RE_AXIS_GREEN.search(s):
        return "axis green"
    if _RE_AXIS_GOLD.search(s):
        return "axis gold"
    if _RE_AXIS_ORANGE.search(s):
        return "axis orange"
    if _RE_AXIS_BLACK.search(s):
        return "axis black"
    if _RE_AXIS_RED.search(s):
        return "axis red"

    if flags.get("WF_refractor") or flags.get("WF_x_fractor"):
        return "axis parallel"
    return "axis plain"


def parse_axis_insert_number(title: str) -> int:
    """Axis insert checklist number from title (#A-12 or A-12); large sentinel if missing."""
    t = title or ""
    m = re.search(r"#\s*A-(\d+)", t, re.I) or re.search(r"\bA-(\d+)\b", t, re.I)
    if m:
        return int(m.group(1))
    return 999999


def format_axis_type_for_review(axis_type: str) -> str:
    """Title-case for review CSV (e.g. axis mini-diamond → Axis Mini-Diamond)."""
    if not axis_type.startswith("axis"):
        return axis_type
    out: List[str] = []
    for part in axis_type.split():
        if part.lower() == "mini-diamond":
            out.append("Mini-Diamond")
        else:
            out.append(part.capitalize())
    return " ".join(out)


def display_card_type_for_review(row: Dict[str, Any]) -> str:
    """Review CSV `card_type` column: primary taxonomy, Axis subtypes title-cased."""
    ct = row_primary_card_type(row)
    if ct.startswith("axis"):
        return format_axis_type_for_review(ct)
    return ct


def row_is_graded_listing(row: Dict[str, Any], flags: Optional[Dict[str, Any]] = None) -> bool:
    """
    PSA / BGS / SGC / CGC / explicit graded (WF_graded). Uses `pilot_is_graded` when present;
    otherwise classifier flags on title (for CSV rows scored before graded column existed).
    """
    pg = row.get("pilot_is_graded")
    if pg == "1":
        return True
    if pg == "0":
        return False
    if flags is None:
        flags = _flags_for_row(row)
    return bool(flags.get("WF_graded"))


def _parse_reason_codes(row: Dict[str, Any]) -> List[str]:
    raw = row.get("pilot_reason_codes")
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    s = str(raw).strip()
    if not s:
        return []
    try:
        out = json.loads(s)
        if isinstance(out, list):
            return [str(x) for x in out]
    except json.JSONDecodeError:
        pass
    return []


def row_primary_card_type(row: Dict[str, Any]) -> str:
    """
    Composite card type: product group · stock · color · finish · Auto (when applicable).
    Falls back to legacy nb_* / BDC string labels when taxonomy does not apply.
    """
    if (row.get("pilot_is_snack_pack") or "") == "1":
        return "Snack-Pack"
    if (row.get("pilot_is_axis") or "") == "1":
        return format_axis_card_type(row)

    flags = _flags_for_row(row)
    if flags.get("WF_snack_pack"):
        return "Snack-Pack"
    if (row.get("pilot_is_orange_border") or "") == "1" or flags.get("WF_orange_border"):
        return _orange_border_bdc_card_type(flags)

    if row_is_graded_listing(row, flags):
        return "Graded"

    if flags.get("WF_lot"):
        return "Lot / multi-card"
    if flags.get("WF_pick") or flags.get("WF_set_builder"):
        return "Pick / set builder"
    if flags.get("WF_complete_set"):
        return "Complete set"
    if flags.get("WF_presale"):
        return "Presale"

    if (row.get("pilot_is_likely_chrome_base") or "") == "1":
        return finalize_bdc_composite_string(f"{BDC_PRIMARY_FAMILY} · Base")
    if (row.get("pilot_is_likely_base") or "") == "1":
        codes_lb = _parse_reason_codes(row)
        nb_lb = [c for c in codes_lb if isinstance(c, str) and c.startswith("nb_")]
        want_auto_lb = bool(flags.get("WF_auto")) or ("nb_auto" in nb_lb)
        if want_auto_lb:
            return finalize_bdc_composite_string(f"{BDC_PRIMARY_FAMILY} · Auto")
        return "Base-Paper"

    composite = build_composite_card_type(row)
    if composite:
        return _coerce_bare_bdc_product_line_to_base_or_paper(
            row, finalize_bdc_composite_string(composite)
        )

    return _coerce_bare_bdc_product_line_to_base_or_paper(
        row, finalize_bdc_composite_string(legacy_primary_card_type(row))
    )


def _legacy_primary_card_type_impl(row: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Returns (label, used_fallback: bool). Fallback is the former **Other** path:
    no nb_* / title product line — infer **Chrome · Base** if *chrome* in title else **Base-Paper**.
    """
    if (row.get("pilot_is_snack_pack") or "") == "1":
        return ("Snack-Pack", False)
    if (row.get("pilot_is_axis") or "") == "1":
        return (_axis_card_type_label(row), False)

    flags = _flags_for_row(row)
    if flags.get("WF_snack_pack"):
        return ("Snack-Pack", False)
    if (row.get("pilot_is_orange_border") or "") == "1" or flags.get("WF_orange_border"):
        return (_orange_border_bdc_card_type(flags), False)

    if row_is_graded_listing(row, flags):
        return ("Graded", False)

    if flags.get("WF_lot"):
        return ("Lot / multi-card", False)
    if flags.get("WF_pick") or flags.get("WF_set_builder"):
        return ("Pick / set builder", False)
    if flags.get("WF_complete_set"):
        return ("Complete set", False)
    if flags.get("WF_presale"):
        return ("Presale", False)

    if (row.get("pilot_is_likely_chrome_base") or "") == "1":
        return (finalize_bdc_composite_string(f"{BDC_PRIMARY_FAMILY} · Base"), False)
    if (row.get("pilot_is_likely_base") or "") == "1":
        codes_lb = _parse_reason_codes(row)
        nb_lb = [c for c in codes_lb if isinstance(c, str) and c.startswith("nb_")]
        want_auto_lb = bool(flags.get("WF_auto")) or ("nb_auto" in nb_lb)
        if want_auto_lb:
            return (finalize_bdc_composite_string(f"{BDC_PRIMARY_FAMILY} · Auto"), False)
        return ("Base-Paper", False)

    codes = _parse_reason_codes(row)
    nb_codes = [c for c in codes if isinstance(c, str) and c.startswith("nb_")]
    want_auto = bool(flags.get("WF_auto")) or ("nb_auto" in nb_codes)
    product_codes = [c for c in nb_codes if c != "nb_auto"]

    p = _legacy_from_title_flags(row, flags)
    if p is not None:
        return (_augment_label_with_auto(p, row, flags, want_auto), False)

    if product_codes:
        last = product_codes[-1]
        base = _NB_LABEL.get(last, last.replace("nb_", "").replace("_", " ").title())
        if last == "nb_numbered_serial":
            base = _coerce_nb_numbered_serial_to_colored_parallel(row)
        return (_augment_label_with_auto(base, row, flags, want_auto), False)

    if want_auto:
        r = _resolve_autograph_only_nb(row, flags)
        if r is not None:
            return (r, False)
        # Autographs must not fall through to plain **Base-Paper** when the title omits *chrome*
        # (e.g. "1st Auto" only). Default to on-card Chrome prospect autographs for Bowman Draft.
        return (finalize_bdc_composite_string(f"{BDC_PRIMARY_FAMILY} · Auto"), False)
    return (_fallback_base_or_paper_title(row), True)


def legacy_primary_card_type(row: Dict[str, Any]) -> str:
    """
    Pre-taxonomy primary label chain (nb_* last wins + BDC parallel strings).
    Used when `build_composite_card_type` returns None. Review exports and focus use
    `row_primary_card_type` (composite + this fallback) as the canonical card type.
    """
    label, _ = _legacy_primary_card_type_impl(row)
    return label


def row_primary_card_type_used_legacy_other_fallback(row: Dict[str, Any]) -> bool:
    """
    True when `row_primary_card_type` used the legacy chrome-vs-paper default (ex-composite **Other**).
    Used for **`classification_focus: other`** in `review_targets.json`.
    """
    if (row.get("pilot_is_snack_pack") or "") == "1":
        return False
    if (row.get("pilot_is_axis") or "") == "1":
        return False
    flags = _flags_for_row(row)
    if (row.get("pilot_is_orange_border") or "") == "1" or flags.get("WF_orange_border"):
        return False
    if row_is_graded_listing(row, flags):
        return False
    if flags.get("WF_lot"):
        return False
    if flags.get("WF_pick") or flags.get("WF_set_builder"):
        return False
    if flags.get("WF_complete_set"):
        return False
    if flags.get("WF_presale"):
        return False
    if (row.get("pilot_is_likely_chrome_base") or "") == "1":
        return False
    if (row.get("pilot_is_likely_base") or "") == "1":
        return False
    if build_composite_card_type(row):
        return False
    return _legacy_primary_card_type_impl(row)[1]


def write_listing_count_reports(
    rows: List[Dict[str, Any]], out_dir: Path
) -> Tuple[Path, Path, Counter[str]]:
    """
    Write listing_counts_by_card_type.csv and listing_counts_by_player_and_card_type.csv.
    Rows excluded via `row_excluded_from_listing_counts` (lot/pick/graded/complete-set/presale,
    including `… · Auto` variants) are skipped.

    **listing_counts_by_card_type.csv** sort order: **card group** (first ` · ` segment, A–Z),
    then **non-auto** rows before **· Auto** rows, then **listing_count** descending within
    each of those buckets.
    Returns (by_type_path, by_player_type_path, counts_by_card_type).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    by_type: Counter[str] = Counter()
    by_player_type: Counter[Tuple[str, str]] = Counter()

    for r in rows:
        ct = row_primary_card_type(r)
        if row_excluded_from_listing_counts(r, ct):
            continue
        by_type[ct] += 1
        player = (r.get("pilot_player_guess") or "").strip()
        if not player:
            player = "(unknown player)"
        by_player_type[(player, ct)] += 1

    type_path = out_dir / "listing_counts_by_card_type.csv"
    with type_path.open("w", encoding="utf-8", newline="") as fw:
        w = csv.DictWriter(fw, fieldnames=["card_type", "listing_count"])
        w.writeheader()
        for ct, n in sorted(by_type.items(), key=_listing_counts_by_card_type_sort_key):
            w.writerow({"card_type": ct, "listing_count": n})

    pt_path = out_dir / "listing_counts_by_player_and_card_type.csv"
    with pt_path.open("w", encoding="utf-8", newline="") as fw:
        w = csv.DictWriter(fw, fieldnames=["player", "card_type", "listing_count"])
        w.writeheader()
        for (player, ct), n in sorted(
            by_player_type.items(),
            key=lambda x: (
                x[0][0].lower(),
                _card_group_from_type(x[0][1]).lower(),
                -x[1],
            ),
        ):
            w.writerow({"player": player, "card_type": ct, "listing_count": n})

    return type_path, pt_path, by_type


def write_listing_counts_by_player_bdc_order(
    rows: List[Dict[str, Any]],
    out_dir: Path,
    checklist: Path,
    *,
    bdc_cap: int = 200,
) -> Path:
    """
    Write listing_counts_by_player_bdc_order.csv: total listing counts per player (same exclusions
    as `write_listing_count_reports`), sorted by **BDC chrome checklist number** (BDC-1 … BDC-N),
    then players not on the BDC map (e.g. unknown / name mismatch) last, A–Z within each bucket.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    bdc_cap = max(1, min(int(bdc_cap), 500))
    by_player: Counter[str] = Counter()
    for r in rows:
        ct = row_primary_card_type(r)
        if row_excluded_from_listing_counts(r, ct):
            continue
        player = (r.get("pilot_player_guess") or "").strip()
        if not player:
            player = "(unknown player)"
        by_player[player] += 1

    rank_map = load_bdc_player_rank(checklist, bdc_cap)
    sentinel = 1_000_000
    ordered: List[Tuple[int, str, str, int]] = []
    for player, n in by_player.items():
        br = rank_map.get(player)
        if br is None:
            ordered.append((sentinel, player, "", n))
        else:
            ordered.append((br, player, str(br), n))
    ordered.sort(key=lambda x: (x[0], x[1].lower()))

    path = out_dir / "listing_counts_by_player_bdc_order.csv"
    with path.open("w", encoding="utf-8", newline="") as fw:
        w = csv.DictWriter(fw, fieldnames=["bdc_rank", "player", "listing_count"])
        w.writeheader()
        for _sort_key, player, br_str, n in ordered:
            w.writerow({"bdc_rank": br_str, "player": player, "listing_count": n})
    return path
