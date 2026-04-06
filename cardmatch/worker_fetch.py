"""Fetch term_search_items from the Worker (same contract as workflows/.../02_export_term_search_items.py)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Sequence, Set, Tuple


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v or not v.strip():
        raise RuntimeError(f"Missing {name}")
    return v.strip()


def _get_json(url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Worker GET failed {e.code}: {text}") from e
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"raw": text}
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response type: {type(data)}")
    return data


def _map_item_to_row(source_run_id: str, it: Dict[str, Any]) -> Dict[str, Any]:
    """Same row shape as workflows/.../02_export_term_search_items.py."""
    return {
        "source_run_id": source_run_id,
        "run_id": it.get("run_id"),
        "item_id": it.get("item_id"),
        "legacy_item_id": it.get("legacy_item_id"),
        "title": it.get("title"),
        "price": it.get("price"),
        "currency": it.get("currency"),
        "condition": it.get("condition"),
        "condition_id": it.get("condition_id"),
        "leaf_category_id": it.get("leaf_category_id"),
        "item_web_url": it.get("item_web_url"),
        "seller_username": it.get("seller_username"),
        "shipping_cost": it.get("shipping_cost"),
        "shipping_cost_type": it.get("shipping_cost_type"),
        "fetched_at": it.get("fetched_at"),
    }


def filter_rows_exclude_title_substrings(
    rows: List[Dict[str, Any]],
    substrings: Sequence[str],
) -> List[Dict[str, Any]]:
    """Drop rows whose title contains any of the substrings (case-insensitive)."""
    if not substrings:
        return rows
    needles = [s.lower() for s in substrings if (s or "").strip()]
    if not needles:
        return rows
    out: List[Dict[str, Any]] = []
    for r in rows:
        t = (r.get("title") or "").lower()
        if any(n in t for n in needles):
            continue
        out.append(r)
    return out


def dedupe_rows_by_run_and_item(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stable dedupe on (run_id, item_id) when both present; else keep order."""
    seen: Set[Tuple[str, str]] = set()
    out: List[Dict[str, Any]] = []
    for r in rows:
        rid = str(r.get("run_id") or "").strip()
        iid = str(r.get("item_id") or "").strip()
        key = (rid, iid)
        if iid and key in seen:
            continue
        if iid:
            seen.add(key)
        out.append(r)
    return out


def fetch_term_search_items_by_run(
    run_id: str,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Paginate GET /internal/termSearchItems/byRun for one term_search run_id.
    Returns rows shaped like 02_export_term_search_items CSV rows.
    """
    base = (base_url or _require_env("WORKER_BASE_URL")).rstrip("/")
    key = api_key or _require_env("INTERNAL_API_KEY")
    headers = {"x-internal-key": key}

    out: List[Dict[str, Any]] = []
    offset = 0
    while True:
        params = urllib.parse.urlencode({"run_id": run_id, "limit": "1000", "offset": str(offset)})
        endpoint = f"{base}/internal/termSearchItems/byRun"
        url = f"{endpoint}?{params}"
        data = _get_json(url, headers=headers)
        rows = data.get("rows") or []
        if not isinstance(rows, list):
            raise RuntimeError("Unexpected rows type")
        for it in rows:
            if not isinstance(it, dict):
                continue
            out.append(_map_item_to_row(run_id, it))
        next_offset = data.get("next_offset")
        if not next_offset:
            break
        offset = int(next_offset)
    return out


def fetch_multiple_runs(run_ids: List[str]) -> List[Dict[str, Any]]:
    all_rows: List[Dict[str, Any]] = []
    for rid in run_ids:
        all_rows.extend(fetch_term_search_items_by_run(rid.strip()))
    return all_rows


def fetch_term_search_items_by_search_query(
    q: str,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Paginate GET /internal/termSearchItems/search?q=... (Supabase-backed, no eBay).
    Same row shape as fetch_term_search_items_by_run.
    """
    base = (base_url or _require_env("WORKER_BASE_URL")).rstrip("/")
    key = api_key or _require_env("INTERNAL_API_KEY")
    headers = {"x-internal-key": key}

    out: List[Dict[str, Any]] = []
    offset = 0
    while True:
        params = urllib.parse.urlencode({"q": q, "limit": "1000", "offset": str(offset)})
        endpoint = f"{base}/internal/termSearchItems/search"
        url = f"{endpoint}?{params}"
        data = _get_json(url, headers=headers)
        rows = data.get("rows") or []
        if not isinstance(rows, list):
            raise RuntimeError("Unexpected rows type")
        for it in rows:
            if not isinstance(it, dict):
                continue
            rid = str(it.get("run_id") or "").strip()
            out.append(_map_item_to_row(rid, it))
        next_offset = data.get("next_offset")
        if not next_offset:
            break
        offset = int(next_offset)
    return out
