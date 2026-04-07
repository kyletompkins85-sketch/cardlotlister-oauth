from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

_BDC_NUM = re.compile(r"^BDC-(\d+)$", re.IGNORECASE)


def default_checklist_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[1]
    return root / "data" / "checklists" / "normalized" / "2025_Bowman_Draft_Normalized.csv"


def _clean_player_name(raw: str) -> str:
    return (raw or "").strip().rstrip(",").strip()


def load_bowman_draft_players(
    checklist_csv: Path | None = None,
) -> Tuple[List[str], Dict[str, List[int]]]:
    """
    Unique display names from checklist + last-token index (same strategy as scripts/topps_update_2025/classify_existing_listings_json.py).
    """
    path = checklist_csv or default_checklist_path()
    names: List[str] = []
    seen: set[str] = set()

    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or "player_name_raw" not in r.fieldnames:
            raise ValueError(f"Expected player_name_raw in {path}")
        for row in r:
            nm = _clean_player_name(row.get("player_name_raw") or "")
            if not nm or nm in seen:
                continue
            seen.add(nm)
            names.append(nm)

    from cardmatch.player_match import build_last_index

    last_index = build_last_index(names)
    return names, last_index


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
