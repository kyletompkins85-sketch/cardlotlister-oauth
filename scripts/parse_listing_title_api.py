#!/usr/bin/env python3
"""
HTTP API: batch-parse eBay listing titles via parse_listing_title().

POST /parse-listing-titles  {"titles": ["...", "..."]}
  → {"ok": true, "results": [{...}, ...]}  (1:1 order; card_count → parsed_card_count)

GET /health  → {"ok": true}

Auth (when PARSER_API_KEY is set):
  Authorization: Bearer <key>   or   ?apiKey=<key>

Railway: set start command to ``python scripts/parse_listing_title_api.py`` and
install ``pip install -r requirements-parse-api.txt``. ``PORT`` is set automatically.
"""
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from parse_listing_title import parse_listing_title  # noqa: E402

_MAX_TITLES = 500


def _to_api_result(parsed: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(parsed)
    if "card_count" in out:
        out["parsed_card_count"] = out.pop("card_count")
    return out


def _extract_api_key(
    authorization: Optional[str],
    api_key_query: Optional[str],
) -> Optional[str]:
    if api_key_query:
        return api_key_query.strip()
    if authorization:
        prefix = "Bearer "
        if authorization.startswith(prefix):
            token = authorization[len(prefix) :].strip()
            return token or None
    return None


def _check_auth(provided: Optional[str], expected: str) -> bool:
    if not expected:
        return True
    if not provided:
        return False
    # Constant-time compare not critical for API keys over TLS, but avoid timing leaks anyway.
    import hmac

    return hmac.compare_digest(provided, expected)


def main() -> None:
    try:
        from fastapi import FastAPI, Query
        from starlette.requests import Request
        from fastapi.responses import JSONResponse
        import uvicorn
    except ImportError as e:
        raise SystemExit(
            "Install: pip install -r requirements-parse-api.txt\n" + str(e)
        ) from e

    parser_api_key = (os.environ.get("PARSER_API_KEY") or "").strip()

    app = FastAPI(title="Listing title parser", version="1.0.0")

    @app.get("/health")
    def health() -> dict:
        return {"ok": True}

    @app.post("/parse-listing-titles")
    async def parse_listing_titles(
        req: Request,
        api_key: Optional[str] = Query(default=None, alias="apiKey"),
    ) -> JSONResponse:
        if not parser_api_key:
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "error": "Server misconfigured: PARSER_API_KEY not set.",
                },
            )

        auth_header = req.headers.get("Authorization")
        if not _check_auth(_extract_api_key(auth_header, api_key), parser_api_key):
            return JSONResponse(
                status_code=401,
                content={"ok": False, "error": "Unauthorized."},
            )

        try:
            body = await req.json()
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Invalid JSON body."},
            )

        if not isinstance(body, dict):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "Request body must be a JSON object."},
            )

        raw_titles = body.get("titles")
        if raw_titles is None:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": 'Missing "titles" array.'},
            )
        if not isinstance(raw_titles, list):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": '"titles" must be an array.'},
            )

        if len(raw_titles) == 0:
            return JSONResponse(status_code=200, content={"ok": True, "results": []})

        if len(raw_titles) > _MAX_TITLES:
            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "error": f"At most {_MAX_TITLES} titles per request.",
                },
            )

        try:
            results = []
            for title in raw_titles:
                if not isinstance(title, str):
                    return JSONResponse(
                        status_code=400,
                        content={"ok": False, "error": "Each title must be a string."},
                    )
                parsed = parse_listing_title(title)
                results.append(_to_api_result(parsed))
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"ok": False, "error": f"Title parsing failed: {e}"},
            )

        return JSONResponse(status_code=200, content={"ok": True, "results": results})

    port = int(os.environ.get("PARSER_API_PORT") or os.environ.get("PORT", "8766"))
    host = os.environ.get("PARSER_API_HOST")
    if host is None:
        host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
