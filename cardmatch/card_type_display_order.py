"""
Card type **display order** for UI / API: **1 = cheapest** (lowest typical price tier), higher = more expensive.

The committed CSV is the source of truth for ordering. Baseline values are derived from the pairwise
export (``rank`` 1 = wins expensive duels most often) via :func:`pairwise_rank_to_display_order`.
Rows use full canonical ``card_type`` strings (including print runs). Bare ``Bowman Draft Night /99``-style
rows are omitted from the CSV (they share a tier with ``Bowman Draft Night``); use
:func:`resolve_display_order` for lookup. You may edit ``display_order`` in the CSV to reorder.
Optional JSON overrides merge on top.

Environment (optional):

- ``BOWMAN_CARD_TYPE_DISPLAY_ORDER_CSV`` — path to the CSV (default: ``cardmatch/card_type_display_order.csv``).
- ``BOWMAN_CARD_TYPE_DISPLAY_ORDER_OVERRIDES_JSON`` — path to overrides JSON (default:
  ``cardmatch/card_type_display_order_overrides.json``).
"""

from __future__ import annotations

import csv
import json
import os
import re
import statistics
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple, Union

from cardmatch.pairwise_price_rankings import _norm

PathLike = Union[str, Path]

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISPLAY_ORDER_CSV = _PACKAGE_DIR / "card_type_display_order.csv"
DEFAULT_OVERRIDES_JSON = _PACKAGE_DIR / "card_type_display_order_overrides.json"
DEFAULT_PAIRWISE_CARD_TYPE_RANKINGS_CSV = (
    _REPO_ROOT
    / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/bowman_pairwise_card_type_rankings_with_listings.csv"
)


def pairwise_rank_to_display_order(pairwise_rank: int, *, max_pairwise_rank: int) -> int:
    """
    Map pairwise ``rank`` (1 = most expensive in duel sim) to ``display_order`` (1 = cheapest).

    ``display_order = max_pairwise_rank - pairwise_rank + 1``.
    """
    return int(max_pairwise_rank) - int(pairwise_rank) + 1


def load_pairwise_rank_column(
    pairwise_csv: PathLike, *, name_col: str = "card_type", rank_col: str = "rank"
) -> Tuple[Dict[str, int], int]:
    """
    Load ``card_type -> pairwise rank`` and return ``(map, max_rank)``.
    """
    p = Path(pairwise_csv)
    out: Dict[str, int] = {}
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
    if not out:
        return out, 0
    mx = max(out.values())
    return out, mx


def iter_pairwise_lookup_keys(card_type: str) -> Iterator[str]:
    """
    Yield candidates to match ``card_type`` against the pairwise ``card_type`` column.

    Order: exact string, then (if present) the same without `` · Auto``, then repeatedly strip a
    trailing `` /N`` print-run suffix.
    """
    k = _norm(card_type)
    if not k:
        return
    queue: List[str] = [k]
    if k.endswith(" · Auto"):
        k0 = k[: -len(" · Auto")].strip()
        if k0:
            queue.append(k0)
    seen: Set[str] = set()
    i = 0
    while i < len(queue):
        cur = queue[i]
        i += 1
        if not cur or cur in seen:
            continue
        seen.add(cur)
        yield cur
        m = re.match(r"^(.*?)\s+/\d+\s*$", cur)
        if m:
            nx = m.group(1).strip()
            if nx and nx not in seen:
                queue.append(nx)


def is_bare_product_line_print_run_only(card_type: str) -> bool:
    """
    True for ``<insert line> /N`` or ``<insert line> /N · Auto`` with no `` · Color · …`` segment.
    """
    k = _norm(card_type)
    if k.endswith(" · Auto"):
        k = k[: -len(" · Auto")].strip()
    if " · " in k:
        return False
    return bool(
        re.match(
            r"^(Bowman Draft Night|Bowman In Action|Prized Prospects) /\d+\s*$",
            k,
        )
    )


def should_omit_display_order_row(
    card_type: str, rank_match: str, matched_key: str
) -> bool:
    """
    Omit bare ``Product /N`` rows from the committed table when they only inferred from the
    generic product line, so the file foregrounds color/parallel names.
    """
    if rank_match != "inferred":
        return False
    if matched_key not in (
        "Bowman Draft Night",
        "Bowman In Action",
        "Prized Prospects",
    ):
        return False
    return is_bare_product_line_print_run_only(card_type)


def lookup_pairwise_rank_for_taxonomy(
    card_type: str,
    pairwise_ranks: Dict[str, int],
) -> Tuple[int, str, str]:
    """
    Resolve a canonical card type to a pairwise ``rank``.

    Returns ``(pairwise_rank, rank_match, matched_key)`` where ``rank_match`` is
    ``exact``, ``inferred``, or ``fallback`` (median rank when nothing matches).
    """
    if not pairwise_ranks:
        return 1, "fallback", ""
    k = _norm(card_type)
    if k in pairwise_ranks:
        return pairwise_ranks[k], "exact", k
    for cand in iter_pairwise_lookup_keys(card_type):
        if cand in pairwise_ranks:
            return pairwise_ranks[cand], "inferred", cand
    fb = int(round(statistics.median(list(pairwise_ranks.values()))))
    return fb, "fallback", ""


