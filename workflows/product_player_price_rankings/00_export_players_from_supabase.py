#!/usr/bin/env python3
"""
Export players from the players table WITHOUT calling eBay.

Preferred source:
  - Worker internal endpoint (uses INTERNAL_API_KEY). This avoids SUPABASE_URL secrets in Actions.

Writes:
  workflows/product_player_price_rankings/data/<RUN_ID>/players_export.csv

Env required:
  RUN_ID
  WORKER_BASE_URL
  INTERNAL_API_KEY

Optional:
  PLAYERS_TABLE (default: players_import_2025_bowman_draft)
  PLAYER_COL    (default: playerName)
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode, urljoin

import requests


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _worker_get(url: str, key: str) -> Any:
    resp = requests.get(url, headers={"x-internal-key": key}, timeout=90)
    if not resp.ok:
        raise RuntimeError(f"Worker GET failed {resp.status_code}: {resp.text}")
    return resp.json()


def _iter_players_from_worker(base: str, key: str, table: str, col: str) -> Iterable[str]:
    """
    Tries a few likely Worker endpoints for listing players from a Supabase table.
    You only need ONE of these to exist in your Worker.
    """
    # Add/adjust candidates to match your Worker if needed.
    candidates = [
        "internal/players/list",
        "internal/players",
        "internal/playerNames",
        "internal/supabase/players",
        "internal/tableRows",
    ]

    # We’ll probe endpoints until one works.
    last_err: Optional[str] = None

    for path in candidates:
        try:
            limit = 1000
            offset = 0
            while True:
                params = {
                    "table": table,
                    "select": col,
                    "limit": str(limit),
                    "offset": str(offset),
                }
                endpoint = urljoin(base.rstrip("/") + "/", path)
                url = f"{endpoint}?{urlencode(params)}"
                data = _worker_get(url, key)

                # Accept either: list[dict] OR {"rows": list[dict], "next_offset": ...}
                if isinstance(data, list):
                    rows = data
                    next_offset = None
                elif isinstance(data, dict):
                    rows = data.get("rows") or data.get("data") or []
                    next_offset = data.get("next_offset") or data.get("nextOffset")
                else:
                    raise RuntimeError(f"Unexpected response type: {type(data)}")

                if not isinstance(rows, list):
                    raise RuntimeError("Expected rows to be a list")

                got = 0
                for r in rows:
                    if not isinstance(r, dict):
                        continue
                    nm = (r.get(col) or "").strip()
                    if nm:
                        got += 1
                        yield nm

                if next_offset:
                    offset = int(next_offset)
                    continue

                # If endpoint is “plain list”, paginate by count
                if isinstance(data, list) and len(rows) == limit and got > 0:
                    offset += limit
                    continue

                break

            # if we got here, this endpoint worked; stop trying others
            return

        except Exception as e:
            last_err = f"{path}: {e}"
            continue

    raise RuntimeError(
        "Could not export players via Worker. None of the candidate endpoints worked.\n"
        "Tried:\n  - " + "\n  - ".join(candidates) + "\n"
        + (f"\nLast error: {last_err}\n" if last_err else "")
        + "\nFix: point this script at your Worker’s actual endpoint for listing a table."
    )


def main() -> None:
    run_id = _require_env("RUN_ID")
    base = _require_env("WORKER_BASE_URL")
    key = _require_env("INTERNAL_API_KEY")

    table = (os.getenv("PLAYERS_TABLE") or "players_import_2025_bowman_draft").strip()
    col = (os.getenv("PLAYER_COL") or "playerName").strip()

    workflow_root = Path(__file__).resolve().parent
    run_dir = workflow_root / "data" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    players = list(_iter_players_from_worker(base, key, table, col))

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
        w.writerow([col])
        for p in uniq:
            w.writerow([p])

    print(f"RUN_ID={run_id}")
    print(f"SOURCE=worker")
    print(f"TABLE={table}")
    print(f"PLAYER_COL={col}")
    print(f"PLAYERS_EXPORTED={len(uniq)}")
    print(f"OUT={out_csv}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
