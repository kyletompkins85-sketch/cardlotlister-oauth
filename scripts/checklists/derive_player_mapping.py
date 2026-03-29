"""Layer 4: player-set presence rollup from Layer 3 (grouped by lightly normalized name)."""

import argparse
import csv
import re
import sys
from pathlib import Path

# Keep aligned with derive_player_linked.L3_FIELDNAMES
L3_FIELDNAMES = [
    "set_key",
    "year",
    "brand",
    "product",
    "section",
    "section_card_count",
    "card_number",
    "player_slot",
    "player_name_raw",
    "affiliation_raw",
    "is_multi_player",
    "raw_line",
]

L4_FIELDNAMES = [
    "set_key",
    "year",
    "brand",
    "product",
    "player_name_key",
    "player_name_display",
    "card_count",
    "section_count",
    "sections",
    "affiliation_count",
    "affiliations",
]

_WS = re.compile(r"\s+")


def normalize_player_name_key(name: str) -> str:
    """Light normalization for grouping: trim, collapse spaces, strip trailing comma, casefold."""
    t = (name or "").strip()
    t = _WS.sub(" ", t)
    t = t.rstrip(",").strip()
    return t.casefold()


def row_sort_key(row: dict) -> tuple[str, int]:
    slot = row.get("player_slot") or "1"
    try:
        slot_n = int(slot)
    except ValueError:
        slot_n = 1
    return (row.get("card_number") or "", slot_n)


def rollup_from_l3(rows: list[dict]) -> list[dict]:
    """One output row per (set_key, player_name_key)."""
    groups: dict[tuple[str, str], dict] = {}

    for row in rows:
        raw_name = row.get("player_name_raw") or ""
        pkey = normalize_player_name_key(raw_name)
        if not pkey:
            print(
                f"Warning: skipping row with empty name after normalization "
                f"(card {row.get('card_number')!r}).",
                file=sys.stderr,
            )
            continue

        sk = row.get("set_key") or ""
        gk = (sk, pkey)
        if gk not in groups:
            groups[gk] = {
                "set_key": sk,
                "player_name_key": pkey,
                "year": row.get("year", ""),
                "brand": row.get("brand", ""),
                "product": row.get("product", ""),
                "cards": set(),
                "sections": set(),
                "affiliations": set(),
                "display_pick": None,
            }
        g = groups[gk]

        for field in ("year", "brand", "product"):
            incoming = row.get(field, "")
            if g[field] != incoming and incoming not in ("", None):
                if g[field] not in ("", None) and str(g[field]) != str(incoming):
                    print(
                        f"Warning: inconsistent {field} for set_key={sk!r} "
                        f"player_name_key={pkey!r}: {g[field]!r} vs {incoming!r} (keeping first).",
                        file=sys.stderr,
                    )
                elif g[field] in ("", None):
                    g[field] = incoming

        cn = (row.get("card_number") or "").strip()
        if cn:
            g["cards"].add(cn)
        sec = (row.get("section") or "").strip()
        if sec:
            g["sections"].add(sec)
        aff = (row.get("affiliation_raw") or "").strip()
        if aff:
            g["affiliations"].add(aff)

        sk_row = row_sort_key(row)
        cand = (sk_row, raw_name.strip())
        if g["display_pick"] is None or cand[0] < g["display_pick"][0]:
            g["display_pick"] = cand

    out: list[dict] = []
    for g in sorted(
        groups.values(),
        key=lambda x: (x["set_key"], x["player_name_key"]),
    ):
        pick = g["display_pick"]
        display = (pick[1] if pick else "").rstrip(",").strip()
        out.append(
            {
                "set_key": g["set_key"],
                "year": g["year"],
                "brand": g["brand"],
                "product": g["product"],
                "player_name_key": g["player_name_key"],
                "player_name_display": display,
                "card_count": len(g["cards"]),
                "section_count": len(g["sections"]),
                "sections": "|".join(sorted(g["sections"])),
                "affiliation_count": len(g["affiliations"]),
                "affiliations": "|".join(sorted(g["affiliations"])),
            }
        )
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Layer 4 player-set presence rollup from Layer 3 player_linked CSV."
    )
    parser.add_argument("--input", required=True, help="Path to Layer 3 player_linked CSV")
    parser.add_argument("--output", required=True, help="Path to write Layer 4 CSV")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open(newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        missing = [c for c in L3_FIELDNAMES if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(
                f"Input CSV missing required columns: {missing}. Found: {reader.fieldnames!r}"
            )
        rows = list(reader)

    out_rows = rollup_from_l3(rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=L4_FIELDNAMES)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rollup rows to {output_path} (from {len(rows)} Layer 3 rows)")


if __name__ == "__main__":
    main()
