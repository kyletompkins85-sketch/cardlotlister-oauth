#!/usr/bin/env python3
"""
Apply 2025 Bowman retail steps 1–2 (exclusions + checklist match) to a term_search_items_export CSV.

Example:
  python3 scripts/cardmatch/run_2025_bowman_retail_steps12.py \\
    --input data/cardmatch_pilot/2025_bowman/20260501_full/term_search_items_export.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cardmatch.bowman_2025_retail_steps import (  # noqa: E402
    checklist_code_prefixes,
    load_card_lookup,
    process_title,
    write_listings_steps12_split_by_match_status,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="2025 Bowman retail: exclude + match to checklist.")
    ap.add_argument(
        "--input",
        type=Path,
        default=_REPO_ROOT
        / "data/cardmatch_pilot/2025_bowman/20260501_full/term_search_items_export.csv",
        help="term_search_items_export.csv path",
    )
    ap.add_argument(
        "--checklist",
        type=Path,
        default=None,
        help="Override 2025_Bowman_card_number_lookup.csv",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV (default: alongside input as listings_steps12.csv)",
    )
    ap.add_argument(
        "--no-step2-split",
        action="store_true",
        help="Do not write per-match_status CSVs under step2_by_match_status/",
    )
    ap.add_argument(
        "--split-dir",
        type=Path,
        default=None,
        help="Override directory for step-2 split CSVs (default: <output_parent>/step2_by_match_status)",
    )
    args = ap.parse_args()

    inp = args.input.resolve()
    out = args.output
    if out is None:
        out = inp.parent / "listings_steps12.csv"
    else:
        out = out.resolve()

    by_key, _names = load_card_lookup(args.checklist)
    prefixes = checklist_code_prefixes(by_key)

    with inp.open(newline="", encoding="utf-8") as fin:
        r = csv.DictReader(fin)
        fieldnames = list(r.fieldnames or [])
        extra = [
            "exclusion_reason",
            "excluded",
            "match_status",
            "matched_card_number",
            "matched_checklist_player",
            "matched_card_type",
            "player_match_score",
            "extracted_codes",
        ]
        out_fields = fieldnames + [c for c in extra if c not in fieldnames]

        with out.open("w", newline="", encoding="utf-8") as fout:
            w = csv.DictWriter(fout, fieldnames=out_fields, extrasaction="ignore")
            w.writeheader()
            n = 0
            for row in r:
                title = row.get("title") or ""
                ex, mr = process_title(title, by_key, prefixes)
                row["exclusion_reason"] = ex
                row["excluded"] = "1" if ex else "0"
                row["match_status"] = mr.match_status
                row["matched_card_number"] = mr.matched_card_number
                row["matched_checklist_player"] = mr.matched_player
                row["matched_card_type"] = mr.matched_card_type
                row["player_match_score"] = f"{mr.player_match_score:.2f}" if mr.player_match_score else ""
                row["extracted_codes"] = mr.extracted_codes
                w.writerow(row)
                n += 1

    print(f"Wrote {n} rows to {out}")

    if not args.no_step2_split:
        split_dir = args.split_dir.resolve() if args.split_dir else None
        counts = write_listings_steps12_split_by_match_status(out, out_dir=split_dir)
        sd = split_dir or (out.parent / "step2_by_match_status")
        print(f"Wrote step-2 split CSVs under {sd} ({len(counts)} files + step2_split_summary.txt)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
