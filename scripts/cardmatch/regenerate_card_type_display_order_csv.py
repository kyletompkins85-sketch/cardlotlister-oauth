#!/usr/bin/env python3
"""
Rebuild ``cardmatch/card_type_display_order.csv`` from pairwise rankings + canonical card types.

- ``display_order`` 1 = cheapest (inverse of pairwise ``rank``, where rank 1 = most expensive).
- **Default (preserve):** if the output CSV already exists, its **top-to-bottom row order is kept**
  for every ``card_type`` that still exists after this run. New types only are **appended**
  (sorted by rank / prior ``display_order``). Then ``display_order`` is dense-renumbered ``1 … n``;
  ``DISPLAY_ORDER_ERROR_CARD_TYPES`` stay at ``999``. Your manual line order is not reshuffled.
- ``--no-preserve-display-order``: rebuild ordering from ranks only (ignores existing line order).
- Omits bare insert ``/N`` dupes, inferred-only rows, and types with no pairwise match (fallback).

Usage (repo root):

  python3 scripts/cardmatch/regenerate_card_type_display_order_csv.py

Writes ``cardmatch/card_type_display_order.csv`` (overwrites).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cardmatch.card_type_display_order import (  # noqa: E402
    DEFAULT_DISPLAY_ORDER_CSV,
    DISPLAY_ORDER_ERROR_CARD_TYPES,
    DISPLAY_ORDER_WHEN_PAIRWISE_UNKNOWN,
    dense_renumber_display_order_column,
    load_card_types_from_listing_counts_csv,
    load_pairwise_rank_column,
    lookup_pairwise_rank_for_taxonomy,
    pairwise_rank_to_display_order,
    should_omit_display_order_row,
)
from cardmatch.pairwise_price_rankings import _norm  # noqa: E402
from cardmatch.taxonomy import canonical_display_order_lookup_key  # noqa: E402


def _load_prior_display_orders(path: Path) -> dict[str, int]:
    """``card_type`` (normalized) -> committed ``display_order`` for merge-preservation."""
    if not path.is_file():
        return {}
    out: dict[str, int] = {}
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            k = _norm(row.get("card_type", "") or "")
            if not k:
                continue
            try:
                out[k] = int(float(row.get("display_order", "")))
            except (TypeError, ValueError):
                continue
    return out


def _load_prior_row_order(path: Path) -> list[str]:
    """``card_type`` values in file line order (top to bottom)."""
    if not path.is_file():
        return []
    out: list[str] = []
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            k = _norm(row.get("card_type", "") or "")
            if k:
                out.append(k)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "pairwise_csv",
        type=Path,
        nargs="?",
        default=ROOT
        / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/bowman_pairwise_card_type_rankings_with_listings.csv",
        help="bowman_pairwise_card_type_rankings_with_listings.csv",
    )
    ap.add_argument(
        "--listing-counts",
        type=Path,
        default=ROOT
        / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/listing_counts_by_card_type.csv",
        help="listing_counts_by_card_type.csv (canonical card_type names)",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "cardmatch/card_type_display_order.csv",
        help=f"Output CSV (default: {DEFAULT_DISPLAY_ORDER_CSV})",
    )
    ap.add_argument(
        "--no-preserve-display-order",
        dest="preserve_display_order",
        action="store_false",
        default=True,
        help="Ignore existing CSV line order; sort all rows from ranks.",
    )
    args = ap.parse_args()

    ct_map, max_r = load_pairwise_rank_column(args.pairwise_csv)
    if not ct_map or max_r <= 0:
        raise SystemExit("No ranks loaded from pairwise CSV")

    prior_do: dict[str, int] = {}
    prior_row_order: list[str] = []
    if args.preserve_display_order:
        prior_do = _load_prior_display_orders(args.output)
        prior_row_order = _load_prior_row_order(args.output)

    listing_types = load_card_types_from_listing_counts_csv(args.listing_counts)
    all_types = sorted(set(ct_map.keys()) | set(listing_types))

    by_ct: dict[str, dict[str, object]] = {}
    omitted_bare = 0
    omitted_inferred = 0
    omitted_fallback = 0
    seen_canon: set[str] = set()
    for ct in all_types:
        raw_nk = _norm(ct)
        pr0, rm0, mk0 = lookup_pairwise_rank_for_taxonomy(raw_nk, ct_map)
        if should_omit_display_order_row(raw_nk, rm0, mk0):
            omitted_bare += 1
            continue
        canon = canonical_display_order_lookup_key(ct)
        if canon in seen_canon:
            continue
        seen_canon.add(canon)
        pr, rank_match, matched_key = lookup_pairwise_rank_for_taxonomy(canon, ct_map)
        if should_omit_display_order_row(canon, rank_match, matched_key):
            omitted_bare += 1
            continue
        if rank_match == "inferred":
            omitted_inferred += 1
            continue
        if rank_match == "fallback":
            omitted_fallback += 1
            continue
        do = pairwise_rank_to_display_order(pr, max_pairwise_rank=max_r)
        nk = canon
        if prior_do:
            if nk in prior_do:
                do = prior_do[nk]
            elif _norm(ct) in prior_do:
                do = prior_do[_norm(ct)]
        if nk in DISPLAY_ORDER_ERROR_CARD_TYPES:
            do = DISPLAY_ORDER_WHEN_PAIRWISE_UNKNOWN
        by_ct[nk] = {
            "display_order": do,
            "pairwise_rank": pr,
            "rank_match": rank_match,
            "matched_key": matched_key if rank_match == "inferred" else "",
            "card_type": canon,
        }

    def _sort_key(r: dict[str, object]) -> tuple[int, int, str]:
        nk = _norm(str(r["card_type"]))
        err = 1 if nk in DISPLAY_ORDER_ERROR_CARD_TYPES else 0
        return (err, int(r["display_order"]), str(r["card_type"]))

    rows: list[dict[str, object]]
    if not args.preserve_display_order:
        rows = list(by_ct.values())
        rows.sort(key=_sort_key)
    elif prior_row_order:
        rows = []
        placed: set[str] = set()
        for k in prior_row_order:
            nk = _norm(k)
            if nk in by_ct and nk not in placed:
                rows.append(by_ct[nk])
                placed.add(nk)
        remaining = [by_ct[k] for k in by_ct if k not in placed]
        remaining.sort(key=_sort_key)
        rows.extend(remaining)
    else:
        rows = list(by_ct.values())
        rows.sort(key=_sort_key)

    dense_renumber_display_order_column(rows)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "display_order",
                "pairwise_rank",
                "rank_match",
                "matched_key",
                "card_type",
            ],
        )
        w.writeheader()
        w.writerows(rows)

    print(
        f"Wrote {args.output} ({len(rows)} rows, omitted {omitted_bare} bare Product/N rows, "
        f"{omitted_inferred} inferred-only rows, {omitted_fallback} fallback (no pairwise) rows; "
        f"{len(ct_map)} pairwise keys ∪ {len(listing_types)} listing-count types)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
