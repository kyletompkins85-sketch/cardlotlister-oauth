"""
Title-only → **player**, **card type**, **predicted all-in price** (AutoGluon on pairwise ranks).

Composes :func:`cardmatch.listing_classification.classify_listing` with the same pairwise rank
CSVs and ``agModels`` directory used by ``scripts/cardmatch/train_bowman_rank_price_autogluon.py``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

from cardmatch.card_type import display_card_type_for_review, row_excluded_from_listing_counts, row_primary_card_type
from cardmatch.listing_classification import ChecklistPath, pilot_result_to_scored_row
from cardmatch.pairwise_price_rankings import _norm
from cardmatch.pilot import match_pilot
from cardmatch.player_index import load_bowman_draft_players
from cardmatch.types import PlayerStatus

PathLike = Union[str, Path]

try:
    import pandas as pd
    from autogluon.tabular import TabularPredictor  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    pd = None  # type: ignore[assignment]
    TabularPredictor = None  # type: ignore[misc,assignment]


def _load_rank_map(path: PathLike, name_col: str, rank_col: str = "rank") -> Dict[str, int]:
    out: Dict[str, int] = {}
    p = Path(path)
    with p.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            k = _norm(row.get(name_col, "") or "")
            if not k:
                continue
            try:
                out[k] = int(float(row.get(rank_col, "")))
            except (TypeError, ValueError):
                continue
    return out


def _median_rank(rank_map: Dict[str, int]) -> float:
    if not rank_map:
        return 1.0
    vals = sorted(rank_map.values())
    mid = len(vals) // 2
    if len(vals) % 2:
        return float(vals[mid])
    return (vals[mid - 1] + vals[mid]) / 2.0


def _row_eligible_for_rank_price_prediction(row: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Same structural rules as :func:`cardmatch.bowman_pilot_triples.bowman_pilot_row_to_triple`
    except listing price is not required (title-only inference).
    """
    player = _norm(row.get("pilot_player_guess") or "")
    if not player:
        return False, "missing_player"
    ct = row_primary_card_type(row)
    if not (ct or "").strip():
        return False, "missing_card_type"
    if row_excluded_from_listing_counts(row, ct):
        return False, "excluded_listing"
    ctn = _norm(ct)
    if not ctn or "," in ctn:
        return False, "invalid_card_type"
    return True, None


@dataclass(frozen=True)
class BowmanTitlePricePrediction:
    """Result of :func:`predict_bowman_price_from_title`."""

    title: str
    player: str
    card_type: str
    predicted_price: Optional[float]
    excluded: bool
    exclude_reason: Optional[str]
    player_status: PlayerStatus
    player_score: float
    matcher_version: str


def predict_bowman_price_from_title(
    title: str,
    *,
    player_rankings_csv: PathLike,
    card_type_rankings_csv: PathLike,
    autogluon_model_dir: PathLike,
    checklist: Optional[ChecklistPath] = None,
) -> BowmanTitlePricePrediction:
    """
    Classify **title** → player + pilot row, then predict all-in price from pairwise ranks + AutoGluon.

    **Artifacts** (keep versioned together): ``player_rankings_csv`` and ``card_type_rankings_csv``
    from the same pairwise run as training, plus ``autogluon_model_dir`` (``agModels``).
    """
    title = (title or "").strip()
    n, idx = load_bowman_draft_players(Path(checklist)) if checklist is not None else load_bowman_draft_players()
    pr = match_pilot(title, n, idx)
    row = pilot_result_to_scored_row(title, pr)
    card_type_display = display_card_type_for_review(row)

    ok, reason = _row_eligible_for_rank_price_prediction(row)
    if not ok:
        return BowmanTitlePricePrediction(
            title=title,
            player=pr.player_guess or "",
            card_type=card_type_display,
            predicted_price=None,
            excluded=True,
            exclude_reason=reason,
            player_status=pr.player_status,
            player_score=pr.player_score,
            matcher_version=pr.matcher_version,
        )

    pl_map = _load_rank_map(player_rankings_csv, "player", "rank")
    ct_map = _load_rank_map(card_type_rankings_csv, "card_type", "rank")
    pl_med = _median_rank(pl_map)
    ct_med = _median_rank(ct_map)

    pk = _norm(pr.player_guess or "")
    ct_key = _norm(row_primary_card_type(row))
    player_rank = float(pl_map.get(pk, pl_med))
    card_type_rank = float(ct_map.get(ct_key, ct_med))

    if TabularPredictor is None or pd is None:
        raise ImportError(
            "predict_bowman_price_from_title requires autogluon.tabular and pandas; "
            "install e.g. from scripts/cardmatch/requirements-bowman-autogluon.txt"
        )

    # Trained artifacts may be older than the installed autogluon.tabular; allow load when only minor version differs.
    predictor = TabularPredictor.load(
        str(Path(autogluon_model_dir)),
        require_version_match=False,
    )
    feat = pd.DataFrame([{"player_rank": player_rank, "card_type_rank": card_type_rank}])
    pred = predictor.predict(feat)
    if hasattr(pred, "iloc"):
        val = float(pred.iloc[0])
    elif hasattr(pred, "__iter__") and not isinstance(pred, (str, bytes)):
        val = float(list(pred)[0])
    else:
        val = float(pred)

    return BowmanTitlePricePrediction(
        title=title,
        player=pr.player_guess or "",
        card_type=card_type_display,
        predicted_price=val,
        excluded=False,
        exclude_reason=None,
        player_status=pr.player_status,
        player_score=pr.player_score,
        matcher_version=pr.matcher_version,
    )
