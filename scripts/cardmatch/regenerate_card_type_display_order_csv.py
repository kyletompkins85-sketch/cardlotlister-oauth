#!/usr/bin/env python3
"""
Rebuild ``cardmatch/card_type_display_order.csv`` from pairwise rankings + canonical card types.

- ``display_order`` 1 = cheapest (inverse of pairwise ``rank``, where rank 1 = most expensive).
- Includes full taxonomy strings (e.g. ``Bowman Draft Night · Green /99``).
- Omits redundant bare ``Bowman Draft Night /99``-style rows (no `` · Color``); those tiers match
  generic ``Bowman Draft Night`` — use :func:`cardmatch.card_type_display_order.resolve_display_order`
  at runtime for those keys.

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
    load_card_types_from_listing_counts_csv,
    load_pairwise_rank_column,
    lookup_pairwise_rank_for_taxonomy,
    pairwise_rank_to_display_order,
    should_omit_display_order_row,
)


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
    args = ap.parse_args()

    ct_map, max_r = load_pairwise_rank_column(args.pairwise_csv)
    if not ct_map or max_r <= 0:
        raise SystemExit("No ranks loaded from pairwise CSV")

    listing_types = load_card_types_from_listing_counts_csv(args.listing_counts)
    all_types = sorted(set(ct_map.keys()) | set(listing_types))

    rows: list[dict[str, object]] = []
    omitted = 0
    for ct in all_types:
        pr, rank_match, matched_key = lookup_pairwise_rank_for_taxonomy(ct, ct_map)
        if should_omit_display_order_row(ct, rank_match, matched_key):
            omitted += 1
            continue
        do = pairwise_rank_to_display_order(pr, max_pairwise_rank=max_r)
        rows.append(
            {
                "display_order": do,
                "pairwise_rank": pr,
                "rank_match": rank_match,
                "matched_key": matched_key if rank_match == "inferred" else "",
                "card_type": ct,
            }
        )
    rows.sort(key=lambda r: (int(r["display_order"]), str(r["card_type"])))

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
        f"Wrote {args.output} ({len(rows)} rows, omitted {omitted} bare Product/N rows; "
        f"{len(ct_map)} pairwise keys ∪ {len(listing_types)} listing-count types)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
