from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Set


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


def load_review_config(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def row_in_review_slice(player_guess: str, review_players: Set[str]) -> bool:
    if not player_guess:
        return False
    return player_guess in review_players
