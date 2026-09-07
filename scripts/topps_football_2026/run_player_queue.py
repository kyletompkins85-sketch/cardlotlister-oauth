#!/usr/bin/env python3
"""Run the next pending 2026 Topps Football player searches via Worker /comps/batchPlayers."""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

import requests

QUEUE = Path("data/topps_football_2026/players_non_base_plus_rookies.csv")
PREFIX = os.getenv("PREFIX", "2026 Topps Football").strip()
LIMIT = int(os.getenv("PLAYER_LIMIT", "5"))
PAGE_SIZE = int(os.getenv("EBAY_LIMIT", "200"))
PAGE_OFFSETS = [int(x) for x in os.getenv("PAGE_OFFSETS", "0,200").split(",") if x.strip() != ""]
CHUNK = int(os.getenv("MAX_PLAYERS_PER_CALL", "5"))
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

    pending = [r for r in rows if (r.get("status") or "").strip() == "pending"][:LIMIT]
    if not pending:
        print("No pending players.")
        return

    names = [r["search_name"] for r in pending]
    print(f"Searching {len(names)} players x {len(PAGE_OFFSETS)} pages: {names}")

    ok_names: set[str] = set(names)
    for offset in PAGE_OFFSETS:
        for i in range(0, len(names), CHUNK):
            chunk = names[i : i + CHUNK]
            body = {
                "prefix": PREFIX,
                "max_players": len(chunk),
                "limit": PAGE_SIZE,
                "offset": offset,
                "players": chunk,
            }
            resp = requests.post(
                url,
                headers={"x-internal-key": key, "Content-Type": "application/json"},
                json=body,
                timeout=180,
            )
            print(f"offset={offset} chunk={chunk} status={resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(data)
            for p in data.get("processed") or []:
                name = p.get("playerName") or ""
                print(
                    f"  {name}: returned={p.get('returned')} "
                    f"inserted={p.get('inserted_items')} run={p.get('run_id')}"
                )
            time.sleep(PAUSE_S)

    for r in rows:
        if r.get("search_name") in ok_names:
            r["status"] = "done"

    with QUEUE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Marked done: {names}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
