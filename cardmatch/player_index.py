from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple


def default_checklist_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[1]
    return root / "data" / "checklists" / "normalized" / "2025_Bowman_Draft_Normalized.csv"


def _clean_player_name(raw: str) -> str:
    return (raw or "").strip().rstrip(",").strip()


def load_bowman_draft_players(
    checklist_csv: Path | None = None,
) -> Tuple[List[str], Dict[str, List[int]]]:
    """
    Unique display names from checklist + last-token index (same strategy as scripts/classify_existing_listings_json).
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
