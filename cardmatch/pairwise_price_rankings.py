"""
Monte Carlo pairwise price duels: rank card types (same player) and players (same card type).

Input rows are (player, card_type, all_in_price) per listing; optional seller/title for audit logs.
Default 50_000 iterations matches ``scripts/topps_update_2025/simulate_*_price_rankings.py``.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from collections import defaultdict

# (player, card_type, price, seller, title)
SimRow = Tuple[str, str, float, str, str]


def _norm(s: str) -> str:
    return " ".join((s or "").strip().split())


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        s = str(v).strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None


@dataclass(frozen=True)
class PairwiseEntityStats:
    """Wins/losses for one card type (CT sim) or one player (player sim)."""

    name: str
    wins: int
    losses: int
    win_rate: float
    avg_win_margin: float
    played: int


@dataclass
class MonteCarloCardTypeResult:
    """Same player, two different card types — which CT wins more expensive duels."""

    stats: List[PairwiseEntityStats]
    match_log: List[Dict[str, Any]] = field(default_factory=list)
    iterations_made: int = 0
    iterations_requested: int = 0
    rows_used: int = 0
    eligible_players: int = 0
    phase1_scored_duels: int = 0
    phase2_scored_duels: int = 0
    min_duels_per_card_type: Optional[int] = None


@dataclass
class MonteCarloPlayerResult:
    """Same card type, two different players — which player wins more expensive duels."""

    stats: List[PairwiseEntityStats]
    match_log: List[Dict[str, Any]] = field(default_factory=list)
    iterations_made: int = 0
    iterations_requested: int = 0
    rows_used: int = 0
    eligible_card_types: int = 0


@dataclass
class PairwiseMonteCarloRankings:
    """Both simulations; use when you want card-type and player rankings from one dataset."""

    same_player_card_types: MonteCarloCardTypeResult
    same_card_type_players: MonteCarloPlayerResult


def listing_triples_to_sim_rows(
    triples: Sequence[Tuple[str, str, float]],
    *,
    seller_default: str = "",
    title_default: str = "",
) -> List[SimRow]:
    """Expand (player, card_type, all_in) rows to internal sim rows (seller/title optional)."""
    out: List[SimRow] = []
    for p, ct, price in triples:
        pp = _norm(p)
        cct = _norm(ct)
        if not pp or not cct or "," in cct:
            continue
        out.append((pp, cct, float(price), seller_default, title_default))
    return out


def coerce_sim_rows(rows: Sequence[Tuple[Any, ...]]) -> List[SimRow]:
    """Accept (player, ct, price) or full SimRow; drop invalid rows (multi-CT, missing fields)."""
    out: List[SimRow] = []
    for r in rows:
        if len(r) == 3:
            p, ct, pr = r
            pp = _norm(str(p))
            cct = _norm(str(ct))
            if not pp or not cct or "," in cct:
                continue
            out.append((pp, cct, float(pr), "", ""))
        elif len(r) == 5:
            p, ct, pr, sl, tl = r
            pp = _norm(str(p))
            cct = _norm(str(ct))
            if not pp or not cct or "," in cct:
                continue
            out.append((pp, cct, float(pr), _norm(str(sl)), str(tl)))
        else:
            raise ValueError(f"Expected row of length 3 or 5, got {len(r)}")
    return out


def _stats_from_wins(
    wins: Dict[str, int],
    losses: Dict[str, int],
    played: Dict[str, int],
    margin_sum: Dict[str, float],
    names: List[str],
) -> List[PairwiseEntityStats]:
    stats: List[PairwiseEntityStats] = []
    for name in names:
        w = int(wins.get(name, 0))
        l = int(losses.get(name, 0))
        p = int(played.get(name, 0))
        denom = w + l
        win_rate = (w / denom) if denom > 0 else 0.0
        avg_margin = (margin_sum.get(name, 0.0) / w) if w > 0 else 0.0
        stats.append(
            PairwiseEntityStats(
                name=name,
                wins=w,
                losses=l,
                win_rate=round(win_rate, 6),
                avg_win_margin=round(avg_margin, 4),
                played=p,
            )
        )
    return stats


def _ct_duel_same_player_from_anchor(
    rows: List[SimRow],
    a_idx: int,
    by_player_ct: Dict[Tuple[str, str], List[int]],
    player_cts: Dict[str, List[str]],
    wins: Dict[str, int],
    losses: Dict[str, int],
    played: Dict[str, int],
    margin_sum: Dict[str, float],
    match_log: List[Dict[str, Any]],
    max_match_log: int,
) -> str:
    """
    One same-player cross-type duel anchored at ``a_idx``. Updates ``played`` for both CTs even on ties.

    Returns ``"scored"`` (win/loss recorded), ``"tie"``, or ``"skip"`` (invalid anchor).
    """
    a_player, a_ct, a_price, a_seller, a_title = rows[a_idx]

    if a_player not in player_cts:
        return "skip"
    cts = player_cts[a_player]
    if len(cts) < 2:
        return "skip"
    other_cts = [c for c in cts if c != a_ct]
    if not other_cts:
        return "skip"
    b_ct = random.choice(other_cts)
    b_pool = by_player_ct.get((a_player, b_ct), [])
    if not b_pool:
        return "skip"
    b_idx = random.choice(b_pool)
    b_player, b_ct2, b_price, b_seller, b_title = rows[b_idx]
    if b_player != a_player or b_ct2 != b_ct:
        return "skip"

    played[a_ct] += 1
    played[b_ct] += 1

    if a_price == b_price:
        return "tie"

    if a_price > b_price:
        w_ct, l_ct = a_ct, b_ct
        w_price, l_price = a_price, b_price
        w_seller, w_title = a_seller, a_title
        l_seller, l_title = b_seller, b_title
    else:
        w_ct, l_ct = b_ct, a_ct
        w_price, l_price = b_price, a_price
        w_seller, w_title = b_seller, b_title
        l_seller, l_title = a_seller, a_title

    wins[w_ct] += 1
    losses[l_ct] += 1
    margin_sum[w_ct] += (w_price - l_price)

    if max_match_log > 0 and len(match_log) < max_match_log:
        match_log.append(
            {
                "player_name": a_player,
                "winner_ct": w_ct,
                "loser_ct": l_ct,
                "winner_price": round(w_price, 4),
                "loser_price": round(l_price, 4),
                "price_diff": round(w_price - l_price, 4),
                "winner_seller": w_seller,
                "winner_title": w_title,
                "loser_seller": l_seller,
                "loser_title": l_title,
            }
        )
    return "scored"


def run_monte_carlo_card_type_rankings_same_player(
    rows: List[SimRow],
    *,
    iterations: int = 50_000,
    min_duels_per_card_type: Optional[int] = None,
    seed: int = 42,
    max_match_log: int = 0,
) -> MonteCarloCardTypeResult:
    """
    For the same player, compare two listings with different card types; higher all-in wins.

    **Phase 1 (``iterations``):** uniform random anchor listing, same as legacy behavior — run until
    ``iterations`` **scored** (non-tie) duels are recorded.

    **Phase 2 (optional):** if ``min_duels_per_card_type`` is set, repeatedly pick a card type that
    still has ``played[ct]`` below that minimum (among types that can appear in any cross-type duel),
    choose a random eligible player who owns that type, anchor on that type, and duel against another
    of the player's types — until every such type has at least ``min_duels_per_card_type`` recorded
    duels (``played`` counts ties and scored).
    """
    iters = max(1, int(iterations))
    min_duels = int(min_duels_per_card_type) if min_duels_per_card_type is not None else None
    if min_duels is not None and min_duels < 1:
        raise ValueError("min_duels_per_card_type must be >= 1 when set")

    random.seed(int(seed))

    by_player: Dict[str, List[int]] = defaultdict(list)
    by_player_ct: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    for idx, (player, ct, price, _s, _t) in enumerate(rows):
        by_player[player].append(idx)
        by_player_ct[(player, ct)].append(idx)

    player_cts: Dict[str, List[str]] = {}
    eligible_players: List[str] = []
    for p, idxs in by_player.items():
        cts = sorted({rows[i][1] for i in idxs})
        if len(cts) >= 2:
            eligible_players.append(p)
            player_cts[p] = cts

    if not eligible_players:
        raise ValueError("No eligible players (need same player with 2+ different card types).")

    wins: Dict[str, int] = defaultdict(int)
    losses: Dict[str, int] = defaultdict(int)
    played: Dict[str, int] = defaultdict(int)
    margin_sum: Dict[str, float] = defaultdict(float)
    match_log: List[Dict[str, Any]] = []

    attempts = 0
    made = 0
    max_attempts = iters * 50

    while made < iters and attempts < max_attempts:
        attempts += 1
        a_idx = random.randrange(0, len(rows))
        out = _ct_duel_same_player_from_anchor(
            rows,
            a_idx,
            by_player_ct,
            player_cts,
            wins,
            losses,
            played,
            margin_sum,
            match_log,
            max_match_log,
        )
        if out == "scored":
            made += 1

    phase1_made = made

    phase2_made = 0
    if min_duels is not None:
        all_cts_in_data: set = set()
        for p in eligible_players:
            all_cts_in_data.update(player_cts[p])

        def _can_ct_appear_in_duel(ct: str) -> bool:
            return any(ct in player_cts[p] and len(player_cts[p]) >= 2 for p in eligible_players)

        def _needy_cts() -> List[str]:
            return sorted(ct for ct in all_cts_in_data if _can_ct_appear_in_duel(ct) and played[ct] < min_duels)

        p2_attempts = 0
        max_phase2_attempts = max(50_000_000, min_duels * len(all_cts_in_data) * 500)
        need = _needy_cts()
        while need and p2_attempts < max_phase2_attempts:
            p2_attempts += 1
            ct_under = random.choice(need)
            players_ok = [
                p for p in eligible_players if ct_under in player_cts[p] and len(player_cts[p]) >= 2
            ]
            if not players_ok:
                all_cts_in_data.discard(ct_under)
                need = _needy_cts()
                continue
            p_pick = random.choice(players_ok)
            anchor_pool = by_player_ct.get((p_pick, ct_under), [])
            if not anchor_pool:
                need = _needy_cts()
                continue
            a_idx = random.choice(anchor_pool)
            out = _ct_duel_same_player_from_anchor(
                rows,
                a_idx,
                by_player_ct,
                player_cts,
                wins,
                losses,
                played,
                margin_sum,
                match_log,
                max_match_log,
            )
            if out == "scored":
                phase2_made += 1
            need = _needy_cts()

    all_cts = sorted(set(list(wins.keys()) + list(losses.keys()) + list(played.keys())))
    stats = _stats_from_wins(wins, losses, played, margin_sum, all_cts)
    # Preserve legacy Topps CSV order: win_rate ascending, then total duels
    stats.sort(key=lambda s: (s.win_rate, s.wins + s.losses))

    total_scored = phase1_made + phase2_made

    return MonteCarloCardTypeResult(
        stats=stats,
        match_log=match_log,
        iterations_made=total_scored,
        iterations_requested=iters,
        rows_used=len(rows),
        eligible_players=len(eligible_players),
        phase1_scored_duels=phase1_made,
        phase2_scored_duels=phase2_made,
        min_duels_per_card_type=min_duels,
    )


def run_monte_carlo_player_rankings_same_card_type(
    rows: List[SimRow],
    *,
    iterations: int = 50_000,
    seed: int = 42,
    max_match_log: int = 0,
) -> MonteCarloPlayerResult:
    """Same card type, two different players; higher all-in price wins."""
    iters = max(1, int(iterations))
    random.seed(int(seed))

    by_ct: Dict[str, List[int]] = defaultdict(list)
    by_ct_player: Dict[Tuple[str, str], List[int]] = defaultdict(list)

    for idx, (player, ct, _price, _s, _t) in enumerate(rows):
        by_ct[ct].append(idx)
        by_ct_player[(ct, player)].append(idx)

    ct_players: Dict[str, List[str]] = {}
    eligible_cts: List[str] = []
    for ct, idxs in by_ct.items():
        players = sorted({rows[i][0] for i in idxs})
        if len(players) >= 2:
            eligible_cts.append(ct)
            ct_players[ct] = players

    if not eligible_cts:
        raise ValueError("No eligible card types (need a card type with 2+ different players).")

    wins: Dict[str, int] = defaultdict(int)
    losses: Dict[str, int] = defaultdict(int)
    played: Dict[str, int] = defaultdict(int)
    margin_sum: Dict[str, float] = defaultdict(float)
    match_log: List[Dict[str, Any]] = []

    attempts = 0
    made = 0
    max_attempts = iters * 50

    while made < iters and attempts < max_attempts:
        attempts += 1
        a_idx = random.randrange(0, len(rows))
        a_player, a_ct, a_price, a_seller, a_title = rows[a_idx]

        players_in_ct = ct_players.get(a_ct)
        if not players_in_ct or len(players_in_ct) < 2:
            continue
        other_players = [p for p in players_in_ct if p != a_player]
        if not other_players:
            continue
        b_player = random.choice(other_players)
        b_pool = by_ct_player.get((a_ct, b_player), [])
        if not b_pool:
            continue
        b_idx = random.choice(b_pool)
        b_player2, b_ct2, b_price, b_seller, b_title = rows[b_idx]
        if b_ct2 != a_ct or b_player2 != b_player:
            continue

        played[a_player] += 1
        played[b_player] += 1

        if a_price == b_price:
            continue

        if a_price > b_price:
            w_player, l_player = a_player, b_player
            w_price, l_price = a_price, b_price
            w_seller, w_title = a_seller, a_title
            l_seller, l_title = b_seller, b_title
        else:
            w_player, l_player = b_player, a_player
            w_price, l_price = b_price, a_price
            w_seller, w_title = b_seller, b_title
            l_seller, l_title = a_seller, a_title

        wins[w_player] += 1
        losses[l_player] += 1
        margin_sum[w_player] += (w_price - l_price)

        if max_match_log > 0 and len(match_log) < max_match_log:
            match_log.append(
                {
                    "CT_list": a_ct,
                    "winner_player": w_player,
                    "loser_player": l_player,
                    "winner_price": round(w_price, 4),
                    "loser_price": round(l_price, 4),
                    "price_diff": round(w_price - l_price, 4),
                    "winner_seller": w_seller,
                    "winner_title": w_title,
                    "loser_seller": l_seller,
                    "loser_title": l_title,
                }
            )
        made += 1

    players_all = sorted(set(list(wins.keys()) + list(losses.keys()) + list(played.keys())))
    stats = _stats_from_wins(wins, losses, played, margin_sum, players_all)
    stats.sort(key=lambda s: (s.win_rate, s.wins + s.losses), reverse=True)

    return MonteCarloPlayerResult(
        stats=stats,
        match_log=match_log,
        iterations_made=made,
        iterations_requested=iters,
        rows_used=len(rows),
        eligible_card_types=len(eligible_cts),
    )


def aggregate_listing_count_and_avg_price_by_player(rows: List[SimRow]) -> Dict[str, Tuple[int, float]]:
    """Per player: (listing_count, mean all-in price) across input rows."""
    sums: Dict[str, float] = defaultdict(float)
    counts: Dict[str, int] = defaultdict(int)
    for p, _ct, price, _s, _t in rows:
        sums[p] += float(price)
        counts[p] += 1
    return {p: (counts[p], sums[p] / counts[p]) for p in counts}


def aggregate_listing_count_and_avg_price_by_card_type(rows: List[SimRow]) -> Dict[str, Tuple[int, float]]:
    """Per card type: (listing_count, mean all-in price) across input rows."""
    sums: Dict[str, float] = defaultdict(float)
    counts: Dict[str, int] = defaultdict(int)
    for _p, ct, price, _s, _t in rows:
        sums[ct] += float(price)
        counts[ct] += 1
    return {ct: (counts[ct], sums[ct] / counts[ct]) for ct in counts}


def aggregate_listing_count_and_avg_price_by_player_for_card_type(
    rows: List[SimRow],
    *,
    card_type: str,
) -> Dict[str, Tuple[int, float]]:
    """
    Per player: (listing_count, mean all-in price) only for rows whose card type equals
    ``card_type`` after the same normalization as other sim rows (exact match on normalized CT).
    """
    want = _norm(card_type)
    if not want:
        return {}
    sums: Dict[str, float] = defaultdict(float)
    counts: Dict[str, int] = defaultdict(int)
    for p, ct, price, _s, _t in rows:
        if _norm(ct) != want:
            continue
        sums[p] += float(price)
        counts[p] += 1
    return {p: (counts[p], sums[p] / counts[p]) for p in counts}


def aggregate_listing_count_and_median_price_by_player_for_card_type(
    rows: List[SimRow],
    *,
    card_type: str,
) -> Dict[str, Tuple[int, float]]:
    """
    Per player: (listing_count, median all-in price) for rows whose card type equals ``card_type``
    (exact match on normalized CT). Median is less sensitive than the mean to a few mislabeled or
    outlier-priced listings sharing the same primary type.
    """
    want = _norm(card_type)
    if not want:
        return {}
    prices_by: Dict[str, List[float]] = defaultdict(list)
    for p, ct, price, _s, _t in rows:
        if _norm(ct) != want:
            continue
        prices_by[p].append(float(price))
    out: Dict[str, Tuple[int, float]] = {}
    for p, prices in prices_by.items():
        prices.sort()
        out[p] = (len(prices), float(statistics.median(prices)))
    return out


def build_ranking_export_rows(
    stats: List[PairwiseEntityStats],
    listing_by_name: Dict[str, Tuple[int, float]],
    *,
    name_field: str,
    descending_win_rate: bool = True,
) -> List[Dict[str, Any]]:
    """
    Attach listing_count + avg_listing_price; assign ``rank`` (1 = top by sort order).

    Sort: ``win_rate`` then total duels (``wins + losses``), then name — ``descending_win_rate``
    True means rank 1 = highest pairwise win rate (typical \"most expensive\" interpretation).
    """
    sorted_stats = sorted(
        stats,
        key=lambda s: (s.win_rate, s.wins + s.losses, s.name),
        reverse=descending_win_rate,
    )
    out: List[Dict[str, Any]] = []
    for i, s in enumerate(sorted_stats, start=1):
        lc, avg_p = listing_by_name.get(s.name, (0, 0.0))
        row: Dict[str, Any] = {
            "rank": i,
            name_field: s.name,
            "win_rate": s.win_rate,
            "wins": s.wins,
            "losses": s.losses,
            "avg_win_margin": s.avg_win_margin,
            "pairwise_duels_played": s.played,
            "listing_count": lc,
            "avg_listing_price": round(avg_p, 4) if lc else 0.0,
        }
        out.append(row)
    return out


def run_pairwise_monte_carlo_rankings(
    rows: Sequence[Tuple[Any, ...]],
    *,
    iterations: int = 50_000,
    card_type_base_iterations: Optional[int] = None,
    card_type_min_duels_per_type: Optional[int] = None,
    seed: int = 42,
    max_match_log: int = 0,
) -> PairwiseMonteCarloRankings:
    """
    Run both simulations on one dataset.

    Accepts either ``(player, card_type, all_in_price)`` triples (seller/title empty) or full
    ``SimRow`` tuples including seller and title for match logs.

    **Card-type simulation:** ``card_type_base_iterations`` defaults to ``iterations`` (phase 1 scored
    duels). Optional ``card_type_min_duels_per_type`` runs phase 2 until each duelable card type has at
    least that many ``played`` counts (see :func:`run_monte_carlo_card_type_rankings_same_player`).
    **Player simulation** always uses ``iterations`` scored duels.
    """
    if not rows:
        raise ValueError("rows is empty")
    sim_rows = coerce_sim_rows(rows)
    if len(sim_rows) < 2:
        raise ValueError("Not enough rows after filtering (need 2+ with player, card type, price).")

    ct_base = int(card_type_base_iterations) if card_type_base_iterations is not None else int(iterations)
    ct_res = run_monte_carlo_card_type_rankings_same_player(
        sim_rows,
        iterations=max(1, ct_base),
        min_duels_per_card_type=card_type_min_duels_per_type,
        seed=seed,
        max_match_log=max_match_log,
    )
    pl_res = run_monte_carlo_player_rankings_same_card_type(
        sim_rows, iterations=iterations, seed=seed, max_match_log=max_match_log
    )
    return PairwiseMonteCarloRankings(same_player_card_types=ct_res, same_card_type_players=pl_res)


# Re-export for scripts
__all__ = [
    "MonteCarloCardTypeResult",
    "MonteCarloPlayerResult",
    "PairwiseEntityStats",
    "PairwiseMonteCarloRankings",
    "SimRow",
    "aggregate_listing_count_and_avg_price_by_card_type",
    "aggregate_listing_count_and_avg_price_by_player",
    "aggregate_listing_count_and_avg_price_by_player_for_card_type",
    "aggregate_listing_count_and_median_price_by_player_for_card_type",
    "build_ranking_export_rows",
    "listing_triples_to_sim_rows",
    "run_monte_carlo_card_type_rankings_same_player",
    "run_monte_carlo_player_rankings_same_card_type",
    "run_pairwise_monte_carlo_rankings",
    "coerce_sim_rows",
]
