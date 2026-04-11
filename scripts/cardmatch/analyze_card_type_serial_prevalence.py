#!/usr/bin/env python3
"""
Per composite card_type: how often classifier serial_out_of is set (title/flags).

Reads a pilot-style CSV with a `title` column, runs build_composite_card_type + flags,
writes a summary CSV sorted by volume.

Usage:
  python3 scripts/cardmatch/analyze_card_type_serial_prevalence.py \\
    data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/pilot_scored_full.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cardmatch.taxonomy import (  # noqa: E402
    _flags_with_bdc_card_token,
    build_composite_card_type,
    flags_for_title,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "input_csv",
        type=Path,
        help="CSV with a title column (e.g. pilot_scored_full.csv)",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Write CSV here (default: <input_dir>/card_type_serial_prevalence.csv)",
    )
    ap.add_argument(
        "--min-n",
        type=int,
        default=1,
        help="Only include card types with at least this many rows (default: 1)",
    )
    args = ap.parse_args()
    out = args.output or (args.input_csv.parent / "card_type_serial_prevalence.csv")

    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "with_serial": 0})

    with args.input_csv.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if "title" not in (r.fieldnames or []):
            raise SystemExit("CSV must have a 'title' column")
        for row in r:
            title = (row.get("title") or "").strip()
            if not title:
                continue
            ct = build_composite_card_type({"title": title})
            if ct is None:
                continue
            flags = _flags_with_bdc_card_token(title, flags_for_title(title))
            so = flags.get("serial_out_of")
            s = stats[ct]
            s["n"] += 1
            if so is not None:
                s["with_serial"] += 1

    rows_out: list[tuple[str, int, int, float]] = []
    for ct, s in stats.items():
        n = s["n"]
        if n < args.min_n:
            continue
        ws = s["with_serial"]
        pct = (100.0 * ws / n) if n else 0.0
        rows_out.append((ct, n, ws, pct))
    rows_out.sort(key=lambda t: (-t[1], t[0]))

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["card_type", "n", "with_serial", "pct_with_serial"])
        for ct, n, ws, pct in rows_out:
            w.writerow([ct, n, ws, f"{pct:.2f}"])

    print(f"Wrote {out} ({len(rows_out)} card types)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
