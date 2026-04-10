"""
Batch observed-price flags: spread ratio (2nd cheapest / 1st cheapest per card type) and
inversion vs strictly worse card types (pairwise rank).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from cardmatch.pairwise_price_rankings import _norm


def spread_ratio_second_over_first(prices: Sequence[float]) -> Optional[float]:
    """
    Second-smallest / smallest among positive finite prices (same card type group).

    Ties at the bottom (two listings at the minimum) yield ratio 1.0.
    Returns ``None`` if fewer than two such prices.
    """
    good = sorted(p for p in prices if p > 0 and math.isfinite(p))
    if len(good) < 2:
        return None
    return good[1] / good[0]


def _rank_for_card_type(card_type_norm: str, ct_map: Mapping[str, int], ct_median: float) -> float:
    k = _norm(card_type_norm)
    if not k:
        return ct_median
    return float(ct_map.get(k, ct_median))


def cheaper_than_worse_tier_in_batch(
    price: float,
    card_type_norm: str,
    min_price_by_card_type: Mapping[str, float],
    ct_map: Mapping[str, int],
    ct_median: float,
) -> bool:
    """
    True iff ``price`` is strictly below the batch minimum price of some card type **W** that is
    strictly worse than this row's type **T** (``rank(W) > rank(T)`` in the pairwise export;
    rank 1 = best).
    Only types that appear in ``min_price_by_card_type`` participate as **W**.
    """
    if not (price > 0 and math.isfinite(price)):
        return False
    t_key = _norm(card_type_norm)
    if not t_key:
        return False
    rank_t = _rank_for_card_type(t_key, ct_map, ct_median)
    for w_key, min_w in min_price_by_card_type.items():
        wn = _norm(w_key)
        if not wn or wn == t_key:
            continue
        rank_w = _rank_for_card_type(wn, ct_map, ct_median)
        if rank_w > rank_t and price < min_w:
            return True
    return False


@dataclass(frozen=True)
class BatchFlagRow:
    """Per-index output from :func:`analyze_batch_observed_flags`."""

    spread_ratio: Optional[float]
    cheaper_than_worse_tier: Optional[bool]
    price_skip_reason: Optional[str]


def _valid_price(p: Optional[float]) -> Tuple[bool, Optional[str]]:
    if p is None:
        return False, "missing_listing_price"
    try:
        v = float(p)
    except (TypeError, ValueError):
        return False, "invalid_listing_price"
    if not math.isfinite(v):
        return False, "invalid_listing_price"
    if v <= 0:
        return False, "invalid_listing_price"
    return True, None


def analyze_batch_observed_flags(
    *,
    card_type_norm_by_index: Sequence[str],
    classification_excluded: Sequence[bool],
    classification_batch_error: Sequence[Optional[str]],
    listing_prices: Sequence[Optional[float]],
    ct_map: Mapping[str, int],
    ct_median: float,
    is_serial_listing: Sequence[Optional[bool]],
) -> List[BatchFlagRow]:
    """
    Compute spread ratio and inversion flag for each row index.

    Rows with classification excluded or batch processing error get ``None`` for both fields.
    Rows with invalid/missing price get ``None`` for both fields and a ``price_skip_reason``.

    **Inversion (``cheaper_than_worse_tier``):** only computed when ``is_serial_listing[i]``
    is ``True``. If ``False`` or ``None`` (unknown / not serial), the inversion field is ``None``
    (N/A — not applicable to non-serial listings).
    """
    n = len(card_type_norm_by_index)
    if not (
        len(classification_excluded) == n
        and len(classification_batch_error) == n
        and len(listing_prices) == n
        and len(is_serial_listing) == n
    ):
        raise ValueError("parallel sequences must have same length")

    # Group prices by card type for non-excluded rows with valid price
    by_ct: Dict[str, List[float]] = {}
    for i in range(n):
        if classification_excluded[i] or classification_batch_error[i]:
            continue
        ok, _ = _valid_price(listing_prices[i])
        if not ok:
            continue
        ct = _norm(card_type_norm_by_index[i])
        if not ct:
            continue
        by_ct.setdefault(ct, []).append(float(listing_prices[i]))

    ratio_by_ct: Dict[str, Optional[float]] = {ct: spread_ratio_second_over_first(vals) for ct, vals in by_ct.items()}

    min_price_by_ct: Dict[str, float] = {ct: min(vals) for ct, vals in by_ct.items()}

    out: List[BatchFlagRow] = []
    for i in range(n):
        if classification_batch_error[i]:
            out.append(
                BatchFlagRow(
                    spread_ratio=None,
                    cheaper_than_worse_tier=None,
                    price_skip_reason=None,
                )
            )
            continue
        if classification_excluded[i]:
            out.append(
                BatchFlagRow(
                    spread_ratio=None,
                    cheaper_than_worse_tier=None,
                    price_skip_reason=None,
                )
            )
            continue

        ok_price, price_reason = _valid_price(listing_prices[i])
        if not ok_price:
            out.append(
                BatchFlagRow(
                    spread_ratio=None,
                    cheaper_than_worse_tier=None,
                    price_skip_reason=price_reason,
                )
            )
            continue

        ct = _norm(card_type_norm_by_index[i])
        price = float(listing_prices[i])
        sr = ratio_by_ct.get(ct)
        if is_serial_listing[i] is True:
            inv: Optional[bool] = cheaper_than_worse_tier_in_batch(
                price,
                ct,
                min_price_by_ct,
                ct_map,
                ct_median,
            )
        else:
            inv = None
        out.append(
            BatchFlagRow(
                spread_ratio=sr,
                cheaper_than_worse_tier=inv,
                price_skip_reason=None,
            )
        )

    return out
