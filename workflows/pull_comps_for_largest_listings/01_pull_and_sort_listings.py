# workflows/pull_comps_for_largest_listings/01_pull_and_sort_listings.py
"""
Step 01 — Pull listings from your Worker endpoint (/internal/listings/search),
sort largest->smallest by all-in price (price + shipping_cost),
and write a dataset JSON into <repo_root>/data/.

Env vars:
  WORKER_BASE_URL    e.g. https://...workers.dev
  INTERNAL_API_KEY   secret key for x-internal-key
  QUERY              optional; default "2025 Topps Update"
  LIMIT              optional; default 1000
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode, urljoin

import requests


@dataclass
class Config:
    base_url: str
    api_key: str
    query: str
    limit: int


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _safe_slug(s: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (s or "all").lower())
    slug = re.sub(r"^_+|_+$", "", slug)
    return slug or "all"


def _to_number(x: Any) -> float:
    """Convert numbers / numeric strings / '$12.34' to float."""
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return 0.0
        s = s.replace(",", "")
        s = re.sub(r"[^0-9.\-]", "", s)
        try:
            return float(s)
        except ValueError:
            return 0.0
    return 0.0


def _find_repo_root(start: Path) -> Path:
    """
    Walk upward until we find a folder that looks like the repo root.
    Prefer .git, but also accept common repo markers.
    """
    markers = {".git", ".github", "pyproject.toml", "package.json"}
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        for m in markers:
            if (p / m).exists():
                return p
    # fallback: current working directory
    return Path.cwd().resolve()


def fetch_page(cfg: Config, offset: int) -> Dict[str, Any]:
    params = {"limit": str(cfg.limit), "offset": str(offset)}
    if cfg.query and cfg.query.strip():
        params["q"] = cfg.query.strip()

    url = urljoin(cfg.base_url.rstrip("/") + "/", "internal/listings/search")
    url = f"{url}?{urlencode(params)}"

    resp = requests.get(url, headers={"x-internal-key": cfg.api_key}, timeout=60)

    text = resp.text
    try:
        data = resp.json()
    except Exception:
        data = {"raw": text}

    if not resp.ok:
        raise RuntimeError(f"Worker request failed {resp.status_code}: {text}")

    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response type: {type(data)}")

    return data


def compute_all_in(row: Dict[str, Any]) -> float:
    return _to_number(row.get("price")) + _to_number(row.get("shipping_cost"))


def main() -> None:
    base = _require_env("WORKER_BASE_URL")
    key = _require_env("INTERNAL_API_KEY")
    query = os.getenv("QUERY", "2025 Topps Update")
    limit = int(os.getenv("LIMIT", "1000"))

    cfg = Config(base_url=base, api_key=key, query=query, limit=limit)

    offset = 0
    rows: List[Dict[str, Any]] = []

    while True:
        page = fetch_page(cfg, offset)
        page_rows = page.get("rows") or []
        if not isinstance(page_rows, list):
            raise RuntimeError("Response 'rows' was not a list")

        for r in page_rows:
            if isinstance(r, dict):
                rows.append(r)

        next_offset = page.get("next_offset")
        if not next_offset:
            break
        offset = int(next_offset)

    # compute + sort descending
    for r in rows:
        r["all_in"] = compute_all_in(r)

    rows_sorted = sorted(rows, key=lambda r: _to_number(r.get("all_in")), reverse=True)

    repo_root = _find_repo_root(Path(__file__).parent)
    out_dir = repo_root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_q = _safe_slug(query)
    out_path = out_dir / f"listings_{safe_q}_sorted.json"

    payload = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "count": len(rows_sorted),
        "rows": rows_sorted,
    }

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows_sorted)} rows to {out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
