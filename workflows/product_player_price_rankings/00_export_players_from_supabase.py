#!/usr/bin/env python3
"""
Export players from Supabase table to CSV (NO EBAY).

Writes:
  workflows/product_player_price_rankings/data/<RUN_ID>/players_export.csv

Env required:
  RUN_ID
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY   (or a key that can SELECT from the players table)

Optional:
  PLAYERS_TABLE (default: players_import_2025_bowman_draft)
  PLAYER_COL    (default: playerName)
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _get_page(url: str, headers: Dict[str, str], params: Dict[str, str]) -> List[Dict[str, Any]]:
    # PostgREST pagination via Range headers
    # https://postgrest.org/ (Range-Unit: items)
    out: List[Dict[str, Any]] = []
    start = 0
    page_size = 1000

    while True:
        h = dict(headers)
        h["Range-Unit"] = "items"
        h["Range"] = f"{start}-{start + page_size - 1}"

        resp = requests.get(url, headers=h, params=params, timeout=60)
        if not resp.ok:
            raise RuntimeError(f"Supabase GET failed {resp.status_code}: {resp.text}")

        rows = resp.json()
        if not isinstance(rows, list):
            raise RuntimeError(f"Unexpected response type: {type(rows)}")

        out.extend([r for r in rows if isinstance(r, dict)])

        # If fewer than page_size returned, we’re done
        if len(rows) < page_size:
            break
        start += page_size

    return out


def main() -> None:
    run_id = _require_env("RUN_ID")
    supabase_url = _require_env("SUPABASE_URL").rstrip("/")
    supabase_key = _require_env("SUPABASE_SERVICE_ROLE_KEY")

    table = (os.getenv("PLAYERS_TABLE") or "players_import_2025_bowman_draft").strip()
    player_col = (os.getenv("PLAYER_COL") or "playerName").strip()

    workflow_root = Path(__file__).resolve().parent
    run_dir = workflow_root / "data" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # PostgREST endpoint
    endpoint = f"{supabase_url}/rest/v1/{table}"

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
    }

    params = {
        "select": player_col,
    }

    rows = _get_page(endpoint, headers, params)

    players: List[str] = []
    for r in rows:
        nm = (r.get(player_col) or "").strip()
        if nm:
            players.append(nm)

    # de-dupe preserving order
    seen = set()
    uniq: List[str] = []
    for p in players:
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)

    out_csv = run_dir / "players_export.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["playerName"])
        for p in uniq:
            w.writerow([p])

    print(f"RUN_ID={run_id}")
    print(f"TABLE={table}")
    print(f"PLAYERS_EXPORTED={len(uniq)}")
    print(f"OUT={out_csv}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
