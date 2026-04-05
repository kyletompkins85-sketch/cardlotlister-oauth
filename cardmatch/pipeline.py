from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from cardmatch.pilot import match_pilot
from cardmatch.player_index import load_bowman_draft_players
from cardmatch.review_slice import load_review_config, load_review_player_keys, row_in_review_slice


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


EXTRA = [
    "pilot_player_guess",
    "pilot_player_score",
    "pilot_player_status",
    "pilot_is_likely_base",
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
) -> Tuple[Path, Path, Path]:
    """
    Score listing rows and write pilot_scored_full.csv, review_slice.csv, run_summary.md.
    Returns paths (full, slice, summary).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    names, last_index = load_bowman_draft_players(checklist)
    rc = load_review_config(review_config)
    card_nums = rc.get("card_numbers") or []
    review_players = load_review_player_keys(checklist, card_nums)

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

    slice_rows = [r for r in rows_out if row_in_review_slice(r.get("pilot_player_guess") or "", review_players)]

    def sort_key(r: Dict[str, Any]) -> str:
        return (r.get("fetched_at") or r.get("item_id") or "")[:64]

    slice_rows.sort(key=sort_key, reverse=True)

    slice_path = out_dir / "review_slice.csv"
    with slice_path.open("w", encoding="utf-8", newline="") as fw:
        w = csv.DictWriter(fw, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in slice_rows:
            w.writerow(r)

    st: Counter[str] = Counter()
    for r in rows_out:
        st[r.get("pilot_player_status") or ""] += 1
    base_yes = sum(1 for r in rows_out if r.get("pilot_is_likely_base") == "1")

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
        f"- **review_slice rows (BD-1..10 players):** {len(slice_rows)}",
        "",
        "## Outputs",
        "",
        f"- `{full_path.name}` — full scored CSV",
        f"- `{slice_path.name}` — BD-1..10 player slice, newest-first",
        "",
    ]
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

    return full_path, slice_path, summary_path


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
