# Cmd+F: GH_ANCHOR_PRODUCT_PLAYER_RANKINGS_STEP01_2C7B9D10
"""
Step 01 — For a PRODUCT, pull players (from Supabase via Worker) and run eBay searches via:
  POST /comps/batchPlayers

This Worker endpoint inserts:
  - term_search_runs
  - term_search_items

Writes:
  workflows/product_player_price_rankings/data/<RUN_ID>/
    - product_players_search_summary.json
    - product_players_search_summary.csv

Env vars required:
  WORKER_BASE_URL
  INTERNAL_API_KEY
  RUN_ID

Optional:
  PRODUCT_NAME (label only)
  PLAYERS_TABLE (default players_import_2025_bowman_draft)
  PREFIX (default "2025 Bowman Draft")
  MAX_PLAYERS_TOTAL (default 50)
  MAX_PLAYERS_PER_CALL (default 5)
  EBAY_LIMIT (default 200)
  EBAY_OFFSET (default 0)
  EBAY_PAUSE_MS (default 250)
  MAX_RETRIES_429 (default 3)
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import requests


@dataclass
class Config:
    base_url: str
    api_key: str
    run_id: str
    product_name: str
    players_table: str
    prefix: str
    max_players_total: int
    max_players_per_call: int
    ebay_limit: int
    ebay_offset: int
    pause_ms: int


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _to_int_env(name: str, default: int) -> int:
    s = (os.getenv(name) or "").strip()
    if not s:
        return default
    try:
        return int(float(s))
    except Exception:
        return default


def _safe_slug(s: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (s or "product").lower()).strip("_")
    return slug or "product"


def _post_json(url: str, key: str, body: Dict[str, Any]) -> Dict[str, Any]:
    # Cmd+F: GH_ANCHOR_WORKER_POST_JSON_RETRY_429_0F6A1B22
    max_retries_429 = _to_int_env("MAX_RETRIES_429", 3)
    backoffs_s = [2, 5, 10]

    attempt = 0
    while True:
        resp = requests.post(
            url,
            headers={"x-internal-key": key, "Content-Type": "application/json"},
            data=json.dumps(body),
            timeout=180,
        )

        text = resp.text
        try:
            data = resp.json()
        except Exception:
            data = {"raw": text}

        if resp.status_code == 429 and attempt < max_retries_429:
            wait_s = backoffs_s[min(attempt, len(backoffs_s) - 1)]
            time.sleep(wait_s)
            attempt += 1
            continue

        if not resp.ok:
            raise RuntimeError(f"Worker POST failed {resp.status_code}: {text}")
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected response type: {type(data)}")
        return data


def main() -> None:
    base = _require_env("WORKER_BASE_URL").rstrip("/")
    key = _require_env("INTERNAL_API_KEY")
    run_id = _require_env("RUN_ID")

    product_name = (os.getenv("PRODUCT_NAME") or "product").strip()

    cfg = Config(
        base_url=base,
        api_key=key,
        run_id=run_id,
        product_name=product_name,
        players_table=(os.getenv("PLAYERS_TABLE") or "players_import_2025_bowman_draft").strip(),
        prefix=(os.getenv("PREFIX") or product_name or "2025 Bowman Draft").strip(),
        max_players_total=max(1, _to_int_env("MAX_PLAYERS_TOTAL", 50)),
        max_players_per_call=max(1, min(10, _to_int_env("MAX_PLAYERS_PER_CALL", 5))),
        ebay_limit=max(1, min(200, _to_int_env("EBAY_LIMIT", 200))),
        ebay_offset=max(0, _to_int_env("EBAY_OFFSET", 0)),
        pause_ms=max(0, _to_int_env("EBAY_PAUSE_MS", 250)),
    )

    workflow_root = Path(__file__).resolve().parent
    out_dir = workflow_root / "data" / cfg.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    batch_url = f"{cfg.base_url}/comps/batchPlayers"

    processed_rows: List[Dict[str, Any]] = []
    run_ids: List[str] = []

    players_offset = 0
    total_processed_players = 0

    # Cmd+F: GH_ANCHOR_PRODUCT_PLAYERS_PAGINATION_LOOP_8D11C0A2
    while total_processed_players < cfg.max_players_total:
        remaining = cfg.max_players_total - total_processed_players
        this_batch = max(1, min(cfg.max_players_per_call, remaining))

        body = {
            "players_table": cfg.players_table,
            "prefix": cfg.prefix,
            "max_players": this_batch,
            "players_offset": players_offset,
            "limit": cfg.ebay_limit,
            "offset": cfg.ebay_offset,
        }

        resp = _post_json(batch_url, cfg.api_key, body)

        processed = resp.get("processed") or []
        next_offset = resp.get("next_players_offset")

        if isinstance(processed, list):
            for p in processed:
                if isinstance(p, dict):
                    processed_rows.append(p)
                    rid = (p.get("run_id") or "").strip()
                    if rid:
                        run_ids.append(rid)

        processed_count = int(resp.get("processed_count") or (len(processed) if isinstance(processed, list) else 0))

        total_processed_players += processed_count

        if processed_count <= 0:
            break

        if next_offset is None:
            players_offset += processed_count
        else:
            try:
                players_offset = int(next_offset)
            except Exception:
                players_offset += processed_count

        if cfg.pause_ms > 0:
            time.sleep(cfg.pause_ms / 1000.0)

    run_ids_unique = sorted(set([r for r in run_ids if r]))

    safe_product = _safe_slug(cfg.product_name)

    json_path = out_dir / f"product_players_search_summary_{safe_product}.json"
    csv_path = out_dir / f"product_players_search_summary_{safe_product}.csv"

    payload = {
        "run_id": cfg.run_id,
        "product_name": cfg.product_name,
        "players_table": cfg.players_table,
        "prefix": cfg.prefix,
        "max_players_total": cfg.max_players_total,
        "max_players_per_call": cfg.max_players_per_call,
        "ebay_limit": cfg.ebay_limit,
        "ebay_offset": cfg.ebay_offset,
        "processed_count": len(processed_rows),
        "unique_term_search_run_ids": run_ids_unique,
        "processed": processed_rows,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    fieldnames = [
        "cardNumber",
        "playerName",
        "team",
        "query",
        "run_id",
        "total",
        "returned",
        "inserted_items",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in processed_rows:
            w.writerow({k: r.get(k) for k in fieldnames})

    print(f"Wrote Step 01 JSON: {json_path}")
    print(f"Wrote Step 01 CSV:  {csv_path}")
    print(f"Unique term_search_runs: {len(run_ids_unique)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
