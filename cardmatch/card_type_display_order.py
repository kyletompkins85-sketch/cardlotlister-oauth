"""
Card type **display order** for UI / API: **1 = cheapest** (lowest typical price tier), higher = more expensive.

The committed CSV is the source of truth for ordering. Baseline values are derived from the pairwise
export (``rank`` 1 = wins expensive duels most often) via :func:`pairwise_rank_to_display_order`.
Rows use full canonical ``card_type`` strings (including print runs). The committed CSV keeps
**exact** pairwise keys only (listing-only types with no pairwise row resolve at runtime to ``999``).
Bare ``Bowman Draft Night /99``-style rows and **inferred** rows (e.g. ``… · Auto`` matched only
after stripping `` · Auto``) are omitted from the CSV; use :func:`resolve_display_order` for those
lookups. You may edit ``display_order`` in the CSV to reorder.
Optional JSON overrides merge on top.

When a type is missing from the merged map and has **no** pairwise match (even after
:func:`iter_pairwise_lookup_keys` stripping), :func:`resolve_display_order` assigns
``DISPLAY_ORDER_WHEN_PAIRWISE_UNKNOWN`` (``999``) so unknown tiers sort after
known ladder slots. The regen script writes **contiguous** ``display_order`` (1 … n) for normal rows;
types in ``DISPLAY_ORDER_ERROR_CARD_TYPES`` keep ``999``. With the default **preserve** mode, regen
keeps the CSV’s **existing line order** and only appends new types; it does not reshuffle your rows.

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
from pathlib import Path
from typing import Any, Dict, Iterator, List, MutableMapping, Optional, Set, Tuple, Union

from cardmatch.pairwise_price_rankings import _norm
from cardmatch.taxonomy import (
    canonical_display_order_lookup_key,
    insert_line_card_type_collapsed_for_display,
)

PathLike = Union[str, Path]

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISPLAY_ORDER_CSV = _PACKAGE_DIR / "card_type_display_order.csv"
DEFAULT_OVERRIDES_JSON = _PACKAGE_DIR / "card_type_display_order_overrides.json"
DEFAULT_PAIRWISE_CARD_TYPE_RANKINGS_CSV = (
    _REPO_ROOT
    / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/bowman_pairwise_card_type_rankings_with_listings.csv"
)

# Sort/UI: unknown card types (no pairwise key after candidate stripping) — not a real price tier.
DISPLAY_ORDER_WHEN_PAIRWISE_UNKNOWN = 999

# Hand-flagged taxonomy rows that should sort after the normal ladder in the committed CSV (same 999
# bucket as unknown tiers for UI ordering).
DISPLAY_ORDER_ERROR_CARD_TYPES = frozenset(
    {
        "Bowman In Action · Speckle /150",
        "Bowman In Action · Blue /150",
        # Erroneous Gold + Mini Diamond stack (classifier noise); keep at tail for review.
        "Bowman Draft Night · Gold /50 · Mini Diamond · Auto",
        "Bowman Draft Night · Auto · Gold /50 · Mini Diamond",
    }
)


def dense_renumber_display_order_column(
    rows: List[MutableMapping[str, Any]],
    *,
    sentinel: int = DISPLAY_ORDER_WHEN_PAIRWISE_UNKNOWN,
    error_card_types: Optional[frozenset[str]] = None,
) -> None:
    """
    Set ``display_order`` to **1 … n** in **current row list order** without reordering rows.

    Rows already at ``sentinel`` (``999``) or whose ``card_type`` is in ``error_card_types``
    (default: :data:`DISPLAY_ORDER_ERROR_CARD_TYPES`) keep ``sentinel``.
    """
    err_n = frozenset(
        _norm(x)
        for x in (
            error_card_types
            if error_card_types is not None
            else DISPLAY_ORDER_ERROR_CARD_TYPES
        )
    )
    n = 1
    for r in rows:
        nk = _norm(str(r.get("card_type", "") or ""))
        try:
            cur = int(float(r.get("display_order", 0) or 0))
        except (TypeError, ValueError):
            cur = 0
        if cur == sentinel or nk in err_n:
            r["display_order"] = sentinel
        else:
            r["display_order"] = n
            n += 1


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
    m = re.match(r"^(.+?) · Auto · (.+)$", k)
    if m:
        mid_strip = f"{m.group(1)} · {m.group(2)}".strip()
        if mid_strip:
            queue.append(mid_strip)
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
    # Omit exact pairwise rows that duplicate an explicit insert ladder label (bare ``/N``, Sparkle/150, …).
    nk = _norm(card_type)
    if rank_match == "exact" and insert_line_card_type_collapsed_for_display(nk) != nk:
        return True
    if rank_match != "inferred":
        return False
    if matched_key not in (
        "Bowman Draft Night",
        "Bowman In Action",
        "Prized Prospects",
    ):
        return False
    return is_bare_product_line_print_run_only(card_type)


def _legacy_trailing_auto_pairwise_key(k: str) -> str:
    """
    Pairwise exports may still use ``… · Parallel · Auto``; taxonomy uses ``… · Auto · Parallel``.
    Also ``Chrome /N · Auto`` vs ``Chrome · Auto /N``.
    """
    m = re.match(r"^(Chrome) · Auto (/\d+)$", k, re.I)
    if m:
        return f"{m.group(1)} {m.group(2)} · Auto".replace("  ", " ").strip()
    parts = k.split(" · ")
    if len(parts) < 3 or parts[1] != "Auto":
        return k
    return f"{parts[0]} · " + " · ".join(parts[2:]) + " · Auto"


def lookup_pairwise_rank_for_taxonomy(
    card_type: str,
    pairwise_ranks: Dict[str, int],
) -> Tuple[int, str, str]:
    """
    Resolve a canonical card type to a pairwise ``rank``.

    Returns ``(pairwise_rank, rank_match, matched_key)`` where ``rank_match`` is
    ``exact``, ``inferred``, or ``fallback`` (nothing matched; ``pairwise_rank`` is ``0``
    and :func:`resolve_display_order` maps this to ``DISPLAY_ORDER_WHEN_PAIRWISE_UNKNOWN``).
    """
    if not pairwise_ranks:
        return 0, "fallback", ""
    k = _norm(card_type)
    if k in pairwise_ranks:
        return pairwise_ranks[k], "exact", k
    leg = _norm(_legacy_trailing_auto_pairwise_key(k))
    if leg != k and leg in pairwise_ranks:
        return pairwise_ranks[leg], "exact", leg
    for cand in iter_pairwise_lookup_keys(card_type):
        if cand in pairwise_ranks:
            return pairwise_ranks[cand], "inferred", cand
    return 0, "fallback", ""


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

    For **inferred** pairwise matches (e.g. ``… · Auto`` whose rank comes from a stripped key), if
    ``matched_key`` is present in ``merged``, its ``display_order`` is reused so auto tiers follow
    hand-tuned non-auto slots even when those auto rows are omitted from the committed CSV.
    """
    k = _norm(card_type or "")
    if not k:
        return None
    if k in merged:
        return merged[k]
    collapsed = insert_line_card_type_collapsed_for_display(k)
    if collapsed != k and collapsed in merged:
        return merged[collapsed]
    canon = canonical_display_order_lookup_key(k)
    if canon != k and canon in merged:
        return merged[canon]
    pc = Path(pairwise_card_type_csv) if pairwise_card_type_csv else _pairwise_ct_csv_for_inference()
    ct_map, max_r = load_pairwise_rank_column(pc)
    if not ct_map or max_r <= 0:
        return None
    lookup_key = canon
    pr, rank_match, matched_key = lookup_pairwise_rank_for_taxonomy(lookup_key, ct_map)
    if rank_match == "fallback":
        return DISPLAY_ORDER_WHEN_PAIRWISE_UNKNOWN
    # Inferred tiers (e.g. ``… · Auto``) are omitted from the CSV; inherit hand-tuned ``display_order``
    # from the matched non-auto key when present instead of raw rank inversion.
    if rank_match == "inferred" and matched_key:
        mkn = _norm(matched_key)
        if mkn in merged:
            return merged[mkn]
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
    collapsed = insert_line_card_type_collapsed_for_display(k)
    if collapsed != k and collapsed in merged:
        return merged[collapsed]
    canon = canonical_display_order_lookup_key(k)
    if canon != k and canon in merged:
        return merged[canon]
    if infer_missing:
        r = resolve_display_order(k, merged, pairwise_card_type_csv=pairwise_card_type_csv)
        if r is not None:
            return r
    return fallback
