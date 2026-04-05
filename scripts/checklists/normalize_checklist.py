import argparse
import csv
import re
from pathlib import Path
from typing import Optional



def build_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-file", required=True)
    parser.add_argument("--output-file", required=True)
    parser.add_argument("--set-key", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--product", required=True)
    return parser.parse_args()


CARD_COUNT_PATTERN = re.compile(r"^(\d+)\s+cards?\.?\s*$", re.IGNORECASE)
CHECKLIST_ROW_PATTERN = re.compile(r"^([A-Za-z0-9\-]+)\s+(.+?)(?:\t+|\s{2,})(.+)$")
# Insert-pack odds (e.g. "1:33 packs", "1:7,665 packs"); not a checklist section.
PACK_ODDS_LINE_PATTERN = re.compile(r"^\d+:\s*[\d,]+")


def looks_like_card_catalog_id(s: str) -> bool:
    """True if the first tab field looks like a catalog number, not a section label."""
    s = s.strip()
    if not s or any(c.isspace() for c in s):
        return False
    if s.isdigit():
        return True
    if re.match(r"^[A-Za-z]{1,10}\d", s):
        return True
    if re.search(r"\d", s) and "-" in s:
        return True
    return False


def try_parse_tab_checklist_row(
    line: str,
    current_section: Optional[str],
    current_section_card_count: Optional[int],
) -> Optional[dict]:
    """
    Tab-delimited rows: either card\\tname\\taffiliation (3+ fields, first is catalog id)
    or section\\tcard\\tname\\taffiliation+ (4+ fields, first is not a catalog id).
    """
    parts = [p.strip() for p in line.split("\t")]
    while parts and parts[-1] == "":
        parts.pop()
    if len(parts) >= 4:
        if looks_like_card_catalog_id(parts[0]):
            card_number = parts[0]
            player_name_raw = parts[1]
            affiliation_raw = "\t".join(parts[2:])
            section = current_section
        else:
            section = parts[0]
            card_number = parts[1]
            player_name_raw = parts[2]
            affiliation_raw = "\t".join(parts[3:])
        return {
            "section": section,
            "section_card_count": current_section_card_count,
            "card_number": card_number,
            "player_name_raw": player_name_raw,
            "affiliation_raw": affiliation_raw,
            "raw_line": line,
            "is_multi_player": "/" in player_name_raw,
        }
    if len(parts) == 3:
        return {
            "section": current_section,
            "section_card_count": current_section_card_count,
            "card_number": parts[0],
            "player_name_raw": parts[1],
            "affiliation_raw": parts[2],
            "raw_line": line,
            "is_multi_player": "/" in parts[1],
        }
    if len(parts) == 2:
        # Name + team only (no catalog id), e.g. Fanatics redemption lists:
        # "Bryce Harper\tPhiladelphia Phillies," — must not match CHECKLIST_ROW_PATTERN.
        if looks_like_card_catalog_id(parts[0]):
            return None
        aff = parts[1].rstrip(",").strip()
        return {
            "section": current_section,
            "section_card_count": current_section_card_count,
            "card_number": "",
            "player_name_raw": parts[0],
            "affiliation_raw": aff,
            "raw_line": line,
            "is_multi_player": "/" in parts[0],
        }
    return None


def is_pack_odds_line(line: str) -> bool:
    return bool(PACK_ODDS_LINE_PATTERN.match(line))


def is_likely_section_header(line: str) -> bool:
    if not line:
        return False
    if CARD_COUNT_PATTERN.match(line):
        return False
    if CHECKLIST_ROW_PATTERN.match(line):
        return False
    if is_pack_odds_line(line):
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
    parallel_catalog_mode = False
    section_before_parallels: Optional[str] = None
    # After "Parallels", Topps checklists often have a blank line before the parallel-name list.
    # That blank must not end parallel-catalog mode (or the next lines become section headers).
    parallels_skip_one_blank = False

    with raw_file.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line:
                if parallel_catalog_mode:
                    if parallels_skip_one_blank:
                        parallels_skip_one_blank = False
                        continue
                    parallel_catalog_mode = False
                    if section_before_parallels is not None:
                        current_section = section_before_parallels
                    elif current_section_card_count is not None:
                        current_section = "Base"
                    section_before_parallels = None
                continue

            card_count_match = CARD_COUNT_PATTERN.match(line)
            if card_count_match:
                current_section_card_count = int(card_count_match.group(1))
                continue

            if line.lower() == "parallels":
                parallel_catalog_mode = True
                section_before_parallels = current_section
                parallels_skip_one_blank = True
                continue

            if parallel_catalog_mode:
                sec_for_row = (
                    section_before_parallels
                    if section_before_parallels is not None
                    else "Base"
                )
                tab_row = try_parse_tab_checklist_row(
                    line, sec_for_row, current_section_card_count
                )
                if tab_row is not None:
                    parallel_catalog_mode = False
                    current_section = sec_for_row
                    section_before_parallels = None
                    rows.append(
                        {
                            "set_key": set_key,
                            "year": year,
                            "brand": brand,
                            "product": product,
                            **tab_row,
                        }
                    )
                continue

            if is_pack_odds_line(line):
                continue

            tab_row = try_parse_tab_checklist_row(
                line, current_section, current_section_card_count
            )
            if tab_row is not None:
                rows.append(
                    {
                        "set_key": set_key,
                        "year": year,
                        "brand": brand,
                        "product": product,
                        **tab_row,
                    }
                )
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
