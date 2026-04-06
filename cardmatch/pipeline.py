from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from cardmatch.card_type import (
    display_card_type_for_review,
    parse_axis_insert_number,
    row_excluded_from_listing_counts,
    row_is_graded_listing,
    write_listing_count_reports,
)
from cardmatch.normalize import abridge_listing_title
from cardmatch.pilot import match_pilot
from cardmatch.player_index import load_bowman_draft_players
from cardmatch.review_slice import (
    load_bdc_player_rank,
    load_player_card_rank,
    load_review_config,
    load_review_player_keys,
    row_in_review_slice,
    row_matches_classification_focus,
)


def _ordered_fieldnames(rows: List[Dict[str, Any]]) -> List[str]:
    order: List[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                order.append(k)
    for k in EXTRA:
        if k not in seen:
            seen.add(k)
            order.append(k)
    return order


REVIEW_SLICE_COLUMNS = ["player", "price", "card_type", "title"]


def _review_slice_rows_label(card_nums: List[str]) -> str:
    """Label for run_summary count line, e.g. 'BD-1..BD-20 players'."""
    nums = [str(x).strip() for x in card_nums if str(x).strip()]
    if not nums:
        return "review targets"
    if len(nums) == 1:
        return f"{nums[0]} player"
    return f"{nums[0]}..{nums[-1]} players"


def _review_slice_export_blurb(card_nums: List[str]) -> str:
    """Label for run_summary outputs line, e.g. 'BD-1..BD-20 player slice'."""
    nums = [str(x).strip() for x in card_nums if str(x).strip()]
    if not nums:
        return "review targets"
    if len(nums) == 1:
        return f"{nums[0]} player"
    return f"{nums[0]}..{nums[-1]} player"


def _row_is_lot(row: Dict[str, Any]) -> bool:
    return (row.get("pilot_is_lot") or "") == "1"


def _row_is_graded(row: Dict[str, Any]) -> bool:
    """Slab / graded listings (PSA, BGS, …) — excluded from review exports."""
    return row_is_graded_listing(row)


def _row_excluded_from_review_focus(row: Dict[str, Any], classification_focus: str) -> bool:
    """
    Rows omitted from `review_focus.csv`. For **`bdc_chrome_prospect`**, use the same rules as
    `listing_counts_by_card_type.csv` so the focus matches that aggregate bucket.
    """
    f = (classification_focus or "").strip().lower()
    if f == "bdc_chrome_prospect":
        return row_excluded_from_listing_counts(row)
    return _row_is_lot(row) or _row_is_graded(row)


def _price_round_dollar(price: Any) -> str:
    if price is None:
        return ""
    s = str(price).strip()
    if not s:
        return ""
    try:
        return str(int(round(float(s))))
    except ValueError:
        return ""


def _focus_explain(classification_focus: str) -> str:
    f = (classification_focus or "").strip().lower()
    if f == "axis":
        return "`axis` = **Axis** insert (classifier `WF_axis`; word *axis* or `#A-…`)"
    if f == "paper_base":
        return "`paper_base` = **paper BD** base only; use `base` for **BDC Chrome Prospect · Base** (chrome stock)"
    if f == "base":
        return "`base` = **BDC Chrome Prospect · Base** (chrome stock) only; use `paper_base` for paper BD"
    if f == "refractor":
        return (
            "`refractor` = canonical **BDC Chrome Prospect · …** parallels, **Bowman Axis** (not Base), "
            "**Etched in Glass**, **Image Variations**; not **BDC Chrome Prospect · Base**"
        )
    if f == "chrome_refractor_plain":
        return (
            "`chrome_refractor_plain` = canonical primary exactly **BDC Chrome Prospect · Refractor** "
            "(plain silver parallel; excludes **… · Refractor · Auto**)"
        )
    if f == "bdc_chrome_prospect_parallel":
        return (
            "`bdc_chrome_prospect_parallel` = canonical primary exactly **BDC Chrome Prospect · Parallel** "
            "(still unresolved after serial→color / title parallel inference from `nb_numbered_serial`)"
        )
    if f == "refractor_and_chrome_plain":
        return (
            "`refractor_and_chrome_plain` = canonical `row_primary_card_type`: **BDC Chrome Prospect · Refractor**, "
            "**BDC Chrome Prospect · Parallel**, CPA (**BDC Chrome Prospect · …**) / **Chrome Prospect College Variations** "
            "prefixes, **College Variation** (excludes colored BDC parallels)"
        )
    if f == "bdc_chrome_prospect_auto":
        return (
            "`bdc_chrome_prospect_auto` = canonical `row_primary_card_type` exactly **BDC Chrome Prospect · Auto** "
            "(Chrome Prospect Autographs base line; excludes parallel/colored **… · Auto** variants)"
        )
    if f == "bdc_chrome_prospect":
        return (
            "`bdc_chrome_prospect` = canonical `row_primary_card_type` exactly **BDC Chrome Prospect** "
            "(generic chrome prospect line; not **· Base**, **· Refractor**, **· Auto**, etc.)"
        )
    if f == "other":
        return (
            "`other` = listings that received the legacy chrome-vs-paper default "
            "(**BDC Chrome Prospect · Base** if *chrome* in title, else **Base-Paper**); "
            "former **Other** bucket for manual review"
        )
    if f == "primary_exact":
        return (
            "`primary_exact` = canonical `row_primary_card_type` equals **`primary_card_type_exact`** "
            "in `review_targets.json`"
        )
    return (classification_focus or "").strip() or "(see `review_targets.json`)"


def review_focus_row_source(
    rows_out: List[Dict[str, Any]],
    slice_rows: List[Dict[str, Any]],
    classification_focus: str,
    rc: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Rows to draw `review_focus.csv` from. `review_focus_scope` in JSON: `all` | `slice`.
    If `all`, use the full scored pool. If `slice`, only BD card_numbers slice rows (plus lot/graded filters).
    If omitted, `axis` and refractor-family focuses use all scored rows; otherwise defaults to slice.
    For **`bdc_chrome_prospect_auto`**, set **`review_focus_scope` to `all`** to list every plain **BDC Chrome Prospect · Auto** listing in the pilot.
    """
    scope = (rc.get("review_focus_scope") or "").strip().lower()
    f = (classification_focus or "").strip().lower()
    if scope == "all":
        return rows_out
    if scope == "slice":
        return slice_rows
    if f == "axis":
        return rows_out
    if f == "refractor" or f == "chrome_refractor_plain" or f == "refractor_and_chrome_plain":
        return rows_out
    if (
        f == "bdc_chrome_prospect_auto"
        or f == "bdc_chrome_prospect"
        or f == "other"
        or f == "bdc_chrome_prospect_parallel"
        or f == "primary_exact"
    ):
        return rows_out
    return slice_rows


def _unclassified_sort_key(r: Dict[str, Any]) -> tuple:
    ps = r.get("price")
    try:
        if ps is None or str(ps).strip() == "":
            pv = float("inf")
        else:
            pv = float(ps)
    except (TypeError, ValueError):
        pv = float("inf")
    title = (r.get("title") or "").strip()
    return (pv, title)


def _review_sort_label(sort_mode: str) -> str:
    m = (sort_mode or "").strip().lower()
    if m == "price_desc":
        return "price descending (most expensive first; missing price last)"
    return "BD# ascending, then price ascending (missing price last)"


def _resolve_focus_sort_mode(
    rc: Dict[str, Any], classification_focus: str, slice_sort: str
) -> str:
    explicit = (rc.get("review_focus_sort") or "").strip().lower()
    if explicit:
        return explicit
    if classification_focus in (
        "bdc_chrome_prospect_auto",
        "bdc_chrome_prospect",
        "bdc_chrome_prospect_parallel",
        "chrome_refractor_plain",
        "primary_exact",
    ):
        return "bdc_then_price_asc"
    if classification_focus == "other":
        return "player_then_price_asc"
    return slice_sort or "bd_then_price_asc"


def _make_rank_then_price_key(rank_map: Dict[str, int]):
    """Sort by checklist rank (1..n), then price ascending (missing last)."""

    def key(r: Dict[str, Any]) -> tuple:
        p = (r.get("pilot_player_guess") or "").strip()
        rank = rank_map.get(p, 999999)
        ps = r.get("price")
        try:
            if ps is None or str(ps).strip() == "":
                pv = float("inf")
            else:
                pv = float(ps)
        except (TypeError, ValueError):
            pv = float("inf")
        return (rank, pv)

    return key


def write_review_derived_csvs(
    rows_out: List[Dict[str, Any]],
    out_dir: Path,
    checklist: Path,
    review_config: Path,
    *,
    outputs: Optional[Set[str]] = None,
) -> Tuple[Path, Path, Path, int, str]:
    """
    From already-scored rows, write review_slice.csv, review_focus.csv,
    and review_unclassified.csv.
    `outputs` — if set, only those names are written (e.g. {"focus"} for a fast refresh).
    Returns (slice_path, focus_path, unclassified_path, n_focus, focus_sort_blurb).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    write_set = outputs if outputs is not None else {"slice", "focus", "unclassified"}
    rc = load_review_config(review_config)
    card_nums = rc.get("card_numbers") or []
    classification_focus = (rc.get("classification_focus") or "base").strip().lower()
    sort_mode = (rc.get("review_slice_sort") or "bd_then_price_asc").strip().lower()
    review_players = load_review_player_keys(checklist, card_nums)
    player_card_rank = load_player_card_rank(checklist, card_nums)

    slice_rows = [
        r
        for r in rows_out
        if row_in_review_slice(r.get("pilot_player_guess") or "", review_players)
        and not _row_is_lot(r)
        and not _row_is_graded(r)
    ]

    def _review_sort_key_bd_then_price_asc(r: Dict[str, Any]) -> tuple:
        p = (r.get("pilot_player_guess") or "").strip()
        rank = player_card_rank.get(p, 999999)
        ps = r.get("price")
        try:
            if ps is None or str(ps).strip() == "":
                pv = float("inf")
            else:
                pv = float(ps)
        except (TypeError, ValueError):
            pv = float("inf")
        return (rank, pv)

    def _review_sort_key_price_desc(r: Dict[str, Any]) -> tuple:
        """Highest price first; missing/invalid price last; stable tie-break."""
        ps = r.get("price")
        try:
            if ps is None or str(ps).strip() == "":
                return (1, 0.0, "", "")
            pv = float(ps)
            return (0, -pv, (r.get("pilot_player_guess") or "").lower(), (r.get("title") or ""))
        except (TypeError, ValueError):
            return (1, 0.0, "", "")

    def _review_sort_key_axis_a_then_price_asc(r: Dict[str, Any]) -> tuple:
        """Axis #A-… ascending, then price ascending (missing price last)."""
        an = parse_axis_insert_number(r.get("title") or "")
        ps = r.get("price")
        try:
            if ps is None or str(ps).strip() == "":
                pv = float("inf")
            else:
                pv = float(ps)
        except (TypeError, ValueError):
            pv = float("inf")
        return (an, pv, (r.get("pilot_player_guess") or "").lower(), (r.get("title") or "").lower())

    def _review_sort_key_player_then_price_asc(r: Dict[str, Any]) -> tuple:
        """Player name A–Z, then price ascending (missing price last); title tie-break."""
        name = (r.get("pilot_player_guess") or "").strip().lower()
        missing_name = 1 if not name else 0
        ps = r.get("price")
        try:
            if ps is None or str(ps).strip() == "":
                pv = float("inf")
            else:
                pv = float(ps)
        except (TypeError, ValueError):
            pv = float("inf")
        return (missing_name, name, pv, (r.get("title") or "").lower())

    if sort_mode == "price_desc":
        slice_rows.sort(key=_review_sort_key_price_desc)
    else:
        slice_rows.sort(key=_review_sort_key_bd_then_price_asc)

    slice_path = out_dir / "review_slice.csv"
    if "slice" in write_set:
        with slice_path.open("w", encoding="utf-8", newline="") as fw:
            w = csv.DictWriter(fw, fieldnames=REVIEW_SLICE_COLUMNS, extrasaction="ignore")
            w.writeheader()
            for r in slice_rows:
                w.writerow(_review_slice_compact_row(r))

    focus_pool = review_focus_row_source(rows_out, slice_rows, classification_focus, rc)
    focus_rows = [
        r
        for r in focus_pool
        if row_matches_classification_focus(r, classification_focus, review_config=rc)
        and not _row_excluded_from_review_focus(r, classification_focus)
    ]
    focus_sort_mode = _resolve_focus_sort_mode(rc, classification_focus, sort_mode)
    try:
        bdc_cap = int(rc.get("bdc_rank_max") or 200)
    except (TypeError, ValueError):
        bdc_cap = 200
    bdc_cap = max(1, min(bdc_cap, 500))

    if classification_focus == "axis":
        focus_rows.sort(key=_review_sort_key_axis_a_then_price_asc)
    elif focus_sort_mode == "player_then_price_asc":
        focus_rows.sort(key=_review_sort_key_player_then_price_asc)
    elif focus_sort_mode == "bdc_then_price_asc":
        bdc_rank = load_bdc_player_rank(checklist, bdc_cap)
        focus_rows.sort(key=_make_rank_then_price_key(bdc_rank))
    elif focus_sort_mode == "price_desc":
        focus_rows.sort(key=_review_sort_key_price_desc)
    else:
        focus_rows.sort(key=_review_sort_key_bd_then_price_asc)

    if classification_focus == "axis":
        focus_sort_blurb = "Axis #A-… number ascending, then price ascending (missing price last)"
    elif classification_focus == "other":
        focus_sort_blurb = (
            "Player name A–Z, then price ascending (missing price last); "
            "legacy default bucket (chrome vs paper) for review"
        )
    elif focus_sort_mode == "bdc_then_price_asc":
        focus_sort_blurb = (
            f"BDC# ascending (1–{bdc_cap} chrome checklist order), "
            "then price ascending (missing price last)"
        )
    elif focus_sort_mode == "player_then_price_asc":
        focus_sort_blurb = (
            "Player name A–Z, then price ascending (missing price last)"
        )
    elif focus_sort_mode == "price_desc":
        focus_sort_blurb = _review_sort_label("price_desc")
    else:
        focus_sort_blurb = (
            "BD# ascending (order from `card_numbers` in `review_targets.json`), "
            "then price ascending (missing price last)"
        )

    focus_path = out_dir / "review_focus.csv"
    if "focus" in write_set:
        with focus_path.open("w", encoding="utf-8", newline="") as fw:
            w = csv.DictWriter(fw, fieldnames=REVIEW_SLICE_COLUMNS, extrasaction="ignore")
            w.writeheader()
            for r in focus_rows:
                w.writerow(_review_slice_compact_row(r))

    n_focus = len(focus_rows)

    unclassified_rows = [
        r
        for r in rows_out
        if (r.get("pilot_player_status") or "") == "unknown" and not _row_is_graded(r)
    ]
    unclassified_rows.sort(key=_unclassified_sort_key)
    unclassified_path = out_dir / "review_unclassified.csv"
    if "unclassified" in write_set:
        with unclassified_path.open("w", encoding="utf-8", newline="") as fw:
            w = csv.DictWriter(fw, fieldnames=REVIEW_SLICE_COLUMNS, extrasaction="ignore")
            w.writeheader()
            for r in unclassified_rows:
                w.writerow(_review_slice_compact_row(r))

    return slice_path, focus_path, unclassified_path, n_focus, focus_sort_blurb


def _review_slice_compact_row(row: Dict[str, Any]) -> Dict[str, str]:
    """Human-oriented review row: player, price, primary card type, abridged title."""
    price_str = _price_round_dollar(row.get("price"))
    return {
        "player": (row.get("pilot_player_guess") or "").strip(),
        "price": price_str,
        "card_type": display_card_type_for_review(row),
        "title": abridge_listing_title(row.get("title") or ""),
    }


EXTRA = [
    "pilot_player_guess",
    "pilot_player_score",
    "pilot_player_status",
    "pilot_is_likely_base",
    "pilot_is_graded",
    "pilot_is_lot",
    "pilot_is_draft_night",
    "pilot_is_chrome",
    "pilot_is_orange_border",
    "pilot_is_likely_chrome_base",
    "pilot_is_snack_pack",
    "pilot_is_axis",
    "pilot_reason_codes",
    "matcher_version",
]


def score_rows_to_run_dir(
    *,
    rows_in: List[Dict[str, Any]],
    out_dir: Path,
    checklist: Path,
    review_config: Path,
    baseline: Optional[Path],
    input_label: str,
    run_allow: Set[str],
    no_run_filter: bool,
) -> Tuple[Path, Path, Path, Path, Path, Path, Path]:
    """
    Score listing rows and write pilot_scored_full.csv, review_slice.csv,
    review_focus.csv, review_unclassified.csv, run_summary.md,
    listing_counts_by_card_type.csv, listing_counts_by_player_and_card_type.csv.
    Returns paths (full, slice, focus, unclassified, summary, counts_by_type, counts_by_player).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    names, last_index = load_bowman_draft_players(checklist)
    rc = load_review_config(review_config)

    has_run = bool(rows_in) and ("run_id" in rows_in[0])

    if has_run and not run_allow and not no_run_filter:
        raise RuntimeError(
            "Rows include run_id but no run allowlist and not no_run_filter. "
            "Pass Bowman Draft term_search run UUIDs or use --no-run-filter."
        )

    rows_out: List[Dict[str, Any]] = []
    skipped_run = 0
    n_in = len(rows_in)

    for row in rows_in:
        if has_run and run_allow:
            rid = (row.get("run_id") or "").strip()
            if rid not in run_allow:
                skipped_run += 1
                continue
        title = row.get("title") or ""
        pr = match_pilot(title, names, last_index)
        row2 = dict(row)
        row2["pilot_player_guess"] = pr.player_guess
        row2["pilot_player_score"] = f"{pr.player_score:.2f}"
        row2["pilot_player_status"] = pr.player_status
        row2["pilot_is_likely_base"] = "1" if pr.is_likely_base else "0"
        row2["pilot_is_graded"] = "1" if pr.is_graded else "0"
        row2["pilot_is_lot"] = "1" if pr.is_lot else "0"
        row2["pilot_is_draft_night"] = "1" if pr.is_draft_night else "0"
        row2["pilot_is_chrome"] = "1" if pr.is_chrome else "0"
        row2["pilot_is_orange_border"] = "1" if pr.is_orange_border else "0"
        row2["pilot_is_likely_chrome_base"] = "1" if pr.is_likely_chrome_base else "0"
        row2["pilot_is_snack_pack"] = "1" if pr.is_snack_pack else "0"
        row2["pilot_is_axis"] = "1" if pr.is_axis else "0"
        row2["pilot_reason_codes"] = json.dumps(pr.reason_codes)
        row2["matcher_version"] = pr.matcher_version
        rows_out.append(row2)

    fieldnames = _ordered_fieldnames(rows_out)

    full_path = out_dir / "pilot_scored_full.csv"
    with full_path.open("w", encoding="utf-8", newline="") as fw:
        w = csv.DictWriter(fw, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

    slice_path, focus_path, unclassified_path, n_focus, focus_sort_blurb = write_review_derived_csvs(
        rows_out, out_dir, checklist, review_config
    )
    card_nums = rc.get("card_numbers") or []
    review_players = load_review_player_keys(checklist, card_nums)
    slice_rows = [
        r
        for r in rows_out
        if row_in_review_slice(r.get("pilot_player_guess") or "", review_players)
        and not _row_is_lot(r)
        and not _row_is_graded(r)
    ]
    classification_focus = (rc.get("classification_focus") or "base").strip().lower()
    n_unclassified = sum(
        1
        for r in rows_out
        if (r.get("pilot_player_status") or "") == "unknown" and not _row_is_graded(r)
    )

    st: Counter[str] = Counter()
    for r in rows_out:
        st[r.get("pilot_player_status") or ""] += 1
    base_yes = sum(1 for r in rows_out if r.get("pilot_is_likely_base") == "1")

    sort_mode = (rc.get("review_slice_sort") or "bd_then_price_asc").strip().lower()
    sort_blurb = _review_sort_label(sort_mode)

    counts_by_type_path, counts_by_player_path, ct_counts = write_listing_count_reports(rows_out, out_dir)

    summary_path = out_dir / "run_summary.md"
    lines = [
        f"# Pilot run {out_dir.name}",
        "",
        f"- **Input:** {input_label}",
        f"- **Rows read:** {n_in}",
        f"- **Rows scored (after run filter):** {len(rows_out)}",
        f"- **Skipped by run_id filter:** {skipped_run}",
        f"- **Checklist:** `{checklist}`",
        f"- **Run allowlist size:** {len(run_allow)}",
        "",
        "## Counts",
        "",
        f"- **pilot_player_status:** {dict(st)}",
        f"- **is_likely_base yes:** {base_yes} / {len(rows_out)}",
        f"- **review_slice rows ({_review_slice_rows_label(card_nums)}):** {len(slice_rows)}",
        f"- **classification_focus (`review_targets.json`):** `{classification_focus}` → **{n_focus}** rows in `{focus_path.name}`",
        f"- **review_unclassified (unknown player):** {n_unclassified}",
        "",
        "## Outputs",
        "",
        f"- `{full_path.name}` — full scored CSV",
        f"- `{slice_path.name}` — {_review_slice_export_blurb(card_nums)} slice ({sort_blurb}); **excludes** lot listings (`WF_lot`) and graded slabs (`WF_graded` / `pilot_is_graded`)",
        f"- `{focus_path.name}` — rows matching **classification_focus** ({_focus_explain(classification_focus)}); "
        f"pool from `review_focus_scope` / defaults (see `review_targets.json`); **sort:** {focus_sort_blurb}; "
        "**excludes** lot listings (`WF_lot`) and graded slabs (`WF_graded` / `pilot_is_graded`)",
        f"- `{unclassified_path.name}` — rows with **unknown** player (could not match checklist)",
        f"- `{counts_by_type_path.name}` — **sum of listings by card type** (mutually exclusive primary type)",
        f"- `{counts_by_player_path.name}` — **listings by player and card type** (matrix)",
        "",
        "## Listings by card type",
        "",
        "Mutually exclusive **primary** type per listing (`cardmatch/card_type.py`). "
        "Bowman Chrome BDC parallels use refined labels when possible (e.g. Chrome Refractor Sky Blue, Chrome x-Fractor); "
        "otherwise non-base rows use the most specific `nb_*` classifier hit (last reason code).",
        "",
        "| card_type | listings |",
        "|-----------|----------|",
    ]
    for ct, n in sorted(ct_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"| {ct} | {n} |")
    lines.append("")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if baseline and baseline.is_file():
        changes = diff_baseline(baseline, full_path)
        ch_path = out_dir / "changes_since_previous.csv"
        with ch_path.open("w", encoding="utf-8", newline="") as fw:
            w = csv.DictWriter(
                fw,
                fieldnames=[
                    "item_id",
                    "title",
                    "old_guess",
                    "new_guess",
                    "old_base",
                    "new_base",
                    "old_reasons",
                    "new_reasons",
                ],
            )
            w.writeheader()
            for r in changes:
                w.writerow(r)

    return (
        full_path,
        slice_path,
        focus_path,
        unclassified_path,
        summary_path,
        counts_by_type_path,
        counts_by_player_path,
    )


def diff_baseline(old_csv: Path, new_csv: Path) -> List[Dict[str, str]]:
    def load(path: Path) -> Dict[str, Dict[str, str]]:
        with path.open(encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            out: Dict[str, Dict[str, str]] = {}
            for row in r:
                iid = (row.get("item_id") or "").strip()
                if iid:
                    out[iid] = {k: (row.get(k) or "") for k in row.keys()}
            return out

    o = load(old_csv)
    n = load(new_csv)
    changes: List[Dict[str, str]] = []
    for iid, nrow in n.items():
        orow = o.get(iid)
        if not orow:
            continue
        keys = ("pilot_player_guess", "pilot_is_likely_base", "pilot_reason_codes")
        if any((orow.get(k) != nrow.get(k)) for k in keys):
            changes.append(
                {
                    "item_id": iid,
                    "title": (nrow.get("title") or "")[:200],
                    "old_guess": orow.get("pilot_player_guess") or "",
                    "new_guess": nrow.get("pilot_player_guess") or "",
                    "old_base": orow.get("pilot_is_likely_base") or "",
                    "new_base": nrow.get("pilot_is_likely_base") or "",
                    "old_reasons": orow.get("pilot_reason_codes") or "",
                    "new_reasons": nrow.get("pilot_reason_codes") or "",
                }
            )
    return changes


def load_rows_from_csv(path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise ValueError("CSV has no header")
        rows = list(r)
        return rows, list(r.fieldnames or [])
