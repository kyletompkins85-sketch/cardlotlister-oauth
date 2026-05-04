#!/usr/bin/env python3
"""
Build ``data/checklists/normalized/2025_Bowman_retail_card_type_serial_combos_observed.csv``:
unique (canonical card_type, serial) from matched step-3 retail listings, plus UI ``display_name``.

Re-run after updating ``listings_steps12.csv`` / ``listings_step3_matched.csv``.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from cardmatch.bowman_2025_retail_combo_catalog import (  # noqa: E402
    card_type_sort_tier,
    canonical_card_type,
    display_name_for_card_type_display,
    load_card_type_lookup_maps,
    serial_sort_tuple,
)


def _collect_pairs(
    step3_path: Path,
    step12_path: Path,
    ct_to_disp: dict[str, str],
    disp_to_ct: dict[str, str],
) -> set[tuple[str, int]]:
    pairs: set[tuple[str, int]] = set()
    if step3_path.exists():
        with step3_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                ct = canonical_card_type(row.get("card_type", ""), ct_to_disp, disp_to_ct)
                ser = (row.get("serial") or "").strip()
                if not ct or ser == "":
                    continue
                try:
                    ser_i = int(ser)
                except ValueError:
                    continue
                pairs.add((ct, ser_i))
    if step12_path.exists():
        with step12_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("match_status_after_step3") or "").strip() != "matched":
                    continue
                ct_raw = (row.get("matched_card_type") or "").strip()
                if not ct_raw:
                    ct_raw = (row.get("step3_matched_card_type") or "").strip()
                ct = canonical_card_type(ct_raw, ct_to_disp, disp_to_ct)
                ser_raw = (row.get("serial_out_of") or "").strip()
                if not ct or ser_raw == "":
                    continue
                try:
                    ser_i = int(ser_raw)
                except ValueError:
                    continue
                pairs.add((ct, ser_i))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--lookup",
        type=Path,
        default=_REPO / "data/checklists/normalized/2025_Bowman_card_number_lookup.csv",
    )
    ap.add_argument(
        "--step3",
        type=Path,
        default=_REPO
        / "data/cardmatch_pilot/2025_bowman/20260501_full/step3_by_match_status/listings_step3_matched.csv",
    )
    ap.add_argument(
        "--step12",
        type=Path,
        default=_REPO / "data/cardmatch_pilot/2025_bowman/20260501_full/listings_steps12.csv",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=_REPO / "data/checklists/normalized/2025_Bowman_retail_card_type_serial_combos_observed.csv",
    )
    args = ap.parse_args()

    ct_to_disp, disp_to_ct = load_card_type_lookup_maps(args.lookup.resolve())
    pairs = _collect_pairs(args.step3.resolve(), args.step12.resolve(), ct_to_disp, disp_to_ct)
    rows = sorted(
        pairs,
        key=lambda x: (card_type_sort_tier(x[0]), x[0], serial_sort_tuple(x[1])),
    )

    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["sort_order", "card_type", "card_type_display", "serial", "display_name"]
        )
        for i, (ct, ser_i) in enumerate(rows, start=1):
            disp = ct_to_disp.get(ct, "")
            w.writerow([i, ct, disp, ser_i, display_name_for_card_type_display(disp)])

    print(f"Wrote {len(rows)} rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
