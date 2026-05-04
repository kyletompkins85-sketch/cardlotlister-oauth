"""
2025 Bowman retail: canonical ``card_type`` resolution, UI ``display_name`` map, combo CSV index,
and sort keys shared by ``build_2025_bowman_retail_card_type_serial_combos_observed.py`` and the
retail deals API.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Mapping, Optional

# Keys are ``card_type_display`` (lookup short code).
DISPLAY_NAME_BY_CARD_TYPE_DISPLAY: Dict[str, str] = {
    "BA": "Anime",
    "BA-K": "Anime Kanji",
    "Base": "Paper",
    "BCP": "Chrome",
    "BP": "Paper",
    "BPA": "Paper Auto",
    "PRV": "Paper Auto",
    "BTP": "Top 100",
    "CPA": "Chrome Auto",
    "CRA": "Chrome Auto",
    "BWC": "Crystalized",
    "GL": "Greatness Loading",
    "HS": "Hobby Stars",
    "HSA": "Hobby Stars Auto",
    "CPR": "Retrofractor Auto",
    "Retro": "Retrofractors",
    "RR": "Rockstar Rookies",
    "RRA": "Rockstar Rookies Auto",
    "ROY": "ROY",
    "ROY-A": "ROY Auto",
    "VIP": "VIP",
    "VIP-A": "VIP Auto",
}


def load_card_type_lookup_maps(lookup_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """``card_type`` -> ``card_type_display``, and reverse ``card_type_display`` -> ``card_type``."""
    ct_to_disp: dict[str, str] = {}
    disp_to_ct: dict[str, str] = {}
    with lookup_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ct = (row.get("card_type") or "").strip()
            d = (row.get("card_type_display") or "").strip()
            if not ct:
                continue
            ct_to_disp.setdefault(ct, d or ct)
            if d:
                disp_to_ct[d] = ct
    return ct_to_disp, disp_to_ct


def canonical_card_type(
    raw: str,
    ct_to_disp: dict[str, str],
    disp_to_ct: dict[str, str],
) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    if s in ct_to_disp:
        return s
    if s in disp_to_ct:
        return disp_to_ct[s]
    return s


def serial_sort_tuple(ser: int) -> tuple[int, int]:
    """Non-serial (-1) first, then denominators descending (499 before 99)."""
    if ser == -1:
        return (0, 0)
    return (1, -ser)


def card_type_sort_tier(ct: str) -> int:
    """Paper → Chrome → Paper Auto → Chrome Auto; then everything else."""
    if ct in ("Base", "Bowman Prospects"):
        return 0
    if ct == "Bowman Chrome Prospects":
        return 1
    if ct in ("Bowman Prospect Autographs", "Bowman Rookies and Veterans Autographs"):
        return 2
    if ct in ("Chrome Prospect Autographs", "Chrome Rookie Autographs"):
        return 3
    return 4


def display_name_for_card_type_display(short_disp: str) -> str:
    d = (short_disp or "").strip()
    if d in DISPLAY_NAME_BY_CARD_TYPE_DISPLAY:
        return DISPLAY_NAME_BY_CARD_TYPE_DISPLAY[d]
    parts = d.replace("-", " ").split()
    return " ".join(p[:1].upper() + p[1:].lower() if p else "" for p in parts).strip() or d


def sort_hint_tuple(canonical_ct: str, serial: int) -> tuple[int, str, tuple[int, int]]:
    """Fallback ordering when ``(canonical_ct, serial)`` is missing from the combos CSV."""
    return (card_type_sort_tier(canonical_ct), canonical_ct, serial_sort_tuple(serial))


def load_combo_sort_index(
    csv_path: Path,
) -> dict[tuple[str, int], dict[str, object]]:
    """
    Load ``2025_Bowman_retail_card_type_serial_combos_observed.csv`` rows.

    Returns map ``(canonical card_type, serial)`` -> ``{"sort_order": int, "display_name": str,
    "card_type_display": str}``.
    """
    out: dict[tuple[str, int], dict[str, object]] = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            ct = (row.get("card_type") or "").strip()
            sd = (row.get("serial") or "").strip()
            if not ct or sd == "":
                continue
            try:
                ser_i = int(sd)
            except ValueError:
                continue
            try:
                so = int((row.get("sort_order") or "0").strip() or "0")
            except ValueError:
                so = 0
            dn = (row.get("display_name") or "").strip()
            ctd = (row.get("card_type_display") or "").strip()
            out[(ct, ser_i)] = {
                "sort_order": so,
                "display_name": dn,
                "card_type_display": ctd,
            }
    return out


def combo_meta_for_cluster(
    canonical_ct: str,
    serial: int,
    combo_index: Mapping[tuple[str, int], dict[str, object]],
    ct_to_disp: dict[str, str],
) -> tuple[Optional[int], str, str]:
    """``(sort_order or None, display_name, card_type_display)``."""
    meta = combo_index.get((canonical_ct, serial))
    short_disp = ct_to_disp.get(canonical_ct, "")
    disp_name = display_name_for_card_type_display(short_disp)
    if meta is None:
        return None, disp_name, short_disp
    so_raw = meta.get("sort_order")
    try:
        sort_o: Optional[int] = int(so_raw) if so_raw is not None and str(so_raw).strip() != "" else None
    except (TypeError, ValueError):
        sort_o = None
    dn = str(meta.get("display_name") or disp_name)
    ctd = str(meta.get("card_type_display") or short_disp)
    return sort_o, dn, ctd
