"""
EBay listing title → player guess + primary card type (for ingestion / scoring pipelines).

**Why this module exists:** Product flows that **ingest listings** and store or score them need a
single call that takes the **listing title** (the same text as on eBay) and returns a
**player** + **card_type** pair aligned with Cardmatch pilot outputs. This wraps
`match_pilot` and the same scored-row fields + `display_card_type_for_review` used in
`cardmatch.pipeline` when building `pilot_scored_full.csv` / review exports — so batch jobs
and interactive classification stay consistent.

**Primary API:** ``classify_listing``, ``classify_listings``. See ``cardmatch/README.md`` (section
**Ingestion / scoring from eBay listing titles**) for intent, defaults, and batch tips.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from cardmatch.card_type import display_card_type_for_review
from cardmatch.pilot import match_pilot
from cardmatch.player_index import default_checklist_path, load_bowman_draft_players
from cardmatch.types import PilotResult, PlayerStatus

ChecklistPath = Union[Path, str]


@dataclass(frozen=True)
class ListingClassification:
    """One listing title: guessed player plus canonical primary `card_type` string."""

    title: str
    player: str
    player_status: PlayerStatus
    player_score: float
    card_type: str
    matcher_version: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


def pilot_result_to_scored_row(title: str, pr: PilotResult) -> Dict[str, Any]:
    """
    Same pilot_* columns the batch pipeline writes before `display_card_type_for_review` /
    `row_primary_card_type`.
    """
    return {
        "title": title,
        "pilot_player_guess": pr.player_guess,
        "pilot_player_score": f"{pr.player_score:.2f}",
        "pilot_player_status": pr.player_status,
        "pilot_is_likely_base": "1" if pr.is_likely_base else "0",
        "pilot_is_graded": "1" if pr.is_graded else "0",
        "pilot_is_lot": "1" if pr.is_lot else "0",
        "pilot_is_draft_night": "1" if pr.is_draft_night else "0",
        "pilot_is_chrome": "1" if pr.is_chrome else "0",
        "pilot_is_orange_border": "1" if pr.is_orange_border else "0",
        "pilot_is_likely_chrome_base": "1" if pr.is_likely_chrome_base else "0",
        "pilot_is_snack_pack": "1" if pr.is_snack_pack else "0",
        "pilot_is_axis": "1" if pr.is_axis else "0",
        "pilot_reason_codes": json.dumps(pr.reason_codes),
        "matcher_version": pr.matcher_version,
    }


def _resolve_player_index(
    names: Optional[List[str]],
    last_index: Optional[Dict[str, List[int]]],
    checklist: Optional[ChecklistPath],
) -> Tuple[List[str], Dict[str, List[int]]]:
    if names is not None and last_index is not None:
        return names, last_index
    if names is not None or last_index is not None:
        raise ValueError("Pass both names and last_index together, or omit both to load from checklist.")
    path = Path(checklist) if checklist is not None else default_checklist_path()
    return load_bowman_draft_players(path)


def classify_listing(
    title: str,
    *,
    names: Optional[List[str]] = None,
    last_index: Optional[Dict[str, List[int]]] = None,
    checklist: Optional[ChecklistPath] = None,
) -> ListingClassification:
    """
    Classify a single eBay-style listing title: Bowman Draft player guess + primary card type label.

    **Checklist:** default is `data/checklists/normalized/2025_Bowman_Draft_Normalized.csv` under the
    repo root. Pass ``checklist=`` to override, or precompute ``names`` / ``last_index`` once and
    reuse (recommended for many titles; see :func:`classify_listings`).
    """
    n, idx = _resolve_player_index(names, last_index, checklist)
    return _classify_listing_with_index(title, n, idx)


def _classify_listing_with_index(
    title: str,
    names: List[str],
    last_index: Dict[str, List[int]],
) -> ListingClassification:
    pr = match_pilot(title, names, last_index)
    row = pilot_result_to_scored_row(title, pr)
    card_type = display_card_type_for_review(row)
    return ListingClassification(
        title=title,
        player=pr.player_guess,
        player_status=pr.player_status,
        player_score=pr.player_score,
        card_type=card_type,
        matcher_version=pr.matcher_version,
        reason_codes=tuple(pr.reason_codes),
    )


def classify_listings(
    titles: Iterable[str],
    *,
    names: Optional[List[str]] = None,
    last_index: Optional[Dict[str, List[int]]] = None,
    checklist: Optional[ChecklistPath] = None,
) -> List[ListingClassification]:
    """
    Classify many titles with a **single** checklist load (unless ``names`` / ``last_index`` are
    passed in).
    """
    n, idx = _resolve_player_index(names, last_index, checklist)
    return [_classify_listing_with_index(t, n, idx) for t in titles]
