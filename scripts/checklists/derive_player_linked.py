import argparse
import csv
import sys
from pathlib import Path


L2_REQUIRED = (
    "set_key",
    "year",
    "brand",
    "product",
    "section",
    "section_card_count",
    "card_number",
    "player_name_raw",
    "affiliation_raw",
    "raw_line",
    "is_multi_player",
)

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Derive Layer 3 (player-linked) rows from Layer 2 normalized checklist CSV."
    )
    parser.add_argument("--input", required=True, help="Path to Layer 2 normalized CSV")
    parser.add_argument("--output", required=True, help="Path to write Layer 3 CSV")
    return parser.parse_args()


def row_is_multi_player(row: dict) -> bool:
    v = row.get("is_multi_player", "")
    return str(v).lower() in ("true", "1")


def _strip_rc_suffix(s: str) -> str:
    """Remove trailing checklist ' RC' from a team token (e.g. Heritage quad lines)."""
    t = s.strip()
    if t.endswith(" RC"):
        t = t[:-3].strip()
    return t


def split_multi_player_parts(row: dict) -> list[tuple[str, str, int]]:
    """Return (player_name, affiliation, player_slot) for each slot."""
    name_raw = row.get("player_name_raw") or ""
    aff_raw = row.get("affiliation_raw") or ""
    names = [p.strip() for p in name_raw.split("/") if p.strip()]
    if not names:
        return []

    aff_raw = _strip_rc_suffix(aff_raw)
    if "/" in aff_raw:
        affs = [_strip_rc_suffix(p) for p in aff_raw.split("/")]
    else:
        affs = [_strip_rc_suffix(aff_raw)] * len(names)

    if len(affs) < len(names) and affs:
        print(
            f"Warning: fewer affiliation part(s) than name part(s) for card "
            f"{row.get('card_number')!r}: {len(names)} names vs {len(affs)} teams; "
            f"padding with last team.",
            file=sys.stderr,
        )
        while len(affs) < len(names):
            affs.append(affs[-1])

    if len(affs) > len(names):
        n = len(names)
        print(
            f"Warning: more affiliation part(s) than name part(s) for card "
            f"{row.get('card_number')!r}: {len(names)} names vs {len(affs)} teams; truncating teams.",
            file=sys.stderr,
        )
        affs = affs[:n]

    return [(names[i], affs[i], i + 1) for i in range(len(names))]


def l2_row_to_l3_rows(row: dict) -> list[dict]:
    multi = row_is_multi_player(row)
    base_keys = {
        "set_key": row["set_key"],
        "year": row["year"],
        "brand": row["brand"],
        "product": row["product"],
        "section": row["section"],
        "section_card_count": row["section_card_count"],
        "card_number": row["card_number"],
        "raw_line": row["raw_line"],
    }

    if not multi:
        return [
            {
                **base_keys,
                "player_slot": 1,
                "player_name_raw": row["player_name_raw"],
                "affiliation_raw": row["affiliation_raw"],
                "is_multi_player": multi,
            }
        ]

    parts = split_multi_player_parts(row)
    if not parts:
        print(
            f"Warning: is_multi_player but no name parts after split for card "
            f"{row.get('card_number')!r}; skipping.",
            file=sys.stderr,
        )
        return []

    out = []
    for name, aff, slot in parts:
        out.append(
            {
                **base_keys,
                "player_slot": slot,
                "player_name_raw": name,
                "affiliation_raw": aff,
                "is_multi_player": True,
            }
        )
    return out


def derive_player_linked(input_path: Path) -> list[dict]:
    with input_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in L2_REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(
                f"Input CSV missing required columns: {missing}. Found: {reader.fieldnames!r}"
            )
        rows: list[dict] = []
        for row in reader:
            rows.extend(l2_row_to_l3_rows(row))
    return rows


def write_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=L3_FIELDNAMES)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in L3_FIELDNAMES})


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    rows = derive_player_linked(input_path)
    write_csv(rows, output_path)
    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
