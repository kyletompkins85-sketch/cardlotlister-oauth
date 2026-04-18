#!/usr/bin/env python3
"""
Rewrite only the ``display_order`` column — **does not reorder rows**.

Reads the CSV top-to-bottom, assigns ``1 … n`` in that order; ``999`` and error-tier rows stay ``999``.
Use this when you have already arranged ``card_type`` lines the way you want.

Optional ``--sort-like-regen`` re-sorts rows first (same as ``regenerate … --no-preserve-display-order``);
only use that when you intentionally want to discard manual line order.

Usage::

  python3 scripts/cardmatch/dense_renumber_card_type_display_order_csv.py
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
    dense_renumber_display_order_column,
)
from cardmatch.pairwise_price_rankings import _norm  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "cardmatch/card_type_display_order.csv",
        help=f"CSV path (default: {DEFAULT_DISPLAY_ORDER_CSV})",
    )
    ap.add_argument(
        "--sort-like-regen",
        action="store_true",
        help="Re-sort rows before renumbering (discards manual line order).",
    )
    args = ap.parse_args()
    p = args.output
    if not p.is_file():
        raise SystemExit(f"Missing CSV: {p}")

    with p.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        fieldnames = list(r.fieldnames or [])
        rows = list(r)
    if not fieldnames or "display_order" not in fieldnames or "card_type" not in fieldnames:
        raise SystemExit("CSV must have display_order and card_type columns")

    if args.sort_like_regen:

        def _sk(row: dict[str, str]) -> tuple[int, int, str]:
            nk = _norm(row.get("card_type", "") or "")
            err = 1 if nk in DISPLAY_ORDER_ERROR_CARD_TYPES else 0
            try:
                do = int(float(row.get("display_order", "") or 0))
            except (TypeError, ValueError):
                do = 0
            return (err, do, nk)

        rows.sort(key=_sk)

    dense_renumber_display_order_column(rows)

    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {p} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
