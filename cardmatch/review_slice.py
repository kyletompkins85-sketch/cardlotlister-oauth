from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from cardmatch.card_type import row_primary_card_type, row_primary_card_type_used_legacy_other_fallback
from cardmatch.taxonomy import flags_for_title

_BD_NUM = re.compile(r"^BD-(\d+)$", re.IGNORECASE)
_BDC_NUM = re.compile(r"^BDC-(\d+)$", re.IGNORECASE)

# `classification_focus: refractor` — extras that are refractor-family but not BDC-prefixed.
_REFRACTOR_FOCUS_EXTRA_TYPES = frozenset(
    {
        "Etched in Glass",
        "Image Variations",
        "BDC Chrome Prospect · Aqua /125",
    }
)

def _canonical_refractor_and_chrome_plain(row: Dict[str, Any]) -> bool:
    """
    `refractor_and_chrome_plain` focus: match on canonical `row_primary_card_type` plus
    Chrome Prospect Autograph inserts (merged into **BDC Chrome Prospect · …** strings).

    Includes plain BDC refractor / serial-ish parallel / CPA (WF_chrome_prospect_autographs) / college
    (including legacy-only **College Variation**); excludes colored BDC parallels (e.g. BDC · Green)
    to match historical focus scope.
    """
    primary = row_primary_card_type(row)
    if primary in ("College Variation",):
        return True
    if primary in ("BDC Chrome Prospect · Refractor", "BDC Chrome Prospect · Parallel"):
        return True
    if primary.startswith("Chrome Prospect College Variations"):
        return True
    flags = flags_for_title(row.get("title") or "")
    if flags.get("WF_chrome_prospect_autographs"):
        return True
    return False


def load_review_player_keys(checklist_csv: Path, card_numbers: List[str]) -> Set[str]:
    want = set(card_numbers)
    out: Set[str] = set()
    with checklist_csv.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            cn = (row.get("card_number") or "").strip()
            if cn not in want:
                continue
            raw = (row.get("player_name_raw") or "").strip().rstrip(",").strip()
            if raw:
                out.add(raw)
    return out


def load_player_card_rank(checklist_csv: Path, card_numbers: List[str]) -> Dict[str, int]:
    """
    Map checklist player display name -> numeric card order (BD-1 -> 1, BD-10 -> 10) for sorting.
    """
    want = set(card_numbers)
    out: Dict[str, int] = {}
    with checklist_csv.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            cn = (row.get("card_number") or "").strip()
            if cn not in want:
                continue
            m = _BD_NUM.match(cn.strip())
            rank = int(m.group(1)) if m else 999999
            raw = (row.get("player_name_raw") or "").strip().rstrip(",").strip()
            if raw and raw not in out:
                out[raw] = rank
    return out


def load_bdc_player_rank(checklist_csv: Path, max_num: int = 200) -> Dict[str, int]:
    """
    Map checklist player display name -> BDC chrome number (BDC-1 -> 1 … BDC-200 -> 200) for sorting.
    Uses rows whose `card_number` matches **BDC-*** in the normalized checklist (Base Set - Chrome).
    """
    out: Dict[str, int] = {}
    with checklist_csv.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            cn = (row.get("card_number") or "").strip()
            m = _BDC_NUM.match(cn)
            if not m:
                continue
            rank = int(m.group(1))
            if rank < 1 or rank > max_num:
                continue
            raw = (row.get("player_name_raw") or "").strip().rstrip(",").strip()
            if raw and raw not in out:
                out[raw] = rank
    return out


def load_review_config(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def row_in_review_slice(player_guess: str, review_players: Set[str]) -> bool:
    if not player_guess:
        return False
    return player_guess in review_players


def row_matches_classification_focus(
    row: Dict[str, Any],
    focus: str,
    *,
    review_config: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Whether a scored row matches the current review focus (one product class per pass).

    * axis — Bowman Axis insert (pilot_is_axis == 1; title matches WF_axis in classifier).
    * base — BDC chrome prospect base only (pilot_is_likely_chrome_base == 1).
    * paper_base — paper BD-* base only (pilot_is_likely_base == 1).
    * refractor — primary card type is generic **Refractor** or **axis refractor** (not superfractor / other parallels).
    * chrome_refractor_plain — primary type exactly **BDC Chrome Prospect · Refractor** (no **· Auto**).
    * bdc_chrome_prospect_parallel — primary type exactly **BDC Chrome Prospect · Parallel** (still unresolved after serial/color inference for `nb_numbered_serial`).
    * refractor_and_chrome_plain — canonical primary (`row_primary_card_type`): **BDC Chrome Prospect · Refractor**,
      **BDC Chrome Prospect · Parallel**, CPA line (**BDC Chrome Prospect · …** with WF_chrome_prospect_autographs),
      **Chrome Prospect College Variations …**, legacy **College Variation** (not colored BDC parallels).
    * bdc_chrome_prospect_auto — canonical primary is exactly **BDC Chrome Prospect · Auto** (CPA base auto only; no parallel/colored + Auto).
    * bdc_chrome_prospect — canonical primary is exactly **BDC Chrome Prospect** (bare product line; no parallel/base/auto suffix).
    * other — rows that used the legacy default after taxonomy: **BDC Chrome Prospect · Base** if *chrome* in title else **Base-Paper** (ex-composite **Other** bucket; see `row_primary_card_type_used_legacy_other_fallback`).
    * primary_exact — canonical `row_primary_card_type` equals **`primary_card_type_exact`** in `review_targets.json` (any single primary string).
    """
    f = (focus or "").strip().lower()
    if f == "primary_exact":
        rc = review_config or {}
        want = (rc.get("primary_card_type_exact") or "").strip()
        if not want:
            return False
        return row_primary_card_type(row) == want
    if f == "axis":
        return (row.get("pilot_is_axis") or "") == "1"
    if f == "base":
        return (row.get("pilot_is_likely_chrome_base") or "") == "1"
    if f == "paper_base":
        return (row.get("pilot_is_likely_base") or "") == "1"
    if f == "refractor":
        p = row_primary_card_type(row)
        if p == "BDC Chrome Prospect · Base":
            return False
        if p in _REFRACTOR_FOCUS_EXTRA_TYPES:
            return True
        if p.startswith("Image Variations") or p.startswith("Etched in Glass"):
            return True
        if p.startswith("BDC Chrome Prospect ·"):
            return True
        if p.startswith("Bowman Axis"):
            return p != "Bowman Axis · Base"
        return False
    if f == "chrome_refractor_plain":
        return row_primary_card_type(row) == "BDC Chrome Prospect · Refractor"
    if f == "bdc_chrome_prospect_parallel":
        return row_primary_card_type(row) == "BDC Chrome Prospect · Parallel"
    if f == "refractor_and_chrome_plain":
        return _canonical_refractor_and_chrome_plain(row)
    if f == "bdc_chrome_prospect_auto":
        return row_primary_card_type(row) == "BDC Chrome Prospect · Auto"
    if f == "bdc_chrome_prospect":
        return row_primary_card_type(row) == "BDC Chrome Prospect"
    if f == "other":
        return row_primary_card_type_used_legacy_other_fallback(row)
    return False
