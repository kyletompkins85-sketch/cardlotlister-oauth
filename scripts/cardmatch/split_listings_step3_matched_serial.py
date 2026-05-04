#!/usr/bin/env python3
"""Write step3_by_match_status/listings_step3_matched.csv from listings_steps12.csv (5 columns + serial)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cardmatch.bowman_2025_retail_steps import write_listings_step3_matched_with_serial  # noqa: E402


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
        help="Default: <input_parent>/step3_by_match_status",
    )
    args = ap.parse_args()
    inp = args.input.resolve()
    out_dir = args.output_dir.resolve() if args.output_dir else None
    n = write_listings_step3_matched_with_serial(inp, out_dir=out_dir)
    od = out_dir or (inp.parent / "step3_by_match_status")
    print(f"Wrote {n} rows to {od / 'listings_step3_matched.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
