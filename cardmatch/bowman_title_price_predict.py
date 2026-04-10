"""
Title-only → **player**, **card type**, **predicted all-in price** (AutoGluon on pairwise ranks).

Composes :func:`cardmatch.listing_classification.classify_listing` with the same pairwise rank
CSVs and ``agModels`` directory used by ``scripts/cardmatch/train_bowman_rank_price_autogluon.py``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from cardmatch.card_type import display_card_type_for_review, row_excluded_from_listing_counts, row_primary_card_type
from cardmatch.listing_classification import ChecklistPath, pilot_result_to_scored_row
from cardmatch.pairwise_price_rankings import _norm
from cardmatch.pilot import match_pilot
from cardmatch.player_index import load_bowman_draft_players
from cardmatch.types import MATCHER_VERSION, PilotResult, PlayerStatus

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
    batch_item_error: Optional[str] = None


@dataclass(frozen=True)
class _PendingAG:
    """Eligible row waiting for a batched AutoGluon ``predict``."""

    index: int
    title: str
    pr: PilotResult
    card_type_display: str
    player_rank: float
    card_type_rank: float


def _predictor_predict_values(feat: Any) -> List[float]:
    """Normalize AutoGluon ``predict`` output to a list of floats (one per row)."""
    if hasattr(feat, "tolist"):
        raw = feat.tolist()
        if raw and isinstance(raw[0], (list, tuple)):
            return [float(x[0]) for x in raw]
        return [float(x) for x in raw]
    if hasattr(feat, "iloc"):
        return [float(feat.iloc[i]) for i in range(len(feat))]
    if hasattr(feat, "__iter__") and not isinstance(feat, (str, bytes)):
        return [float(x) for x in feat]
    return [float(feat)]


def predict_bowman_prices_from_titles(
    titles: List[str],
    *,
    player_rankings_csv: PathLike,
    card_type_rankings_csv: PathLike,
    autogluon_model_dir: PathLike,
    checklist: Optional[ChecklistPath] = None,
) -> List[BowmanTitlePricePrediction]:
    """
    Same as :func:`predict_bowman_price_from_title` but for many titles: loads rank CSVs and
    ``TabularPredictor`` at most once and runs a single ``predict`` call for all eligible rows.
    """
    n, idx = load_bowman_draft_players(Path(checklist)) if checklist is not None else load_bowman_draft_players()
    pl_map = _load_rank_map(player_rankings_csv, "player", "rank")
    ct_map = _load_rank_map(card_type_rankings_csv, "card_type", "rank")
    pl_med = _median_rank(pl_map)
    ct_med = _median_rank(ct_map)

    results: List[Optional[BowmanTitlePricePrediction]] = [None] * len(titles)
    pending: List[_PendingAG] = []

    for i, raw in enumerate(titles):
        title = (raw or "").strip()
        try:
            pr = match_pilot(title, n, idx)
            row = pilot_result_to_scored_row(title, pr)
            card_type_display = display_card_type_for_review(row)

            ok, reason = _row_eligible_for_rank_price_prediction(row)
            if not ok:
                results[i] = BowmanTitlePricePrediction(
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
                continue

            pk = _norm(pr.player_guess or "")
            ct_key = _norm(row_primary_card_type(row))
            player_rank = float(pl_map.get(pk, pl_med))
            card_type_rank = float(ct_map.get(ct_key, ct_med))
            pending.append(
                _PendingAG(
                    index=i,
                    title=title,
                    pr=pr,
                    card_type_display=card_type_display,
                    player_rank=player_rank,
                    card_type_rank=card_type_rank,
                )
            )
        except Exception as e:  # pragma: no cover - defensive per-title
            results[i] = BowmanTitlePricePrediction(
                title=title,
                player="",
                card_type="",
                predicted_price=None,
                excluded=True,
                exclude_reason="processing_error",
                player_status="unknown",
                player_score=0.0,
                matcher_version=MATCHER_VERSION,
                batch_item_error=str(e)[:800],
            )

    if pending:
        if TabularPredictor is None or pd is None:
            raise ImportError(
                "predict_bowman_prices_from_titles requires autogluon.tabular and pandas; "
                "install e.g. from scripts/cardmatch/requirements-bowman-autogluon.txt"
            )
        predictor = TabularPredictor.load(
            str(Path(autogluon_model_dir)),
            require_version_match=False,
            require_py_version_match=False,
        )
        feat = pd.DataFrame(
            [{"player_rank": p.player_rank, "card_type_rank": p.card_type_rank} for p in pending]
        )
        pred = predictor.predict(feat)
        vals = _predictor_predict_values(pred)
        if len(vals) != len(pending):
            raise RuntimeError(
                f"AutoGluon predict length mismatch: got {len(vals)} for {len(pending)} pending rows"
            )
        for p, val in zip(pending, vals):
            results[p.index] = BowmanTitlePricePrediction(
                title=p.title,
                player=p.pr.player_guess or "",
                card_type=p.card_type_display,
                predicted_price=float(val),
                excluded=False,
                exclude_reason=None,
                player_status=p.pr.player_status,
                player_score=p.pr.player_score,
                matcher_version=p.pr.matcher_version,
            )

    for j, r in enumerate(results):
        if r is None:
            raise RuntimeError(f"internal: missing result at index {j}")

    return results  # type: ignore[return-value]


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
    return predict_bowman_prices_from_titles(
        [title],
        player_rankings_csv=player_rankings_csv,
        card_type_rankings_csv=card_type_rankings_csv,
        autogluon_model_dir=autogluon_model_dir,
        checklist=checklist,
    )[0]
