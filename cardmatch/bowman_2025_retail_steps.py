# Cmd+F: GH_ANCHOR_BOWMAN_2025_RETAIL_STEPS_7E4A2B01
"""
First-pass 2025 Bowman (retail) listing pipeline: exclusions + checklist code match + insert inference.

Step 1 aligns with docs/classification/2025_bowman_classifier_notes.md (Excluded listings).
Step 2 matches extracted checklist codes to ``data/checklists/normalized/2025_Bowman_card_number_lookup.csv``
(``card_type`` + ``card_type_display`` for short labels in pipeline / review CSVs)
and scores player alignment using cardmatch.player_match.
Step 3 infers missing insert codes by title word flags + checklist name match (same pass threshold as
step 2): ``ROY-*`` (rookie of the year + auto split), ``RRA-*`` / ``RR-*`` (rockstar rookies + auto),
``BTP-*`` (top 100 / scouts top 100). Skips a family when that prefix already appears in extracted codes.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

from cardmatch.bowman_2025_listing_display import listing_display_from_title
from cardmatch.bowman_2025_retail_combo_catalog import load_card_type_lookup_maps
from cardmatch.bowman_2025_retail_flags import (
    checklist_slot_int,
    serial_out_of_for_title,
    word_flags_for_title,
)
from cardmatch.player_match import build_last_index, guess_player_from_title

_DEFAULT_LOOKUP = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "checklists"
    / "normalized"
    / "2025_Bowman_card_number_lookup.csv"
)

# Fallback when CSV omits ``card_type_display`` (must match normalized checklist ``card_type`` strings).
_CARD_TYPE_DISPLAY_DEFAULTS: Dict[str, str] = {
    "Base": "Base",
    "Anime": "BA",
    "Anime Kanji Variations": "BA-K",
    "Bowman Chrome Prospects": "BCP",
    "Bowman Dual Autographs": "BDA",
    "Bowman Prospect Autographs": "BPA",
    "Bowman Prospects": "BP",
    "Bowman Rookies and Veterans Autographs": "PRV",
    "Bowman Scouts' Top 100": "BTP",
    "Bowman Spotlights": "BS",
    "Chrome Prospect Autographs": "CPA",
    "Chrome Rookie Autographs": "CRA",
    "Crystalized": "BWC",
    "Greatness Loading": "GL",
    "Hobby Stars": "HS",
    "Hobby Stars Autographs": "HSA",
    "Retrofractor Autographs": "CPR",
    "Retrofractors": "Retro",
    "Rockstar Rookies": "RR",
    "Rockstar Rookies Autographs": "RRA",
    "Rookie of the Year Favorites": "ROY",
    "Rookie of the Year Favorites Autographs": "ROY-A",
    "Very Important Prospects": "VIP",
    "Very Important Prospects Autographs": "VIP-A",
}


def player_name_for_review_csv(full_name: str) -> str:
    """
    Matched review CSVs only: first token truncated to two letters, rest unchanged
    (``Jackson Humphries`` → ``Ja Humphries``).
    """
    s = (full_name or "").strip()
    if not s:
        return ""
    parts = s.split()
    if len(parts) == 1:
        w = parts[0]
        return w if len(w) <= 2 else w[:2]
    return f"{parts[0][:2]} {' '.join(parts[1:])}".strip()


def _re(pat: str) -> re.Pattern[str]:
    return re.compile(pat, re.IGNORECASE)


def _clean(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


def exclusion_reason(title: str) -> str:
    """
    Return a non-empty reason string if the listing should be excluded; else "".

    Uses the same ``WF_*`` patterns as ``cardmatch.bowman_2025_retail_flags`` so selling /
    gating flags stay in one place (including non–Bowman-retail insert lines such as
    ``WF_insert_melt_mashers``).
    """
    s = _clean(title)
    if not s:
        return "empty_title"
    wf = word_flags_for_title(s)
    if wf["WF_complete_set"]:
        return "complete_set"
    if wf["WF_pick"]:
        return "pick_or_volume_header"
    if wf["WF_set_builder"]:
        return "set_builder"
    if wf["WF_presale"]:
        return "presale"
    if wf["WF_graded"]:
        return "graded_or_slab"
    # Other Topps Bowman products (not 2025 Bowman retail checklist pipeline).
    if wf["WF_bowmans_best"]:
        return "non_bowman_retail_bowmans_best"
    if wf["WF_bowman_draft"]:
        return "non_bowman_retail_bowman_draft"
    # Non–Bowman-retail insert / product lines (before lot so titles like "Melt Mashers lot"
    # classify as non-retail insert, not generic volume).
    if wf["WF_insert_melt_mashers"]:
        return "non_bowman_retail_insert_melt_mashers"
    if wf["WF_insert_ascensions"]:
        return "non_bowman_retail_insert_ascensions"
    if wf["WF_insert_gpk"]:
        return "non_bowman_retail_insert_gpk"
    if wf["WF_insert_it_came_to_the_league"]:
        return "non_bowman_retail_insert_it_came_to_the_league"
    if wf["WF_insert_meteoric_rise"]:
        return "non_bowman_retail_insert_meteoric_rise"
    if wf["WF_insert_max_volume"]:
        return "non_bowman_retail_insert_max_volume"
    if wf["WF_insert_adios"]:
        return "non_bowman_retail_insert_adios"
    if wf["WF_lot"]:
        return "lot"
    return ""


@dataclass(frozen=True)
class ChecklistRow:
    card_number: str
    player: str
    card_type: str
    card_type_display: str


def load_card_lookup(path: Path | None = None) -> Tuple[Dict[str, ChecklistRow], List[str]]:
    """
    Returns lookup by normalized ``card_number`` and parallel list of player names (checklist order).

    Expects ``card_type_display`` on the CSV when present; otherwise derives from ``card_type`` via
    :data:`_CARD_TYPE_DISPLAY_DEFAULTS`.
    """
    p = path or _DEFAULT_LOOKUP
    by_key: Dict[str, ChecklistRow] = {}
    names: List[str] = []
    with p.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            cn = (row.get("card_number") or "").strip()
            pl = (row.get("player") or "").strip()
            ct = (row.get("card_type") or "").strip()
            ctd_raw = (row.get("card_type_display") or "").strip()
            ctd = ctd_raw if ctd_raw else _CARD_TYPE_DISPLAY_DEFAULTS.get(ct, ct)
            if not cn:
                continue
            by_key[cn] = ChecklistRow(cn, pl, ct, ctd)
            names.append(pl)
    return by_key, names


def checklist_code_prefixes(by_key: Dict[str, ChecklistRow]) -> List[str]:
    seen: set[str] = set()
    for k in by_key:
        if "-" in k:
            seen.add(k.split("-", 1)[0].upper())
    return sorted(seen, key=lambda x: (-len(x), x))


def _normalize_code(prefix: str, suffix: str) -> Optional[str]:
    pre = prefix.strip().upper()
    suf = suffix.strip().upper()
    if not pre or not suf:
        return None
    if suf.isdigit():
        return f"{pre}-{int(suf)}"
    if re.fullmatch(r"[A-Z]{2,5}", suf):
        return f"{pre}-{suf}"
    return None


def extract_checklist_codes(title: str, prefixes: Sequence[str]) -> List[str]:
    """
    Return ordered unique checklist codes found in the title.

    Uses **strict** patterns so plain words are not parsed as codes (e.g. ``Royals`` ≠ ``ROY``,
    ``base`` ≠ ``BA``, ``Baty`` ≠ ``BA`` + ``ty``, ``Cracked`` ≠ ``CRA`` + ``cked``):

    - ``PREFIX-SUFFIX`` with a real hyphen (optional spaces around the hyphen). Suffix is
      digits or 2–5 letters (initials-style auto codes).
    - ``PREFIX`` immediately followed by digits only (no hyphen), e.g. ``BCP22``, ``HS11`` —
      digits must end the run (``(?!\d)``) so we do not eat into longer numbers.
    - Base slot: ``#`` + 1–3 digits for **veteran/rookie base** checklist slots **1–100** only.
      Not followed by a serial fraction (``#116/199`` is serial, not card 116). Matches
      ``#99``, ``# 99``, not ``#11/25`` as card 11 (ambiguous; skipped).
    - **Not** applied when ``WF_chrome`` is true: bare ``#1``–``#100`` in Chrome listings are out of
      scope for paper base slots (use ``BCP-`` / ``CPA-`` / etc.); avoids Mojo ``#7`` → paper base 7.
    """
    s = _clean(title)
    if not s or not prefixes:
        return []

    alt = "|".join(re.escape(p) for p in prefixes)
    # Hyphen required — kills ROY+als, BA+se, CRA+cked, BA+ty, etc.
    rx_hyphen = re.compile(
        rf"\b({alt})\s*-\s*(\d{{1,4}}|[A-Za-z]{{2,5}})(?!\d|[A-Za-z])\b",
        re.IGNORECASE,
    )
    # Digits only, glued to prefix (no letters in suffix) — e.g. BCP22, HS11; not ROYals.
    rx_glued_digits = re.compile(
        rf"\b({alt})(\d{{1,4}})(?!\d)\b",
        re.IGNORECASE,
    )

    found: List[str] = []
    seen: set[str] = set()

    for m in rx_hyphen.finditer(s):
        key = _normalize_code(m.group(1), m.group(2))
        if key and key not in seen:
            seen.add(key)
            found.append(key)

    for m in rx_glued_digits.finditer(s):
        key = _normalize_code(m.group(1), m.group(2))
        if key and key not in seen:
            seen.add(key)
            found.append(key)

    # Paper retail base #1–#100 only; never treat #116/199 as card 116. Skip entirely for Chrome-stock
    # titles so parallel copy (e.g. Mojo #7) does not map to paper base slot 7.
    if not word_flags_for_title(s).get("WF_chrome"):
        rx_hash_base = re.compile(
            r"#\s*(\d{1,3})(?!\s*[\/／⁄]\s*\d)\b",
        )
        for m in rx_hash_base.finditer(s):
            n = int(m.group(1))
            if 1 <= n <= 100:
                key = str(n)
                if key not in seen:
                    seen.add(key)
                    found.append(key)

    return found


# Minimum title↔checklist player similarity for a **passing** step-2 match and for step-3 insert inference.
# Below this, step 2 becomes ``rejected_player_mismatch`` (code may be right, name is not).
PLAYER_MATCH_PASS_MIN = 80.0

# ``match_status_after_step3`` when step 3 filled ``step3_inferred_card_number`` (ROY / RR / BTP).
MATCHED_STEP3_INSERT_STATUS = "matched_step3_insert"


def _extracted_codes_include_prefix(extracted_codes: str, prefix: str) -> bool:
    pre = prefix.strip().upper()
    for part in (extracted_codes or "").split("|"):
        if part.strip().upper().startswith(pre):
            return True
    return False


def _extracted_codes_include_rr_family(extracted_codes: str) -> bool:
    for part in (extracted_codes or "").split("|"):
        p = part.strip().upper()
        if p.startswith("RR-") or p.startswith("RRA-"):
            return True
    return False


def _infer_name_match_in_pool(
    title: str,
    candidates: Sequence[ChecklistRow],
    kind_if_hit: str,
) -> Tuple[str, str, float]:
    """
    Pick the checklist row in ``candidates`` with best title↔player score.

    Returns ``(card_number, kind_if_hit, score)`` on pass, or ``("", "", score)`` when no pass.
    """
    if not candidates:
        return "", "", 0.0
    names = [r.player for r in candidates]
    idx = build_last_index(names)
    best_name, score, _win = guess_player_from_title(title, names, idx)
    if score < PLAYER_MATCH_PASS_MIN or not best_name:
        return "", "", score
    matching = [r for r in candidates if r.player == best_name]
    if not matching:
        return "", "", score
    row = min(matching, key=lambda r: r.card_number)
    return row.card_number, kind_if_hit, score


def roy_checklist_subsets(by_key: Dict[str, ChecklistRow]) -> Tuple[List[ChecklistRow], List[ChecklistRow]]:
    """
    Split ``ROY-*`` checklist rows into base (numeric suffix) vs autograph initials (letter suffix).

    Built once per run; used by step-3 ROY name inference.
    """
    numeric: List[ChecklistRow] = []
    auto: List[ChecklistRow] = []
    for cn, row in by_key.items():
        if not cn.upper().startswith("ROY-"):
            continue
        suf = cn.split("-", 1)[1]
        if suf.isdigit():
            numeric.append(row)
        elif re.fullmatch(r"[A-Za-z]{2,5}", suf):
            auto.append(row)

    def _num_key(r: ChecklistRow) -> int:
        return int(r.card_number.split("-", 1)[1])

    numeric.sort(key=_num_key)
    auto.sort(key=lambda r: r.card_number)
    return numeric, auto


def rr_checklist_subsets(by_key: Dict[str, ChecklistRow]) -> Tuple[List[ChecklistRow], List[ChecklistRow]]:
    """Split ``RR-*`` vs ``RRA-*`` rows (``RRA-`` must be checked before ``RR-``)."""
    numeric: List[ChecklistRow] = []
    auto: List[ChecklistRow] = []
    for cn, row in by_key.items():
        u = cn.upper()
        if u.startswith("RRA-"):
            suf = cn.split("-", 1)[1]
            if re.fullmatch(r"[A-Za-z]{2,5}", suf):
                auto.append(row)
        elif u.startswith("RR-"):
            suf = cn.split("-", 1)[1]
            if suf.isdigit():
                numeric.append(row)

    def _num_key(r: ChecklistRow) -> int:
        return int(r.card_number.split("-", 1)[1])

    numeric.sort(key=_num_key)
    auto.sort(key=lambda r: r.card_number)
    return numeric, auto


def btp_checklist_rows(by_key: Dict[str, ChecklistRow]) -> List[ChecklistRow]:
    """All ``BTP-{slot}`` Bowman Scouts' Top 100 rows, sorted by slot."""
    rows: List[ChecklistRow] = []
    for cn, row in by_key.items():
        if not cn.upper().startswith("BTP-"):
            continue
        suf = cn.split("-", 1)[1]
        if suf.isdigit():
            rows.append(row)

    rows.sort(key=lambda r: int(r.card_number.split("-", 1)[1]))
    return rows


def infer_roy_card_number_from_title(
    title: str,
    wf: Dict[str, bool],
    extracted_codes: str,
    roy_numeric: Sequence[ChecklistRow],
    roy_auto: Sequence[ChecklistRow],
) -> Tuple[str, str, float]:
    """
    Step 3 (ROY only): infer ``ROY-*`` when ``WF_rookie_of_the_year`` is true, no ``ROY-`` code was
    extracted, and title vs checklist name score ≥ ``PLAYER_MATCH_PASS_MIN``.

    - ``WF_auto`` true → autograph initials rows (``ROY-AA``, …).
    - ``WF_auto`` false → numeric rows (``ROY-1``, …).

    Returns ``(inferred_card_number, inference_kind, best_score)`` where ``inference_kind`` is
    ``roy_auto_name``, ``roy_numeric_name``, or empty.
    """
    if not wf.get("WF_rookie_of_the_year"):
        return "", "", 0.0
    if _extracted_codes_include_prefix(extracted_codes, "ROY-"):
        return "", "", 0.0

    pool = list(roy_auto if wf.get("WF_auto") else roy_numeric)
    kind = "roy_auto_name" if wf.get("WF_auto") else "roy_numeric_name"
    return _infer_name_match_in_pool(title, pool, kind)


def infer_step3_insert_by_name(
    title: str,
    wf: Dict[str, bool],
    extracted_codes: str,
    roy_numeric: Sequence[ChecklistRow],
    roy_auto: Sequence[ChecklistRow],
    rr_numeric: Sequence[ChecklistRow],
    rr_auto: Sequence[ChecklistRow],
    btp_rows: Sequence[ChecklistRow],
) -> Tuple[str, str, float]:
    """
    Step 3: ROY name inference, else Rockstar Rookies (``RR-*`` / ``RRA-*``), else Top 100 ``BTP-*``.

    Rockstar: ``WF_insert_rockstar_rookies``; ``WF_auto`` → ``RRA-*`` else ``RR-*``. Skips when
    ``RR-`` or ``RRA-`` already extracted.

    Top 100: ``WF_insert_top_100`` or ``WF_insert_scouts_top_100``; skips when ``BTP-`` extracted.

    Returns ``(inferred_card_number, inference_kind, score)``; kinds include ``roy_*``, ``rr_auto_name``,
    ``rr_numeric_name``, ``btp_name``, or empty strings.
    """
    cn, kind, sc = infer_roy_card_number_from_title(
        title, wf, extracted_codes, roy_numeric, roy_auto
    )
    if cn:
        return cn, kind, sc

    if wf.get("WF_insert_rockstar_rookies") and not _extracted_codes_include_rr_family(
        extracted_codes
    ):
        pool = list(rr_auto if wf.get("WF_auto") else rr_numeric)
        k = "rr_auto_name" if wf.get("WF_auto") else "rr_numeric_name"
        cn2, kind2, sc2 = _infer_name_match_in_pool(title, pool, k)
        if cn2:
            return cn2, kind2, sc2

    if (wf.get("WF_insert_top_100") or wf.get("WF_insert_scouts_top_100")) and not _extracted_codes_include_prefix(
        extracted_codes, "BTP-"
    ):
        cn3, kind3, sc3 = _infer_name_match_in_pool(title, btp_rows, "btp_name")
        if cn3:
            return cn3, kind3, sc3

    return "", "", 0.0


@dataclass(frozen=True)
class MatchResult:
    match_status: str
    matched_card_number: str
    matched_player: str
    matched_card_type: str
    player_match_score: float
    extracted_codes: str


def match_listing_to_checklist(
    title: str,
    by_key: Dict[str, ChecklistRow],
    prefixes: Sequence[str],
) -> MatchResult:
    """
    Step 2: extract codes, look up rows, pick best row by player-title similarity.

    Only ``matched`` (player score ≥ ``PLAYER_MATCH_PASS_MIN``) carries identity fields;
    weaker scores become ``rejected_player_mismatch`` so nothing bogus flows to step 3.
    """
    codes = extract_checklist_codes(title, prefixes)
    codes_joined = "|".join(codes)

    if not codes:
        return MatchResult("unmatched_no_code", "", "", "", 0.0, "")

    best: Tuple[float, ChecklistRow, str] = (-1.0, ChecklistRow("", "", "", ""), "")

    for code in codes:
        row = by_key.get(code)
        if not row:
            continue
        _g_name, g_score, _g_win = guess_player_from_title(
            title, [row.player], build_last_index([row.player])
        )
        if g_score > best[0] or (abs(g_score - best[0]) <= 0.01 and len(code) > len(best[2])):
            best = (g_score, row, code)

    score, row, _winning_code = best
    if not row.card_number:
        return MatchResult("unmatched_code_not_on_checklist", "", "", "", 0.0, codes_joined)

    if score >= PLAYER_MATCH_PASS_MIN:
        return MatchResult(
            "matched",
            row.card_number,
            row.player,
            row.card_type_display,
            score,
            codes_joined,
        )

    return MatchResult(
        "rejected_player_mismatch",
        "",
        "",
        "",
        score,
        codes_joined,
    )


def process_title(
    title: str,
    by_key: Dict[str, ChecklistRow],
    prefixes: Sequence[str],
) -> Tuple[str, MatchResult]:
    """
    Run step 1 then step 2. Returns (exclusion_reason, MatchResult).

    When excluded, match_status is ``excluded`` and identity fields are cleared (extracted_codes kept).
    """
    ex = exclusion_reason(title)
    mr = match_listing_to_checklist(title, by_key, prefixes)
    if ex:
        return ex, MatchResult(
            "excluded",
            "",
            "",
            "",
            0.0,
            mr.extracted_codes,
        )
    return "", mr


def match_status_after_step3(excluded: str, match_status: str, step3_inferred_card: str) -> str:
    """
    Status after step 2 + step 3 name inference. Step-2 ``matched`` wins; else non-empty step-3 card
    becomes ``MATCHED_STEP3_INSERT_STATUS``; excluded stays ``excluded``; otherwise the step-2 status.
    """
    if (excluded or "").strip() == "1":
        return "excluded"
    if (match_status or "").strip() == "matched":
        return "matched"
    if (step3_inferred_card or "").strip():
        return MATCHED_STEP3_INSERT_STATUS
    return (match_status or "").strip() or "unknown"


def step23_pass(excluded: str, match_status: str, step3_inferred_card: str) -> bool:
    """True when the listing has a checklist identity from step 2 or step 3 name match (non-excluded)."""
    if (excluded or "").strip() == "1":
        return False
    if (match_status or "").strip() == "matched":
        return True
    return bool((step3_inferred_card or "").strip())


@dataclass(frozen=True)
class RetailApiContext:
    """Checklist + step-3 inference inputs for :func:`retail_steps_row_extensions` / HTTP APIs."""

    by_key: Dict[str, ChecklistRow]
    prefixes: List[str]
    roy_numeric: List[ChecklistRow]
    roy_auto: List[ChecklistRow]
    rr_numeric: List[ChecklistRow]
    rr_auto: List[ChecklistRow]
    btp_rows: List[ChecklistRow]
    ct_to_disp: Dict[str, str]
    disp_to_ct: Dict[str, str]


def load_retail_api_context(checklist: Path | None = None) -> RetailApiContext:
    """Load lookup, code prefixes, step-3 pools, and card-type display maps (same paths as CSV runner)."""
    p = (checklist or _DEFAULT_LOOKUP).resolve()
    by_key, _ = load_card_lookup(p)
    ct_to_disp, disp_to_ct = load_card_type_lookup_maps(p)
    roy_numeric, roy_auto = roy_checklist_subsets(by_key)
    rr_numeric, rr_auto = rr_checklist_subsets(by_key)
    btp_rows = btp_checklist_rows(by_key)
    prefixes = checklist_code_prefixes(by_key)
    return RetailApiContext(
        by_key=by_key,
        prefixes=prefixes,
        roy_numeric=roy_numeric,
        roy_auto=roy_auto,
        rr_numeric=rr_numeric,
        rr_auto=rr_auto,
        btp_rows=btp_rows,
        ct_to_disp=ct_to_disp,
        disp_to_ct=disp_to_ct,
    )


def retail_steps_row_extensions(title: str, ctx: RetailApiContext) -> Dict[str, str]:
    """
    Run retail steps 1–3 for one title; return the same string fields written to ``listings_steps12.csv``
    augmentation columns (no input CSV columns).
    """
    ex, mr = process_title(title, ctx.by_key, ctx.prefixes)
    slot = None if ex else checklist_slot_int(mr.matched_card_number)
    so = serial_out_of_for_title(title, slot)
    out: Dict[str, str] = {
        "WF_serial_out_of": "1" if so is not None else "0",
        "serial_out_of": "-1" if so is None else str(so),
        "exclusion_reason": ex,
        "excluded": "1" if ex else "0",
        "match_status": mr.match_status,
        "step2_pass": "1" if (not ex and mr.match_status == "matched") else "0",
        "matched_card_number": mr.matched_card_number,
        "matched_checklist_player": mr.matched_player,
        "matched_card_type": mr.matched_card_type,
        "player_match_score": f"{mr.player_match_score:.2f}" if mr.player_match_score else "",
        "extracted_codes": mr.extracted_codes,
    }
    if ex:
        out["step3_inferred_card_number"] = ""
        out["step3_inference_kind"] = ""
        out["step3_inference_score"] = ""
        out["step3_matched_checklist_player"] = ""
        out["step3_matched_card_type"] = ""
        out["match_status_after_step3"] = "excluded"
        out["step23_pass"] = "0"
        return out

    wf = word_flags_for_title(title, slot)
    inf_cn, inf_kind, inf_sc = infer_step3_insert_by_name(
        title,
        wf,
        mr.extracted_codes,
        ctx.roy_numeric,
        ctx.roy_auto,
        ctx.rr_numeric,
        ctx.rr_auto,
        ctx.btp_rows,
    )
    out["step3_inferred_card_number"] = inf_cn
    out["step3_inference_kind"] = inf_kind
    out["step3_inference_score"] = f"{inf_sc:.2f}" if inf_kind else ""
    ck_inf = ctx.by_key.get(inf_cn) if inf_cn else None
    out["step3_matched_checklist_player"] = ck_inf.player if ck_inf else ""
    out["step3_matched_card_type"] = ck_inf.card_type_display if ck_inf else ""
    out["match_status_after_step3"] = match_status_after_step3(
        out["excluded"], mr.match_status, inf_cn
    )
    out["step23_pass"] = (
        "1" if step23_pass(out["excluded"], mr.match_status, inf_cn) else "0"
    )
    return out


# Columns written by ``write_listings_steps12_split_by_match_status`` (human review only).
STEP2_REVIEW_COLUMNS: Tuple[str, str, str, str, str] = (
    "card_number",
    "player_name",
    "card_type",
    "listing_display",
    "listing",
)

# Step-2 ``matched`` review export + parsed serial (see classifier notes — hierarchical identity).
STEP3_MATCHED_REVIEW_COLUMNS: Tuple[str, str, str, str, str, str] = (
    "card_number",
    "serial",
    "player_name",
    "card_type",
    "listing_display",
    "listing",
)


def _card_number_sort_key(card_number: str) -> Tuple:
    """
    Sort key for checklist ``card_number`` strings: numeric slots by value, then hyphen codes
    (numeric suffix, then letter suffix), then other strings; empty last.
    """
    cn = (card_number or "").strip()
    if not cn:
        return (4, "", 0, "")
    if cn.isdigit():
        return (0, "", int(cn), "")
    m = re.match(r"^([A-Za-z]{1,12})-(.+)$", cn)
    if m:
        pre, suf = m.group(1).upper(), m.group(2)
        if suf.isdigit():
            return (0, pre, int(suf), "")
        return (1, pre, 0, suf.upper())
    return (3, cn.upper(), 0, "")


def _sort_matched_review_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return sorted(rows, key=lambda r: _card_number_sort_key(r.get("card_number") or ""))


def _step3_serial_sort_key(serial_cell: str) -> Tuple[int, int]:
    """Missing serial ``-1`` sorts before positive denominators; those sort descending (499 before 99)."""
    t = (serial_cell or "").strip()
    if t in ("", "-1"):
        return (0, 0)
    try:
        n = int(t)
    except ValueError:
        return (2, 0)
    if n < 0:
        return (2, 0)
    return (1, -n)


def _sort_step3_matched_review_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return sorted(
        rows,
        key=lambda r: (
            _card_number_sort_key(r.get("card_number") or ""),
            _step3_serial_sort_key(r.get("serial") or ""),
        ),
    )


def _merged_row_to_step2_review_row(row: Dict[str, str]) -> Dict[str, str]:
    """Map a listings_steps12 row to the review columns (``listing`` = raw title; ``listing_display`` cleaned)."""
    title = (row.get("title") or "").strip()
    num = (row.get("matched_card_number") or "").strip()
    if not num:
        codes = (row.get("extracted_codes") or "").strip()
        if codes:
            num = codes.split("|", 1)[0].strip()
    return {
        "card_number": num,
        "player_name": player_name_for_review_csv((row.get("matched_checklist_player") or "").strip()),
        "card_type": (row.get("matched_card_type") or "").strip(),
        "listing_display": listing_display_from_title(title, card_number=num or None),
        "listing": title,
    }


def _serial_cell_for_step3_row(row: Dict[str, str]) -> str:
    """Re-parse serial from ``listing`` + ``card_number`` so slot echo rules apply; ``-1`` = none."""
    r2 = _merged_row_to_step2_review_row(row)
    slot = checklist_slot_int(r2["card_number"])
    so = serial_out_of_for_title(r2["listing"], slot)
    return "-1" if so is None else str(so)


def _resolved_match_status_after_step3(row: Dict[str, str]) -> str:
    """Same ``match_status_after_step3`` value as step-23 split logic (handles blank + legacy ROY bucket)."""
    step3_inf = (row.get("step3_inferred_card_number") or "").strip()
    ms23 = (row.get("match_status_after_step3") or "").strip()
    if not ms23:
        ms23 = match_status_after_step3(
            row.get("excluded") or "",
            row.get("match_status") or "",
            step3_inf,
        )
    elif ms23 == "matched_step3_roy":
        ms23 = MATCHED_STEP3_INSERT_STATUS
    return ms23


def _merged_row_to_step3_matched_review_row(row: Dict[str, str]) -> Dict[str, str]:
    """Step-2 ``matched`` rows only: review columns including ``serial`` (``-1`` = no print run)."""
    r2 = _merged_row_to_step2_review_row(row)
    return {
        "card_number": r2["card_number"],
        "serial": _serial_cell_for_step3_row(row),
        "player_name": r2["player_name"],
        "card_type": r2["card_type"],
        "listing_display": r2["listing_display"],
        "listing": r2["listing"],
    }


def _merged_row_to_step23_review_row(row: Dict[str, str]) -> Dict[str, str]:
    """Review row using step-2 match when present, else step-3 inferred checklist fields."""
    title = (row.get("title") or "").strip()
    num = (row.get("matched_card_number") or "").strip()
    pl = (row.get("matched_checklist_player") or "").strip()
    ct = (row.get("matched_card_type") or "").strip()
    if not num:
        num = (row.get("step3_inferred_card_number") or "").strip()
        if not pl:
            pl = (row.get("step3_matched_checklist_player") or "").strip()
        if not ct:
            ct = (row.get("step3_matched_card_type") or "").strip()
    if not num:
        codes = (row.get("extracted_codes") or "").strip()
        if codes:
            num = codes.split("|", 1)[0].strip()
    return {
        "card_number": num,
        "player_name": player_name_for_review_csv(pl),
        "card_type": ct,
        "listing_display": listing_display_from_title(title, card_number=num or None),
        "listing": title,
    }


def write_listings_step23_split_by_match_status(
    merged_csv: Path,
    out_dir: Path | None = None,
) -> Dict[str, int]:
    """
    Split ``listings_steps12.csv`` by ``match_status_after_step3`` (step 2 + step 3 inference).

    Rows resolved only via step 3 land in ``matched_step3_insert``; ``unmatched_no_code`` etc.
    contain only listings **still** in that state after step 3.

    Output dir default: ``<merged_csv.parent>/step23_by_match_status/``.
    Filenames: ``listings_step23_<status>.csv`` with the same review columns as step-2 splits
    (``card_type`` is the short ``card_type_display`` from the checklist when the merge row carries it;
    ``player_name`` uses two-letter first-name truncation).
    The ``matched`` file is sorted by ``card_number`` (numeric-aware for ``PREFIX-123`` slots).
    """
    merged_csv = merged_csv.resolve()
    if out_dir is None:
        out_dir = merged_csv.parent / "step23_by_match_status"
    else:
        out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    buckets: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    with merged_csv.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        fieldnames = list(r.fieldnames or [])
        for col in ("excluded", "match_status"):
            if col not in fieldnames:
                raise ValueError(f"CSV missing {col} column: {merged_csv}")
        for row in r:
            ms23 = _resolved_match_status_after_step3(dict(row))
            buckets[ms23].append(_merged_row_to_step23_review_row(dict(row)))

    out_fields = list(STEP2_REVIEW_COLUMNS)
    counts: Dict[str, int] = {}
    for status, rows in buckets.items():
        safe = re.sub(r"[^0-9a-zA-Z_.-]+", "_", status).strip("_") or "unknown"
        path = out_dir / f"listings_step23_{safe}.csv"
        out_rows = _sort_matched_review_rows(rows) if status == "matched" else rows
        with path.open("w", newline="", encoding="utf-8") as fout:
            w = csv.DictWriter(fout, fieldnames=out_fields, extrasaction="ignore")
            w.writeheader()
            for rr in out_rows:
                w.writerow(rr)
        counts[status] = len(rows)

    still: List[Dict[str, str]] = []
    for st, rows in buckets.items():
        if st in ("excluded", "matched", MATCHED_STEP3_INSERT_STATUS, "matched_step3_roy"):
            continue
        still.extend(rows)
    still_path = out_dir / "listings_step23_still_unmatched_after_both.csv"
    with still_path.open("w", newline="", encoding="utf-8") as fout:
        w = csv.DictWriter(fout, fieldnames=out_fields, extrasaction="ignore")
        w.writeheader()
        for rr in still:
            w.writerow(rr)

    summary_path = out_dir / "step23_split_summary.txt"
    lines = [f"source: {merged_csv}", f"output_dir: {out_dir}", ""]
    for st in sorted(counts, key=lambda k: (-counts[k], k)):
        lines.append(f"{counts[st]}\t{st}")
    lines.append("")
    lines.append(f"{len(still)}\tstill_unmatched_after_both (union of non-excluded, non-matched buckets)")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return counts


def write_listings_step3_matched_with_serial(
    merged_csv: Path,
    out_dir: Path | None = None,
) -> int:
    """
    Write ``step3_by_match_status/listings_step3_matched.csv``: rows whose resolved
    ``match_status_after_step3`` is **matched** (step-2 checklist + player pass), with columns
    ``card_number``, ``serial``, ``player_name``, ``card_type``, ``listing_display``, ``listing``.

    This is a **review** export (serial ladder on the checklist slot), not the pipeline’s
    insert-inference “step 3” in :func:`infer_step3_insert_by_name`.

    ``serial`` is always recomputed from ``title`` + ``matched_card_number`` (``-1`` when none),
    sorted by ``card_number`` then ``serial`` (``-1`` rows first, then denominators descending).
    ``player_name`` / ``card_type`` use the same review formatting as step-2 splits.

    Returns the number of rows written (excluding header).
    """
    merged_csv = merged_csv.resolve()
    if out_dir is None:
        out_dir = merged_csv.parent / "step3_by_match_status"
    else:
        out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, str]] = []
    with merged_csv.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        fieldnames = list(r.fieldnames or [])
        for col in ("excluded", "match_status"):
            if col not in fieldnames:
                raise ValueError(f"CSV missing {col} column: {merged_csv}")
        for row in r:
            if _resolved_match_status_after_step3(dict(row)) != "matched":
                continue
            rows.append(_merged_row_to_step3_matched_review_row(dict(row)))

    out_path = out_dir / "listings_step3_matched.csv"
    out_rows = _sort_step3_matched_review_rows(rows)
    out_fields = list(STEP3_MATCHED_REVIEW_COLUMNS)
    with out_path.open("w", newline="", encoding="utf-8") as fout:
        w = csv.DictWriter(fout, fieldnames=out_fields, extrasaction="ignore")
        w.writeheader()
        for rr in out_rows:
            w.writerow(rr)

    summary_path = out_dir / "step3_matched_summary.txt"
    summary_path.write_text(
        f"source: {merged_csv}\n"
        f"output: {out_path}\n"
        f"rows: {len(out_rows)}\n",
        encoding="utf-8",
    )
    return len(out_rows)


