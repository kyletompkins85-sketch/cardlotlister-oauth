"""
Batch cohort stats for 2025 Bowman retail: group by player, then by (canonical card_type, serial),
then spread ratios vs 2nd/3rd cheapest in the same bucket (Draft-style min-price gate).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from cardmatch.bowman_2025_retail_combo_catalog import (
    canonical_card_type,
    card_type_sort_tier,
    combo_meta_for_cluster,
    serial_sort_tuple,
    sort_hint_tuple,
)
from cardmatch.bowman_batch_listing_flags import spread_ratio_second_over_first, spread_ratio_third_over_first
from cardmatch.pairwise_price_rankings import _norm
from cardmatch.bowman_2025_retail_steps import RetailApiContext, retail_steps_row_extensions


def _valid_price(p: Optional[float]) -> tuple[bool, Optional[str]]:
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


def _price_is_min_for_cluster(price: float, cluster_key: str, min_price_by_cluster: Mapping[str, float]) -> bool:
    m = min_price_by_cluster.get(cluster_key)
    if m is None:
        return False
    return math.isclose(price, m, rel_tol=0.0, abs_tol=1e-6)


def _player_group_key(explicit: str, matched_player: str, index: int) -> str:
    nk = _norm(explicit)
    if nk:
        return f"explicit:{nk}"
    inf = _norm(matched_player)
    if inf:
        return f"classified:{inf}"
    return f"unknown:{index}"


def _cluster_key(canonical_ct: str, serial: int) -> str:
    return f"{canonical_ct}\x1f{serial}"


def retail_card_type_for_api_grouping(
    eligible: bool,
    display_name: str,
    card_type_display: str,
    canonical_card_type: str,
    serial: int,
    matched_card_type_short: str,
) -> str:
    """
    Single string aligned with Draft ``POST /batch/observed-flags`` ``card_type`` usage: the app
    groups rows with ``Dictionary(grouping:by: \\.cardType)``. For retail, **serial** must be part
    of this string whenever it is not ``-1``, so ``Paper`` and ``Paper /399`` become distinct keys.
    """
    if not eligible:
        s = (matched_card_type_short or "").strip()
        if s:
            return s
        s = (display_name or "").strip() or (card_type_display or "").strip() or (canonical_card_type or "").strip()
        return s
    base = (
        (display_name or "").strip()
        or (card_type_display or "").strip()
        or (canonical_card_type or "").strip()
    )
    if not base:
        base = (matched_card_type_short or "").strip()
    if serial == -1:
        return base
    if serial > 0 and base:
        return f"{base} /{serial}"
    return base


def _eligible_for_spread(ext: Dict[str, str]) -> bool:
    if (ext.get("excluded") or "").strip() == "1":
        return False
    return (ext.get("match_status_after_step3") or "").strip() == "matched"


@dataclass(frozen=True)
class RetailBatchInputItem:
    title: str
    price: float
    id: Optional[str] = None
    player_key: Optional[str] = None


def analyze_retail_batch_deals(
    items: Sequence[RetailBatchInputItem],
    ctx: RetailApiContext,
    combo_index: Mapping[tuple[str, int], dict[str, object]],
) -> tuple[List[dict[str, Any]], List[dict[str, Any]]]:
    """
    Classify each item, compute spread ratios within (player_group, canonical card_type, serial).

    Returns ``(per_item_results, group_summaries)``.
    """
    extensions: List[Dict[str, str]] = []
    for it in items:
        extensions.append(retail_steps_row_extensions(it.title, ctx))

    n = len(items)
    cluster_keys: List[str] = []
    canonical_cts: List[str] = []
    serials: List[int] = []
    eligible: List[bool] = []
    for i, ext in enumerate(extensions):
        ok_elig = _eligible_for_spread(ext)
        eligible.append(ok_elig)
        if not ok_elig:
            cluster_keys.append("")
            canonical_cts.append("")
            serials.append(-999)
            continue
        short_ct = (ext.get("matched_card_type") or "").strip()
        cct = canonical_card_type(short_ct, ctx.ct_to_disp, ctx.disp_to_ct)
        try:
            ser_i = int((ext.get("serial_out_of") or "-1").strip() or "-1")
        except ValueError:
            ser_i = -1
        cluster_keys.append(_cluster_key(cct, ser_i))
        canonical_cts.append(cct)
        serials.append(ser_i)

    # Per-item results skeleton
    results: List[dict[str, Any]] = []
    for i, it in enumerate(items):
        ext = extensions[i]
        ok_p, pr_reason = _valid_price(it.price)
        cct, ser_i = canonical_cts[i], serials[i]
        sort_o, dn, ctd = (
            combo_meta_for_cluster(cct, ser_i, combo_index, ctx.ct_to_disp)
            if eligible[i] and cct
            else (None, "", "")
        )
        if eligible[i] and cct and sort_o is None:
            hint = sort_hint_tuple(cct, ser_i)
        else:
            hint = None

        short_mt = (ext.get("matched_card_type") or "").strip()
        ct_api = retail_card_type_for_api_grouping(
            eligible[i],
            dn,
            ctd,
            cct,
            ser_i,
            short_mt,
        )

        row: dict[str, Any] = {
            "title": it.title,
            "listing_price": it.price,
            "id": it.id,
            "player_key": it.player_key,
            # Draft observed-flags parity: one string the client groups/sorts by (includes /serial).
            "card_type": ct_api,
            "card_type_display_order": sort_o,
            "excluded": (ext.get("excluded") or "").strip() == "1",
            "exclusion_reason": ext.get("exclusion_reason") or None,
            "match_status": ext.get("match_status"),
            "match_status_after_step3": ext.get("match_status_after_step3"),
            "matched_card_number": ext.get("matched_card_number") or None,
            "matched_checklist_player": ext.get("matched_checklist_player") or None,
            "matched_card_type": ext.get("matched_card_type") or None,
            "canonical_card_type": cct if eligible[i] else None,
            "serial": ser_i if eligible[i] else None,
            "cluster_key": cluster_keys[i] if eligible[i] else None,
            "sort_order": sort_o,
            "display_name": dn or None,
            "card_type_display": ctd or None,
            "sort_hint": list(hint) if hint is not None else None,
            "player_group_key": _player_group_key(it.player_key or "", ext.get("matched_checklist_player") or "", i),
            "spread_ratio": None,
            "spread_ratio_third": None,
            "savings_vs_second_listing_pct": None,
            "price_skip_reason": pr_reason if not ok_p else None,
        }
        results.append(row)

    # Group indices by player_group then cluster
    by_pg: Dict[str, List[int]] = {}
    for i in range(n):
        gk = results[i]["player_group_key"]
        by_pg.setdefault(gk, []).append(i)

    group_summaries: List[dict[str, Any]] = []

    for gk, idxs in by_pg.items():
        by_cluster: Dict[str, List[int]] = {}
        for i in idxs:
            if not eligible[i]:
                continue
            ck = cluster_keys[i]
            if not ck:
                continue
            by_cluster.setdefault(ck, []).append(i)

        for ck, c_idxs in by_cluster.items():
            prices: List[float] = []
            for j in c_idxs:
                okp, _ = _valid_price(items[j].price)
                if okp:
                    prices.append(float(items[j].price))
            min_p = min(prices) if prices else None
            sorted_p = sorted(p for p in prices if p > 0 and math.isfinite(p))
            second_p = sorted_p[1] if len(sorted_p) >= 2 else None
            third_p = sorted_p[2] if len(sorted_p) >= 3 else None
            ratio2 = spread_ratio_second_over_first(sorted_p) if len(sorted_p) >= 2 else None
            ratio3 = spread_ratio_third_over_first(sorted_p) if len(sorted_p) >= 3 else None
            min_price_by = {ck: min_p} if min_p is not None else {}

            j0 = c_idxs[0]
            cct, ser_i = canonical_cts[j0], serials[j0]
            sort_o, dn, ctd = combo_meta_for_cluster(cct, ser_i, combo_index, ctx.ct_to_disp)
            short0 = (extensions[j0].get("matched_card_type") or "").strip()
            ct_grp = retail_card_type_for_api_grouping(True, dn, ctd, cct, ser_i, short0)

            group_summaries.append(
                {
                    "player_group_key": gk,
                    "cluster_key": ck,
                    "canonical_card_type": cct,
                    "serial": ser_i,
                    "sort_order": sort_o,
                    "card_type": ct_grp,
                    "card_type_display_order": sort_o,
                    "display_name": dn,
                    "card_type_display": ctd,
                    "item_indices": list(c_idxs),
                    "ids": [items[j].id for j in c_idxs],
                    "count": len(c_idxs),
                    "count_with_valid_price": len(sorted_p),
                    "min_price": min_p,
                    "second_min_price": second_p,
                    "third_min_price": third_p,
                    "spread_ratio_floor": ratio2,
                    "spread_ratio_third_floor": ratio3,
                }
            )

            for j in c_idxs:
                okp, _ = _valid_price(items[j].price)
                if not okp:
                    continue
                price = float(items[j].price)
                sr: Optional[float] = None
                sr3: Optional[float] = None
                sav: Optional[float] = None
                if ratio2 is not None and min_p is not None and _price_is_min_for_cluster(price, ck, min_price_by):
                    sr = ratio2
                    if second_p is not None and second_p > 0:
                        sav = (second_p - min_p) / second_p
                if ratio3 is not None and min_p is not None and _price_is_min_for_cluster(price, ck, min_price_by):
                    sr3 = ratio3
                results[j]["spread_ratio"] = sr
                results[j]["spread_ratio_third"] = sr3
                results[j]["savings_vs_second_listing_pct"] = sav

    # Sort groups for UI: sort_order then cluster key
    def _group_sort_key(g: dict[str, Any]) -> Tuple:
        so = g.get("sort_order")
        so_t = (0, int(so)) if isinstance(so, int) else (1, 10**9)
        cct = str(g.get("canonical_card_type") or "")
        ser = int(g.get("serial") or -999)
        hint = (card_type_sort_tier(cct), cct, serial_sort_tuple(ser))
        return (g.get("player_group_key") or "", so_t, hint)

    group_summaries.sort(key=_group_sort_key)

    return results, group_summaries