def load_card_types_from_listing_counts_csv(path: PathLike) -> List[str]:
    """``card_type`` column from ``listing_counts_by_card_type.csv``."""
    p = Path(path)
    out: List[str] = []
    with p.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or "card_type" not in r.fieldnames:
            raise ValueError(f"CSV must have card_type column: {p}")
        for row in r:
            ct = _norm(row.get("card_type", "") or "")
            if ct:
                out.append(ct)
    return out


def load_display_order_csv(path: PathLike) -> Dict[str, int]:
    """
    Load ``card_type -> display_order`` from CSV. Expected columns: ``card_type``, ``display_order``.
    """
    p = Path(path)
    out: Dict[str, int] = {}
    with p.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or "card_type" not in r.fieldnames:
            raise ValueError(f"CSV must have card_type column: {p}")
        if "display_order" not in r.fieldnames:
            raise ValueError(f"CSV must have display_order column: {p}")
        for row in r:
            k = _norm(row.get("card_type", "") or "")
            if not k:
                continue
            try:
                out[k] = int(float(row.get("display_order", "")))
            except (TypeError, ValueError):
                continue
    return out


def load_overrides_json(path: PathLike) -> Dict[str, int]:
    """
    Load optional overrides: ``{"overrides": {"Card Type · Name": 42}}`` (1 = cheapest).
    Missing file returns ``{}``.
    """
    p = Path(path)
    if not p.is_file():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    o = raw.get("overrides")
    if not isinstance(o, dict):
        return {}
    out: Dict[str, int] = {}
    for k, v in o.items():
        nk = _norm(str(k))
        if not nk:
            continue
        try:
            out[nk] = int(v)
        except (TypeError, ValueError):
            continue
    return out


def merge_display_orders(
    base: Dict[str, int], overrides: Dict[str, int]
) -> Dict[str, int]:
    """Copy ``base`` and apply ``overrides`` (override wins)."""
    out = dict(base)
    out.update(overrides)
    return out


def resolve_display_order_paths() -> Tuple[Path, Path]:
    """Paths from env or defaults."""
    csv_p = os.environ.get("BOWMAN_CARD_TYPE_DISPLAY_ORDER_CSV")
    ovr_p = os.environ.get("BOWMAN_CARD_TYPE_DISPLAY_ORDER_OVERRIDES_JSON")
    c = Path(csv_p) if csv_p else DEFAULT_DISPLAY_ORDER_CSV
    o = Path(ovr_p) if ovr_p else DEFAULT_OVERRIDES_JSON
    return c, o


def load_merged_display_order(
    *,
    csv_path: Optional[PathLike] = None,
    overrides_path: Optional[PathLike] = None,
) -> Dict[str, int]:
    """
    Load CSV + optional JSON overrides. Same keys as :func:`load_display_order_csv` after merge.
    """
    c = Path(csv_path) if csv_path else resolve_display_order_paths()[0]
    o = Path(overrides_path) if overrides_path else resolve_display_order_paths()[1]
    base = load_display_order_csv(c)
    return merge_display_orders(base, load_overrides_json(o))


def _pairwise_ct_csv_for_inference() -> Path:
    p = os.environ.get("BOWMAN_CARD_TYPE_RANKINGS_CSV")
    if p:
        return Path(p)
    return DEFAULT_PAIRWISE_CARD_TYPE_RANKINGS_CSV


def resolve_display_order(
    card_type: str,
    merged: Dict[str, int],
    *,
    pairwise_card_type_csv: Optional[PathLike] = None,
) -> Optional[int]:
    """
    Return ``display_order`` for ``card_type``: use the merged map when present; otherwise derive
    from the pairwise rankings file (same inversion as the CSV). Use this when the table omits
    redundant bare ``Product /N`` rows.
    """
    k = _norm(card_type or "")
    if not k:
        return None
    if k in merged:
        return merged[k]
    pc = Path(pairwise_card_type_csv) if pairwise_card_type_csv else _pairwise_ct_csv_for_inference()
    ct_map, max_r = load_pairwise_rank_column(pc)
    if not ct_map or max_r <= 0:
        return None
    pr, _, _ = lookup_pairwise_rank_for_taxonomy(k, ct_map)
    return pairwise_rank_to_display_order(pr, max_pairwise_rank=max_r)


def display_order_for_card_type(
    card_type: str,
    merged: Dict[str, int],
    *,
    fallback: Optional[int] = None,
    pairwise_card_type_csv: Optional[PathLike] = None,
    infer_missing: bool = False,
) -> Optional[int]:
    """
    Normalized lookup. With ``infer_missing=True``, missing keys use :func:`resolve_display_order`
    (pairwise file); otherwise returns ``fallback``.
    """
    k = _norm(card_type or "")
    if not k:
        return fallback
    if k in merged:
        return merged[k]
    if infer_missing:
        r = resolve_display_order(k, merged, pairwise_card_type_csv=pairwise_card_type_csv)
        if r is not None:
            return r
    return fallback
