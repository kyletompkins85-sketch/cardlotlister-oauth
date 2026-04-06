"""Fetch term_search_items via Supabase PostgREST (no Worker)."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from cardmatch.worker_fetch import _map_item_to_row


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def search_q_to_sql_ilike(q: str) -> str:
    """Turn '2025 bowman draft' into SQL ILIKE pattern %2025%bowman%draft%."""
    parts = [p for p in re.split(r"\s+", (q or "").strip()) if p]
    if not parts:
        return "%%"
    return "%" + "%".join(parts) + "%"


def fetch_term_search_items_supabase_ilike(
    *,
    title_ilike_pattern: str,
    supabase_url: str | None = None,
    service_role_key: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Paginate GET {SUPABASE_URL}/rest/v1/term_search_items?title=ilike...
    Uses Range header (PostgREST). Requires service role (or policies that allow read).
    """
    base_url = (supabase_url or _require_env("SUPABASE_URL")).rstrip("/")
    key = service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not key or not str(key).strip():
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY)")

    cols = (
        "run_id,item_id,legacy_item_id,title,price,currency,condition,condition_id,"
        "leaf_category_id,item_web_url,seller_username,shipping_cost,shipping_cost_type,fetched_at"
    )
    endpoint = f"{base_url}/rest/v1/term_search_items"
    page_size = 1000
    start = 0
    out: List[Dict[str, Any]] = []

    while True:
        params = urllib.parse.urlencode(
            {
                "select": cols,
                "title": f"ilike.{title_ilike_pattern}",
            }
        )
        url = f"{endpoint}?{params}"
        headers = {
            "apikey": key.strip(),
            "Authorization": f"Bearer {key.strip()}",
            "Range": f"{start}-{start + page_size - 1}",
            "Accept": "application/json",
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                content_range = resp.headers.get("Content-Range") or ""
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Supabase GET failed {e.code}: {text}") from e

        try:
            rows = json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Supabase returned non-JSON: {text[:500]}") from e
        if not isinstance(rows, list):
            raise RuntimeError("Supabase rows were not a list")
        if not rows:
            break

        for it in rows:
            if not isinstance(it, dict):
                continue
            rid = str(it.get("run_id") or "").strip()
            out.append(_map_item_to_row(rid, it))

        # Content-Range: 0-999/42000 or */0 when empty
        total: int | None = None
        if "/" in content_range:
            try:
                total = int(content_range.split("/")[-1].strip())
            except ValueError:
                total = None

        if len(rows) < page_size:
            break
        if total is not None and start + len(rows) >= total:
            break
        start += page_size

    return out


def fetch_term_search_items_full_search(q: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Prefer Worker termSearchItems/search; if WORKER env is missing, use Supabase REST.
    Returns (source_label, rows).
    """
    from cardmatch.worker_fetch import fetch_term_search_items_by_search_query

    has_worker = bool(os.getenv("WORKER_BASE_URL") and os.getenv("INTERNAL_API_KEY"))
    has_sb = bool(
        os.getenv("SUPABASE_URL")
        and (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY"))
    )
    if has_worker:
        return "worker `termSearchItems/search`", fetch_term_search_items_by_search_query(q)
    if has_sb:
        pat = search_q_to_sql_ilike(q)
        return "Supabase `rest/v1/term_search_items` (title ilike)", fetch_term_search_items_supabase_ilike(
            title_ilike_pattern=pat
        )
    raise RuntimeError(
        "Set WORKER_BASE_URL and INTERNAL_API_KEY, or SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
        "(see .env.example and cardmatch/README.md)."
    )
