import argparse
import csv
import re
from pathlib import Path



def build_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--set-key", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--product", required=True)
    return parser.parse_args()


CARD_COUNT_PATTERN = re.compile(r"^(\d+)\s+cards?$", re.IGNORECASE)
CHECKLIST_ROW_PATTERN = re.compile(r"^([A-Za-z0-9\-]+)\s+(.+?)(?:\t+|\s{2,})(.+)$")


def is_likely_section_header(line: str) -> bool:
    if not line:
        return False
    if CARD_COUNT_PATTERN.match(line):
        return False
    if CHECKLIST_ROW_PATTERN.match(line):
        return False
    return True


def parse_checklist_file(
    raw_file: Path,
    set_key: str,
    year: int,
    brand: str,
    product: str,
) -> list[dict]:
    rows = []
    current_section = None
    current_section_card_count = None

    with raw_file.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line:
                continue

            card_count_match = CARD_COUNT_PATTERN.match(line)
            if card_count_match:
                current_section_card_count = int(card_count_match.group(1))
                continue

            checklist_match = CHECKLIST_ROW_PATTERN.match(line)
            if checklist_match:
                card_number = checklist_match.group(1).strip()
                player_name_raw = checklist_match.group(2).strip()
                affiliation_raw = checklist_match.group(3).strip()

                rows.append(
                    {
                        "set_key": set_key,
                        "year": year,
                        "brand": brand,
                        "product": product,
                        "section": current_section,
                        "section_card_count": current_section_card_count,
                        "card_number": card_number,
                        "player_name_raw": player_name_raw,
                        "affiliation_raw": affiliation_raw,
                        "raw_line": line,
                        "is_multi_player": "/" in player_name_raw,
                    }
                )
                continue

            if is_likely_section_header(line):
                current_section = line
                current_section_card_count = None

    return rows


def write_csv(rows: list[dict], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
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
    ]

    with output_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = build_parser()

    raw_file = Path(args.raw_file)
    output_file = Path(args.output_file)

    rows = parse_checklist_file(
        raw_file=raw_file,
        set_key=args.set_key,
        year=args.year,
        brand=args.brand,
        product=args.product,
    )

    write_csv(rows, output_file)
    print(f"Wrote {len(rows)} rows to {output_file}")


if __name__ == "__main__":
    main()