def write_listings_steps12_split_by_match_status(
    merged_csv: Path,
    out_dir: Path | None = None,
) -> Dict[str, int]:
    """
    Read ``listings_steps12.csv`` (or any CSV with ``match_status`` and the step-2 columns)
    and write one CSV per status under ``out_dir`` (default: ``<merged_csv.parent>/step2_by_match_status/``).

    Each output file has exactly: ``card_number``, ``player_name``, ``card_type``, ``listing_display``,
    ``listing`` (``listing`` is the raw eBay ``title``; ``listing_display`` drops team/city noise, RC
    / rookie fluff, product noise words, then prefixes ``card_number``, optional ``Chrome`` (+ Mega/Mojo/Anime product line only), and parsed ``/serial`` when known).
    ``card_type`` echoes ``matched_card_type`` from the merge
    (short ``card_type_display`` when the pipeline wrote it). ``player_name`` is abbreviated
    (first word → two letters, e.g. ``Ja Humphries``).

    ``card_number`` uses ``matched_card_number`` when present; otherwise the first value in
    ``extracted_codes`` (pipe-separated), if any.

    Filenames: ``listings_step2_<match_status>.csv``.

    The ``matched`` file is sorted by ``card_number`` (numeric-aware for ``PREFIX-123`` slots).

    Returns row counts keyed by match_status.
    """
    merged_csv = merged_csv.resolve()
    if out_dir is None:
        out_dir = merged_csv.parent / "step2_by_match_status"
    else:
        out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    buckets: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    with merged_csv.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        fieldnames = list(r.fieldnames or [])
        if "match_status" not in fieldnames:
            raise ValueError(f"CSV missing match_status column: {merged_csv}")
        for row in r:
            st = (row.get("match_status") or "").strip() or "unknown"
            buckets[st].append(_merged_row_to_step2_review_row(dict(row)))

    out_fields = list(STEP2_REVIEW_COLUMNS)
    counts: Dict[str, int] = {}
    for status, rows in buckets.items():
        safe = re.sub(r"[^0-9a-zA-Z_.-]+", "_", status).strip("_") or "unknown"
        path = out_dir / f"listings_step2_{safe}.csv"
        out_rows = _sort_matched_review_rows(rows) if status == "matched" else rows
        with path.open("w", newline="", encoding="utf-8") as fout:
            w = csv.DictWriter(fout, fieldnames=out_fields, extrasaction="ignore")
            w.writeheader()
            for row in out_rows:
                w.writerow(row)
        counts[status] = len(rows)

    summary_path = out_dir / "step2_split_summary.txt"
    lines = [f"source: {merged_csv}", f"output_dir: {out_dir}", ""]
    for st in sorted(counts, key=lambda k: (-counts[k], k)):
        lines.append(f"{counts[st]}\t{st}")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return counts
