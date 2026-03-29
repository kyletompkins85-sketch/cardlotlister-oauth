"""Presentation layer: one row per player, set presence as columns (from Layer 4 CSVs)."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

# Columns read from Layer 4 (derive_player_mapping output); keep aligned with L4_FIELDNAMES there.
L4_READ = ("set_key", "player_name_key", "player_name_display", "card_count")

WIDE_PREFIX = ("player_name_key", "player_name_display", "set_count", "total_cards")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a wide CSV: one row per player_name_key, one column per set_key "
            "(cell = card_count in that set). Reads all *.csv in --input-dir."
        )
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/checklists/player_mapping"),
        help="Directory containing Layer 4 player_mapping CSV files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/checklists/player_presence_wide/players_wide.csv"),
        help="Path for the wide presentation CSV",
    )
    return parser.parse_args()


def _parse_card_count(raw: str) -> int:
    raw = (raw or "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def load_player_set_counts(input_dir: Path) -> tuple[dict[str, dict], set[str]]:
    """
    Returns:
      players: player_name_key -> {"display": str, "sets": {set_key: card_count}}
      all_set_keys: every set_key seen
    """
    files = sorted(input_dir.glob("*.csv"))
    if not files:
        raise SystemExit(f"No CSV files found in {input_dir.resolve()}")

    players: dict[str, dict] = {}
    all_set_keys: set[str] = set()

    for path in files:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            missing = [c for c in L4_READ if c not in (reader.fieldnames or [])]
            if missing:
                raise SystemExit(
                    f"{path}: missing columns {missing}; have {reader.fieldnames!r}"
                )
            for row in reader:
                sk = (row.get("set_key") or "").strip()
                pkey = (row.get("player_name_key") or "").strip()
                display = (row.get("player_name_display") or "").strip()
                n = _parse_card_count(row.get("card_count", ""))
                if not pkey or not sk:
                    continue
                all_set_keys.add(sk)
                if pkey not in players:
                    players[pkey] = {"display": display, "sets": {}}
                elif display:
                    prev = players[pkey]["display"]
                    players[pkey]["display"] = display if not prev else min(prev, display)

                sets = players[pkey]["sets"]
                sets[sk] = sets.get(sk, 0) + n

    return players, all_set_keys


def build_wide_rows(
    players: dict[str, dict], set_columns: list[str]
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for pkey in sorted(players.keys()):
        p = players[pkey]
        sets = p["sets"]
        total = sum(sets.values())
        row: dict[str, str | int] = {
            "player_name_key": pkey,
            "player_name_display": p["display"],
            "set_count": len(sets),
            "total_cards": total,
        }
        for sk in set_columns:
            v = sets.get(sk)
            row[sk] = v if v is not None and v > 0 else ""
        rows.append(row)
    return rows


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir
    output_path = args.output

    players, all_set_keys = load_player_set_counts(input_dir)
    set_columns = sorted(all_set_keys)
    fieldnames = list(WIDE_PREFIX) + set_columns

    out_rows = build_wide_rows(players, set_columns)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in out_rows:
            w.writerow(row)

    print(
        f"Wrote {len(out_rows)} players x {len(set_columns)} set columns to {output_path}"
    )


if __name__ == "__main__":
    main()
