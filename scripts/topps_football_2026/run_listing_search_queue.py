#!/usr/bin/env python3
"""Search pending 014 listing queries via Worker /comps/batchPlayers (1 page each)."""

from __future__ import annotations

import csv
import os
import sys
import time
from pathlib import Path

import requests

QUEUE = Path("data/topps_football_2026/014_dad_non_insert_search_draft.csv")
LIMIT = int(os.getenv("SEARCH_LIMIT", "10"))
PAGE_SIZE = int(os.getenv("EBAY_LIMIT", "200"))
CHUNK = int(os.getenv("MAX_SEARCHES_PER_CALL", "5"))
PAUSE_S = int(os.getenv("EBAY_PAUSE_MS", "250")) / 1000.0


def _require(name: str) -> str:
    v = (os.getenv(name) or "").strip()
    if not v:
        raise RuntimeError(f"Missing {name}")
    return v


def main() -> None:
    base = _require("WORKER_BASE_URL").rstrip("/")
    key = _require("INTERNAL_API_KEY")
    url = f"{base}/comps/batchPlayers"

    with QUEUE.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    for extra in ("seq", "status", "run_id", "returned"):
        if extra not in fields:
            fields.append(extra)
    for r in rows:
        r.setdefault("seq", "")
        r.setdefault("status", "pending")
        r.setdefault("run_id", "")
        r.setdefault("returned", "")

    pending = [r for r in rows if (r.get("status") or "pending").strip() == "pending"][:LIMIT]
    if not pending:
        print("No pending listing searches.")
        return

    queries = [(r.get("proposed_search") or "").strip() for r in pending]
    if any(not q for q in queries):
        raise RuntimeError("A pending row has an empty proposed_search")
    print(f"Searching {len(queries)} listings x 1 page")

    by_query = {q: r for q, r in zip(queries, pending)}
    for i in range(0, len(queries), CHUNK):
        chunk = queries[i : i + CHUNK]
        body = {
            "prefix": "",
            "max_players": len(chunk),
            "limit": PAGE_SIZE,
            "offset": 0,
            "players": chunk,
        }
        resp = requests.post(
            url,
            headers={"x-internal-key": key, "Content-Type": "application/json"},
            json=body,
            timeout=180,
        )
        print(f"chunk={len(chunk)} status={resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data)
        for p in data.get("processed") or []:
            q = (p.get("playerName") or "").strip()
            row = by_query.get(q)
            if not row:
                print(f"  unmatched processed: {q[:80]}")
                continue
            row["status"] = "done"
            row["run_id"] = str(p.get("run_id") or "")
            row["returned"] = str(p.get("returned") or "")
            print(
                f"  {q[:70]}: returned={p.get('returned')} "
                f"inserted={p.get('inserted_items')} run={p.get('run_id')}"
            )
        time.sleep(PAUSE_S)

    with QUEUE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    done = [r for r in pending if r.get("status") == "done"]
    print(f"Marked done: {len(done)}/{len(pending)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
