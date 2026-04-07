"""
Build (player, card_type, all_in_price) rows from Bowman pilot-scored listing dicts.

``all_in`` = listing ``price`` + ``shipping_cost`` (missing shipping treated as 0).
``card_type`` uses the same taxonomy as review exports: :func:`cardmatch.card_type.row_primary_card_type`.
Rows excluded from listing-count aggregates (lot, pick/set, complete set, presale, graded, etc.) are
skipped — same rules as :func:`cardmatch.card_type.row_excluded_from_listing_counts`.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from cardmatch.card_type import row_excluded_from_listing_counts, row_primary_card_type

from cardmatch.pairwise_price_rankings import _norm, _to_float

Triple = Tuple[str, str, float]


def bowman_all_in_price(row: Dict[str, Any]) -> Optional[float]:
    """Listing price plus shipping (all-in)."""
    p = _to_float(row.get("price"))
    if p is None:
        return None
    s = _to_float(row.get("shipping_cost"))
    return float(p) + (float(s) if s is not None else 0.0)


def bowman_pilot_row_to_triple(row: Dict[str, Any]) -> Optional[Triple]:
    """
    One pilot-scored CSV row -> (pilot_player_guess, primary card type, all_in_price).

    Returns None if player missing, price missing, or card type cannot be derived.
    """
    player = _norm(row.get("pilot_player_guess") or "")
    if not player:
        return None
    all_in = bowman_all_in_price(row)
    if all_in is None:
        return None
    ct = row_primary_card_type(row)
    if not (ct or "").strip():
        return None
    if row_excluded_from_listing_counts(row, ct):
        return None
    ctn = _norm(ct)
    if not ctn or "," in ctn:
        return None
    return (player, ctn, float(all_in))


def bowman_pilot_rows_to_ranking_triples(rows: Iterable[Dict[str, Any]]) -> List[Triple]:
    """Filter iterable of pilot rows to valid triples for :mod:`cardmatch.pairwise_price_rankings`."""
    out: List[Triple] = []
    for row in rows:
        t = bowman_pilot_row_to_triple(row)
        if t is not None:
            out.append(t)
    return out
