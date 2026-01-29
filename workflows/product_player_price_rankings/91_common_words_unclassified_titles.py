#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_COMMON_WORDS_UNCLASSIFIED_BOWMAN_1D7A9C20
"""
Diagnostic: Most common keywords in UNCLASSIFIED titles (Bowman classifier).

UNCLASSIFIED = CT_any == False, where CT_any = any(CT_* boolean key is True)
(CT_list is ignored.)

Sources (in order):
  1) If present: workflows/product_player_price_rankings/data/<RUN_ID>/term_search_items_export.csv
  2) Fallback: Worker -> GET /internal/termSearchItems/search?q=...  (NO EBAY)

Outputs (same folder):
  - common_words_unclassified.csv
  - common_words_unclassified.meta.json

NO EBAY CALLS.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import urlencode, urljoin

import requests


# -----------------------------
# Tokenization
# -----------------------------
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.IGNORECASE)

STOPWORDS = {
    # generic
    "a","an","and","are","as","at","be","by","for","from","has","have","in","is","it","its",
    "of","on","or","that","the","to","with","you","your","this","these","those","will",

    # hobby noise (edit freely)
    "card","cards","lot","lots","single","singles",

    # NOTE: keep these if you DON'T want them dominating the list
    "bowman","draft","base","paper","chrome",
    "mlb","baseball",

    # year noise
    "2025","2024","2023","2022","2021","2020","2019","2018",
}


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _passes_require_all(title: str, require_all_csv: str) -> bool:
    words = [w.strip().lower() for w in (require_all_csv or "").split(",") if w.strip()]
    if not words:
        return True
    t = (title or "").lower()
    return all(w in t for w in words)


def tokenize(title: str) -> List[str]:
    s = (title or "").lower()
    toks = TOKEN_RE.findall(s)
    out = []
    for t in toks:
        t = t.strip().lower()
        if len(t) <= 1:
            continue
        if t in STOPWORDS:
            continue
        out.append(t)
    return out


def _load_bowman_classifier():
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        from z10_bowman_listing_classifier import classify_title  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Could not import z10_bowman_listing_classifier.py from workflows/product_player_price_rankings/\n"
            f"IMPORT_ERROR={e}"
        )
    return classify_title


def iter_titles_from_export_csv(csv_path: Path, title_col: str) -> Iterable[str]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            return
        for row in r:
            t = (row.get(title_col) or "").strip()
            if t:
                yield t


def _worker_get_json(url: str, key: str) -> Dict[str, Any]:
    resp = requests.get(url, headers={"x-internal-key": key}, timeout=90)
    text = resp.text
    try:
        data = resp.json()
    except Exception:
        data = {"raw": text}
    if not resp.ok:
        raise RuntimeError(f"Worker GET failed {resp.status_code}: {text}")
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response type: {type(data)}")
    return data


def iter_titles_from_worker(base_url: str, api_key: str, q: str, title_key: str = "title") -> Iterable[str]:
    limit = 1000
    offset = 0
    while True:
        params = {"q": q, "limit": str(limit), "offset": str(offset)}
        endpoint = urljoin(base_url.rstrip("/") + "/", "internal/termSearchItems/search")
        url = f"{endpoint}?{urlencode(params)}"

        data = _worker_get_json(url, api_key)
        rows = data.get("rows") or []
        if not isinstance(rows, list):
            raise RuntimeError("Worker returned rows that were not a list")

        for row in rows:
            if not isinstance(row, dict):
                continue
            t = (row.get(title_key) or "").strip()
            if t:
                yield t

        next_offset = data.get("next_offset")
        if not next_offset:
            break
        offset = int(next_offset)


def ct_any_from_flags(flags: Dict[str, Any]) -> bool:
    # CT_any = any boolean CT_* True, ignore CT_list string
    for k, v in flags.items():
        if not k.startswith("CT_"):
            continue
        if k == "CT_list":
            continue
        if isinstance(v, bool) and v:
            return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="", help="RUN_ID folder under workflows/product_player_price_rankings/data/")
    ap.add_argument("--title-col", default="title", help="Title column name (default: title)")
    ap.add_argument("--top", type=int, default=200, help="Top N keywords (default: 200)")
    ap.add_argument("--max-rows", type=int, default=0, help="If >0, stop after scanning this many titles")
    ap.add_argument("--q", default="", help="Worker fallback q (e.g. '2025 Bowman Draft') (NO EBAY)")
    ap.add_argument(
        "--require-all",
        default="bowman,draft",
        help="Comma-separated words that MUST appear in title (default: bowman,draft)",
    )
    args = ap.parse_args()

    run_id = (args.run_id or os.getenv("RUN_ID") or "").strip()
    if not run_id:
        raise SystemExit("Missing --run-id (or env RUN_ID)")

    workflow_root = Path(__file__).resolve().parent
    run_dir = workflow_root / "data" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    export_csv = run_dir / "term_search_items_export.csv"
    title_col = (args.title_col or "title").strip()
    top_n = max(1, int(args.top))
    max_rows = int(args.max_rows or 0)

    classify_title = _load_bowman_classifier()

    # Choose source: CSV first, else Worker fallback (NO EBAY)
    source = ""
    if export_csv.exists():
        source = f"csv:{export_csv}"
        titles_iter = iter_titles_from_export_csv(export_csv, title_col)
    else:
        base = _require_env("WORKER_BASE_URL")
        key = _require_env("INTERNAL_API_KEY")
        q = (args.q or os.getenv("PREFIX") or "").strip()
        if not q:
            raise SystemExit(
                f"Missing input CSV: {export_csv}\n"
                "And no fallback query provided. Provide --q or set env PREFIX.\n"
                "NOTE: this fallback reads from Supabase via Worker and DOES NOT call eBay."
            )
        source = f"worker:/internal/termSearchItems/search?q={q}"
        titles_iter = iter_titles_from_worker(base, key, q, title_key="title")

    docfreq = Counter()
    scanned = 0
    passed_require = 0
    unclassified_rows = 0

    for title in titles_iter:
        scanned += 1

        if not _passes_require_all(title, args.require_all):
            if max_rows > 0 and scanned >= max_rows:
                break
            continue
        passed_require += 1

        flags = classify_title(title)
        if ct_any_from_flags(flags):
            if max_rows > 0 and scanned >= max_rows:
                break
            continue

        unclassified_rows += 1
        words = set(tokenize(title))  # doc frequency per title
        for w in words:
            docfreq[w] += 1

        if max_rows > 0 and scanned >= max_rows:
            break

    out_csv = run_dir / "common_words_unclassified.csv"
    out_meta = run_dir / "common_words_unclassified.meta.json"

    total = max(1, unclassified_rows)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["word", "titles_with_word", "pct_of_unclassified_titles"])
        for word, cnt in docfreq.most_common(top_n):
            w.writerow([word, cnt, round((cnt / total) * 100.0, 4)])

    meta = {
        "run_id": run_id,
        "source": source,
        "scanned_titles": scanned,
        "passed_require_all": passed_require,
        "unclassified_titles": unclassified_rows,
        "unique_words": len(docfreq),
        "top_n": top_n,
        "require_all": args.require_all,
        "out_csv": str(out_csv),
    }
    out_meta.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"SOURCE={source}")
    print(f"RUN_ID={run_id}")
    print(f"SCANNED_TITLES={scanned}")
    print(f"PASSED_REQUIRE_ALL={passed_require}")
    print(f"UNCLASSIFIED_TITLES={unclassified_rows}")
    print(f"UNIQUE_WORDS={len(docfreq)}")
    print(f"OUT_CSV={out_csv}")
    print(f"OUT_META={out_meta}")
    print(f"REQUIRE_ALL={args.require_all}")


if __name__ == "__main__":
    main()
