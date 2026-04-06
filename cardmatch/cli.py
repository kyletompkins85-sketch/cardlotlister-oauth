#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from cardmatch.card_type import write_listing_count_reports
from cardmatch.pipeline import load_rows_from_csv, score_rows_to_run_dir, write_review_derived_csvs
from cardmatch.player_index import default_checklist_path
from cardmatch.supabase_fetch import fetch_term_search_items_full_search
from cardmatch.worker_fetch import (
    dedupe_rows_by_run_and_item,
    fetch_multiple_runs,
    filter_rows_exclude_title_substrings,
)


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _parse_run_ids(s: Optional[str]) -> Set[str]:
    if not s or not s.strip():
        return set()
    return {x.strip() for x in s.split(",") if x.strip()}


def _read_run_ids_file(path: Path) -> Set[str]:
    out: Set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if t and not t.startswith("#"):
            out.add(t)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Pilot-match term_search_items titles (Bowman Draft player + likely base)."
    )
    ap.add_argument(
        "--input",
        default="",
        help="Input CSV (omit if using Worker fetch flags)",
    )
    ap.add_argument(
        "--from-worker",
        action="store_true",
        help="Fetch term_search_items from Worker by run_id (needs WORKER_BASE_URL, INTERNAL_API_KEY).",
    )
    ap.add_argument(
        "--from-worker-search",
        action="store_true",
        help="Fetch ALL rows from Worker GET /internal/termSearchItems/search (paginated; same env vars).",
    )
    ap.add_argument(
        "--search-q",
        default="",
        help="With --from-worker-search: title search string (default: 2025 bowman draft). Or CARDMATCH_SEARCH_Q.",
    )
    ap.add_argument(
        "--no-title-exclude",
        action="store_true",
        help="With --from-worker-search: do not exclude titles containing '2024'.",
    )
    ap.add_argument(
        "--exclude-title-substring",
        action="append",
        default=None,
        metavar="SUBSTR",
        help="With --from-worker-search: extra case-insensitive title substrings to drop (repeatable).",
    )
    ap.add_argument(
        "--term-search-run-id",
        action="append",
        dest="term_search_run_ids",
        metavar="UUID",
        help="term_search run_id to fetch (repeatable). Or set TERM_SEARCH_RUN_IDS=comma,separated",
    )
    ap.add_argument(
        "--output-dir",
        default="",
        help="Output directory (default: data/cardmatch_pilot/<UTC>_supabase_2025_bowman_draft_full for "
        "--from-worker-search, else cardmatch/runs/<UTC>)",
    )
    ap.add_argument(
        "--checklist",
        default="",
        help="Path to 2025_Bowman_Draft_Normalized.csv",
    )
    ap.add_argument(
        "--run-ids",
        default="",
        help="When using --input CSV: comma-separated run_id allowlist (Bowman Draft only).",
    )
    ap.add_argument(
        "--run-ids-file",
        default="",
        help="When using --input CSV: file with one run_id per line.",
    )
    ap.add_argument(
        "--no-run-filter",
        action="store_true",
        help="When using --input CSV: do not filter by run_id.",
    )
    ap.add_argument(
        "--review-config",
        default="",
        help="review_targets.json path (default: cardmatch/review_targets.json)",
    )
    ap.add_argument(
        "--baseline",
        default="",
        help="Optional previous pilot_scored_full.csv for changes_since_previous.csv",
    )
    ap.add_argument(
        "--review-focus-only",
        action="store_true",
        help="Skip player matching and other outputs: read scored CSV and write only review_focus.csv "
        "(uses cardmatch/review_targets.json for slice/focus rules). Much faster than a full rescore.",
    )
    ap.add_argument(
        "--listing-counts-only",
        action="store_true",
        help="Read scored CSV and write only listing_counts_by_card_type.csv and "
        "listing_counts_by_player_and_card_type.csv (recomputes primary card_type from titles/flags). Fast.",
    )
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    checklist = Path(args.checklist) if args.checklist else default_checklist_path(root)
    if not checklist.is_file():
        print(f"Checklist not found: {checklist}", file=sys.stderr)
        return 2

    rc_path = Path(args.review_config) if args.review_config else root / "cardmatch" / "review_targets.json"
    if args.output_dir:
        out_dir = Path(args.output_dir)
    elif args.from_worker_search:
        out_dir = root / "data" / "cardmatch_pilot" / f"{_utc_run_id()}_supabase_2025_bowman_draft_full"
    else:
        out_dir = root / "cardmatch" / "runs" / _utc_run_id()
    baseline = Path(args.baseline) if args.baseline else None

    if args.review_focus_only and args.listing_counts_only:
        print("Use only one of --review-focus-only or --listing-counts-only.", file=sys.stderr)
        return 2

    if args.review_focus_only:
        inp = Path(args.input) if args.input else None
        if not inp or not inp.is_file():
            print("--review-focus-only requires --input pointing to pilot_scored_full.csv (or scored rows).", file=sys.stderr)
            return 2
        out_dir = Path(args.output_dir) if args.output_dir else inp.parent
        rows_in, _ = load_rows_from_csv(inp)
        _, focus_path, _, n_focus, blurb = write_review_derived_csvs(
            rows_in,
            out_dir,
            checklist,
            rc_path,
            outputs={"focus"},
        )
        print(f"Wrote {focus_path} ({n_focus} rows)")
        print(f"Sort: {blurb}")
        return 0

    if args.listing_counts_only:
        inp = Path(args.input) if args.input else None
        if not inp or not inp.is_file():
            print(
                "--listing-counts-only requires --input pointing to pilot_scored_full.csv (or scored rows).",
                file=sys.stderr,
            )
            return 2
        out_dir = Path(args.output_dir) if args.output_dir else inp.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        rows_in, _ = load_rows_from_csv(inp)
        type_path, player_path, _ = write_listing_count_reports(rows_in, out_dir)
        print(f"Wrote {type_path}")
        print(f"Wrote {player_path}")
        return 0

    rows_in: List[Dict[str, Any]] = []
    input_label = ""
    run_allow: Set[str] = set()
    no_run_filter = False

    if args.from_worker_search:
        if args.from_worker:
            print("Use only one of --from-worker or --from-worker-search.", file=sys.stderr)
            return 2
        if args.input:
            print("Do not combine --input with --from-worker-search.", file=sys.stderr)
            return 2
        q = (args.search_q or os.getenv("CARDMATCH_SEARCH_Q") or "").strip() or "2025 bowman draft"
        try:
            source, rows_in = fetch_term_search_items_full_search(q)
        except Exception as e:
            print(f"Full search fetch failed: {e}", file=sys.stderr)
            return 1
        excludes: List[str] = []
        if not args.no_title_exclude:
            excludes.append("2024")
        if args.exclude_title_substring:
            excludes.extend([x for x in args.exclude_title_substring if (x or "").strip()])
        rows_in = filter_rows_exclude_title_substrings(rows_in, excludes)
        rows_in = dedupe_rows_by_run_and_item(rows_in)
        input_label = f"{source} q={q!r} (title excludes: {excludes or ['(none)']})"
        run_allow = set()
        no_run_filter = True
    elif args.from_worker:
        ids: List[str] = list(args.term_search_run_ids or [])
        env_ids = os.getenv("TERM_SEARCH_RUN_IDS", "").strip()
        if env_ids:
            ids.extend([x.strip() for x in env_ids.split(",") if x.strip()])
        if not ids:
            print(
                "No term search run IDs. Use --term-search-run-id <uuid> (repeat) or set TERM_SEARCH_RUN_IDS.",
                file=sys.stderr,
            )
            return 2
        # Dedupe preserving order
        seen: Set[str] = set()
        uniq: List[str] = []
        for u in ids:
            if u not in seen:
                seen.add(u)
                uniq.append(u)
        try:
            rows_in = fetch_multiple_runs(uniq)
        except Exception as e:
            print(f"Worker fetch failed: {e}", file=sys.stderr)
            return 1
        input_label = f"Worker `termSearchItems/byRun` for run_id(s): `{', '.join(uniq)}`"
        run_allow = set()
        no_run_filter = True
    else:
        inp = Path(args.input)
        if not inp.is_file():
            print(
                "Provide --input CSV, or --from-worker with run IDs, or --from-worker-search.",
                file=sys.stderr,
            )
            return 2
        rows_in, _ = load_rows_from_csv(inp)
        input_label = f"`{inp}`"
        run_allow = _parse_run_ids(args.run_ids)
        if args.run_ids_file:
            run_allow |= _read_run_ids_file(Path(args.run_ids_file))
        no_run_filter = args.no_run_filter

    try:
        (
            full_path,
            slice_path,
            focus_path,
            unclassified_path,
            summary_path,
            counts_by_type_path,
            counts_by_player_path,
        ) = score_rows_to_run_dir(
            rows_in=rows_in,
            out_dir=out_dir,
            checklist=checklist,
            review_config=rc_path,
            baseline=baseline,
            input_label=input_label,
            run_allow=run_allow,
            no_run_filter=no_run_filter,
        )
    except Exception as e:
        print(e, file=sys.stderr)
        return 2

    ch_path = out_dir / "changes_since_previous.csv"
    print(f"Wrote {full_path}")
    print(f"Wrote {slice_path}")
    print(f"Wrote {focus_path}")
    print(f"Wrote {unclassified_path}")
    print(f"Wrote {summary_path}")
    print(f"Wrote {counts_by_type_path}")
    print(f"Wrote {counts_by_player_path}")
    if baseline and baseline.is_file() and ch_path.is_file():
        print(f"Wrote {ch_path}")
    print("")
    print(f"Open first: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
