#!/usr/bin/env python3
"""
Append a timestamped snapshot of ``card_type_display_order.csv`` **physical line order**
(``file_row``, ``display_order`` column, ``card_type``) to ``card_type_display_order.order.log``
next to the CSV.

Usage (repo root)::

  python3 scripts/cardmatch/log_card_type_display_order.py
  python3 scripts/cardmatch/log_card_type_display_order.py --csv path/to/card_type_display_order.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cardmatch.card_type_display_order import DEFAULT_DISPLAY_ORDER_CSV  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "-o",
        "--csv",
        type=Path,
        default=ROOT / "cardmatch/card_type_display_order.csv",
        help=f"Display order CSV (default: {DEFAULT_DISPLAY_ORDER_CSV})",
    )
    ap.add_argument(
        "--log",
        type=Path,
        default=None,
        help="Log file (default: <csv_dir>/card_type_display_order.order.log)",
    )
    args = ap.parse_args()
    csv_p = args.csv
    if not csv_p.is_file():
        raise SystemExit(f"Missing CSV: {csv_p}")

    log_p = args.log if args.log else csv_p.parent / "card_type_display_order.order.log"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: list[str] = [
        f"# snapshot {ts} {csv_p}",
        "file_row\tdisplay_order\tpairwise_rank\trank_match\tcard_type",
    ]
    with csv_p.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r, start=1):
            ct = (row.get("card_type") or "").replace("\t", " ")
            lines.append(
                "\t".join(
                    [
                        str(i),
                        str(row.get("display_order", "")),
                        str(row.get("pairwise_rank", "")),
                        str(row.get("rank_match", "")),
                        ct,
                    ]
                )
            )

    block = "\n".join(lines) + "\n\n"
    log_p.parent.mkdir(parents=True, exist_ok=True)
    with log_p.open("a", encoding="utf-8") as out:
        out.write(block)

    sys.stdout.write(block)
    print(f"Appended {len(lines) - 2} rows to {log_p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
