#!/usr/bin/env python3
"""Search pending 014 listing queries. One page each. Query is proposed_search only."""

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
PAUSE_S = int(os.getenv("EBAY_PAUSE_MS", "2000")) / 1000.0


def _require(name: str) -> str:
    v = (os.getenv(name) or "").strip()
    if not v:
        raise RuntimeError(f"Missing {name}")
    return v


def _user_key() -> str:
    for name in ("COMPS_USER_KEY", "USER_KEY", "SYNC_USERKEY"):
        v = (os.getenv(name) or "").strip()
        if v:
            return v
    return ""


def _search_term(base: str, key: str, user_key: str, query: str) -> dict:
    body = {"query": query, "limit": PAGE_SIZE, "offset": 0}
    if user_key:
        body["userKey"] = user_key
    resp = requests.post(
        f"{base}/comps/searchTerm",
        headers={"x-internal-key": key, "Content-Type": "application/json"},
        json=body,
        timeout=180,
    )
    data = {}
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    if resp.status_code == 401 and (data.get("error") or "") == "missing_userKey":
        return _search_via_batch(base, key, query)
    print(f"  searchTerm status={resp.status_code} query={query}")
    resp.raise_for_status()
    if not data.get("ok"):
        raise RuntimeError(data)
    if (data.get("query") or "").strip() != query:
        raise RuntimeError(f"Worker query mismatch: {data.get('query')!r} != {query!r}")
    return data


def _search_via_batch(base: str, key: str, query: str) -> dict:
    # batchPlayers does (prefix || "2025 Bowman Draft").trim()
    # A space is truthy, then trims to empty, so eBay q == playerName.
    resp = requests.post(
        f"{base}/comps/batchPlayers",
        headers={"x-internal-key": key, "Content-Type": "application/json"},
        json={
            "prefix": " ",
            "max_players": 1,
            "limit": PAGE_SIZE,
            "offset": 0,
            "players": [query],
        },
        timeout=180,
    )
    print(f"  batchPlayers(space prefix) status={resp.status_code} query={query}")
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data)
    processed = (data.get("processed") or [None])[0] or {}
    name = (processed.get("playerName") or "").strip()
    if name != query:
        raise RuntimeError(f"batchPlayers name mismatch: {name!r} != {query!r}")
    return {
        "ok": True,
        "query": query,
        "run_id": processed.get("run_id"),
        "returned": processed.get("returned"),
        "inserted_items": processed.get("inserted_items"),
    }


def main() -> None:
    base = _require("WORKER_BASE_URL").rstrip("/")
    key = _require("INTERNAL_API_KEY")
    user_key = _user_key()

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

    print(f"Searching {len(pending)} listings x 1 page (pause {PAUSE_S:.1f}s)")
    for row in pending:
        query = (row.get("proposed_search") or "").strip()
        if not query:
            raise RuntimeError("A pending row has an empty proposed_search")
        if query.lower().startswith("2025 bowman draft"):
            raise RuntimeError(f"Refusing Bowman-prefixed query: {query}")
        data = _search_term(base, key, user_key, query)
        row["status"] = "done"
        row["run_id"] = str(data.get("run_id") or "")
        row["returned"] = str(data.get("returned") or "")
        print(
            f"  returned={data.get('returned')} "
            f"inserted={data.get('inserted_items')} run={data.get('run_id')}"
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
