import csv
import re
from pathlib import Path


RAW_FILE = Path("data/checklists/raw/2025_Bowman_Draft_Raw.txt")
OUTPUT_FILE = Path("data/checklists/normalized/2025_Bowman_Draft_Normalized.csv")

SET_KEY = "2025_bowman_draft"
YEAR = 2025
BRAND = "Bowman"
PRODUCT = "Draft"


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


def parse_checklist_file(raw_file: Path) -> list[dict]:
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
                        "set_key": SET_KEY,
                        "year": YEAR,
                        "brand": BRAND,
                        "product": PRODUCT,
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
    rows = parse_checklist_file(RAW_FILE)
    write_csv(rows, OUTPUT_FILE)
    print(f"Wrote {len(rows)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
