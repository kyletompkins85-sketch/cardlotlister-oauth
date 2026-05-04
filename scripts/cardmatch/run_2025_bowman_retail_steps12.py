#!/usr/bin/env python3
"""
Apply 2025 Bowman retail steps 1–3 (exclusions + checklist match + insert name inference) to a term_search_items_export CSV.

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
    load_retail_api_context,
    retail_steps_row_extensions,
    write_listings_step23_split_by_match_status,
    write_listings_step3_matched_with_serial,
    write_listings_steps12_split_by_match_status,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="2025 Bowman retail: exclude + match + insert inference.")
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
    ap.add_argument(
        "--no-step23-split",
        action="store_true",
        help="Do not write step-2+3 combined splits under step23_by_match_status/",
    )
    ap.add_argument(
        "--step23-split-dir",
        type=Path,
        default=None,
        help="Override directory for step-23 split CSVs (default: <output_parent>/step23_by_match_status)",
    )
    ap.add_argument(
        "--no-step3-matched-split",
        action="store_true",
        help="Do not write step3_by_match_status/listings_step3_matched.csv (matched + serial review)",
    )
    ap.add_argument(
        "--step3-matched-dir",
        type=Path,
        default=None,
        help="Override directory for step-3 matched+serial CSV (default: <output_parent>/step3_by_match_status)",
    )
    args = ap.parse_args()

    inp = args.input.resolve()
    out = args.output
    if out is None:
        out = inp.parent / "listings_steps12.csv"
    else:
        out = out.resolve()

    ctx = load_retail_api_context(args.checklist)

    with inp.open(newline="", encoding="utf-8") as fin:
        r = csv.DictReader(fin)
        fieldnames = list(r.fieldnames or [])
        extra = [
            "WF_serial_out_of",
            "serial_out_of",
            "exclusion_reason",
            "excluded",
            "match_status",
            "step2_pass",
            "matched_card_number",
            "matched_checklist_player",
            "matched_card_type",
            "player_match_score",
            "extracted_codes",
            "step3_inferred_card_number",
            "step3_inference_kind",
            "step3_inference_score",
            "step3_matched_checklist_player",
            "step3_matched_card_type",
            "match_status_after_step3",
            "step23_pass",
        ]
        out_fields = fieldnames + [c for c in extra if c not in fieldnames]

        with out.open("w", newline="", encoding="utf-8") as fout:
            w = csv.DictWriter(fout, fieldnames=out_fields, extrasaction="ignore")
            w.writeheader()
            n = 0
            for row in r:
                title = row.get("title") or ""
                ext = retail_steps_row_extensions(title, ctx)
                row.update(ext)
                w.writerow(row)
                n += 1

    print(f"Wrote {n} rows to {out}")

    if not args.no_step2_split:
        split_dir = args.split_dir.resolve() if args.split_dir else None
        counts = write_listings_steps12_split_by_match_status(out, out_dir=split_dir)
        sd = split_dir or (out.parent / "step2_by_match_status")
        print(f"Wrote step-2 split CSVs under {sd} ({len(counts)} files + step2_split_summary.txt)")

    if not args.no_step23_split:
        s23 = args.step23_split_dir.resolve() if args.step23_split_dir else None
        c23 = write_listings_step23_split_by_match_status(out, out_dir=s23)
        d23 = s23 or (out.parent / "step23_by_match_status")
        print(
            f"Wrote step-2+3 split CSVs under {d23} ({len(c23)} status buckets + "
            f"listings_step23_still_unmatched_after_both.csv + step23_split_summary.txt)"
        )

    if not args.no_step3_matched_split:
        s3 = args.step3_matched_dir.resolve() if args.step3_matched_dir else None
        n_matched_serial = write_listings_step3_matched_with_serial(out, out_dir=s3)
        d3 = s3 or (out.parent / "step3_by_match_status")
        print(
            f"Wrote step-3 matched+serial under {d3} ({n_matched_serial} rows in listings_step3_matched.csv)"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
