#!/usr/bin/env python3
"""Split listings_steps12.csv into one review CSV per match_status (4 columns only)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cardmatch.bowman_2025_retail_steps import write_listings_steps12_split_by_match_status  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        type=Path,
        default=_REPO_ROOT
        / "data/cardmatch_pilot/2025_bowman/20260501_full/listings_steps12.csv",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Default: <input_parent>/step2_by_match_status",
    )
    args = ap.parse_args()
    inp = args.input.resolve()
    out_dir = args.output_dir.resolve() if args.output_dir else None
    counts = write_listings_steps12_split_by_match_status(inp, out_dir=out_dir)
    od = out_dir or (inp.parent / "step2_by_match_status")
    print(f"Wrote {len(counts)} status CSVs + summary under {od}")
    for k in sorted(counts, key=lambda x: (-counts[x], x)):
        print(f"  {counts[k]:6d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
