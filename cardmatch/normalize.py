from __future__ import annotations


def normalize_title(s: str) -> str:
    return (s or "").strip()
