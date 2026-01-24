#!/usr/bin/env python3
# Cmd+F: GH_ANCHOR_TITLE_COMMON_WORDS_SCRIPT_61D2A9C0
import argparse
import csv
import glob
import json
import os
import re
from collections import Counter
from typing import Dict, Iterable, List, Set, Tuple

# Cmd+F: GH_ANCHOR_SIMPLE_STOPWORDS_3B8E1C21
STOPWORDS = {
    # small, practical list (edit freely)
    "a","an","and","are","as","at","be","by","for","from","has","have","in","is","it","its",
    "of","on","or","that","the","to","with","you","your","this","these","those","will",
    "new","lot","card","cards",
    "topps","bowman","panini",  # optional: remove brand noise
}

TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.IGNORECASE)

def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    if not s:
        return "all"
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "all"

def tokenize_title(title: str) -> List[str]:
    # Cmd+F: GH_ANCHOR_TOKENIZE_TITLE_9F0C2D11
    title = (title or "").lower()
    tokens = TOKEN_RE.findall(title)
    # filter stopwords + tiny tokens
    out = []
    for t in tokens:
        t = t.strip().lower()
        if len(t) <= 1:
            continue
        if t in STOPWORDS:
            continue
        out.append(t)
    return out

def iter_titles_from_jsonl(paths: List[str], title_key: str, ct_any_key: str, only_unclassified: bool) -> Iterable[str]:
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)

                if only_unclassified:
                    v = row.get(ct_any_key)
                    if isinstance(v, str):
                        vv = v.strip().lower()
                        is_true = vv in ("true", "1", "yes", "y", "t")
                    else:
                        is_true = bool(v)
                    if is_true:
                        continue

                title = row.get(title_key)
                if isinstance(title, str) and title.strip():
                    yield title

def iter_titles_from_csv(path: str, title_key: str, ct_any_key: str, only_unclassified: bool) -> Iterable[str]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if only_unclassified:
                v = row.get(ct_any_key)
                # treat missing as False; accept common truthy strings
                if isinstance(v, str):
                    vv = v.strip().lower()
                    is_true = vv in ("true", "1", "yes", "y", "t")
                else:
                    is_true = bool(v)
                if is_true:
                    continue

            title = row.get(title_key)
            if isinstance(title, str) and title.strip():
                yield title

def compute_docfreq(titles: Iterable[str]) -> Tuple[int, Counter]:
    # Cmd+F: GH_ANCHOR_COMPUTE_DOCFREQ_7A1B2C3D
    docfreq = Counter()
    total_titles = 0

    for title in titles:
        total_titles += 1
        words = set(tokenize_title(title))  # set => doc frequency per title
        for w in words:
            docfreq[w] += 1

    return total_titles, docfreq

def write_outputs(out_base: str, total_titles: int, docfreq: Counter, top_n: int) -> None:
    os.makedirs(os.path.dirname(out_base) or ".", exist_ok=True)

    # CSV table
    out_csv = out_base + ".csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["word", "titles_with_word", "pct_of_titles"])
        for word, cnt in docfreq.most_common(top_n):
            pct = (cnt / total_titles * 100.0) if total_titles else 0.0
            w.writerow([word, cnt, round(pct, 4)])

    # JSON meta
    out_json = out_base + ".meta.json"
    meta = {
        "total_titles": total_titles,
        "unique_words": len(docfreq),
        "top_n": top_n,
        "out_csv": out_csv,
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"WROTE: {out_csv}")
    print(f"WROTE: {out_json}")

def main():
    # Cmd+F: GH_ANCHOR_TITLE_COMMON_WORDS_MAIN_5C44B0E2
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV path or JSONL glob (e.g. data/term_search_items_table.csv or data/term_search_items_*.jsonl)")
    ap.add_argument("--title-key", default="title", help="Field/column name for title (default: title)")
    ap.add_argument("--top", type=int, default=200, help="How many words to output (default: 200)")
    ap.add_argument("--out", default="", help="Output base path without extension (default: data/common_words_<slug>)")
    ap.add_argument("--ct-any-key", default="CT_any", help="Field/column name for CT_any (default: CT_any)")
    ap.add_argument("--only-unclassified", action="store_true", help="If set, only include rows where CT_any is false")

    args = ap.parse_args()

    inp = args.input.strip()
    title_key = args.title_key.strip() or "title"
    top_n = max(1, int(args.top))
    ct_any_key = args.ct_any_key.strip() or "CT_any"
    only_unclassified = bool(args.only_unclassified)

    titles_iter: Iterable[str]
    out_base: str

    if inp.lower().endswith(".csv"):
        if not os.path.exists(inp):
            raise SystemExit(f"CSV not found: {inp}")
        titles_iter = iter_titles_from_jsonl(paths, title_key, ct_any_key, only_unclassified)
        out_base = args.out.strip() or f"data/common_words_{slugify(os.path.basename(inp))}"
    else:
        paths = sorted(glob.glob(inp))
        if not paths:
            raise SystemExit(f"No JSONL files matched: {inp}")
        titles_iter = iter_titles_from_jsonl(paths, title_key)
        out_base = args.out.strip() or f"data/common_words_{slugify(inp)}"

    total_titles, docfreq = compute_docfreq(titles_iter)
    print(f"TOTAL_TITLES={total_titles}")
    print(f"UNIQUE_WORDS={len(docfreq)}")

    write_outputs(out_base, total_titles, docfreq, top_n)

if __name__ == "__main__":
    main()
