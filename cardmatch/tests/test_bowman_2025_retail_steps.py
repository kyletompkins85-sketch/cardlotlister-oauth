from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from cardmatch.bowman_2025_retail_steps import (
    checklist_code_prefixes,
    exclusion_reason,
    extract_checklist_codes,
    load_card_lookup,
    match_listing_to_checklist,
    process_title,
    write_listings_steps12_split_by_match_status,
)


class TestBowman2025RetailSteps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        by_key, names = load_card_lookup()
        cls.by_key = by_key
        cls.prefixes = checklist_code_prefixes(by_key)
        cls.names = names

    def test_exclusion_lot(self):
        self.assertEqual(exclusion_reason("2025 Bowman Aaron Judge 3 Card lot"), "lot")

    def test_exclusion_pick_your(self):
        self.assertEqual(
            exclusion_reason("2025 Bowman Pick Your Card RPAs"),
            "pick_or_volume_header",
        )

    def test_exclusion_pick_and_choose(self):
        self.assertEqual(
            exclusion_reason("Yankees Pick & Choose Mattingly Judge"),
            "pick_or_volume_header",
        )

    def test_exclusion_graded(self):
        self.assertEqual(exclusion_reason("2025 Bowman Aaron Judge PSA 10"), "graded_or_slab")

    def test_exclusion_complete_set(self):
        self.assertEqual(exclusion_reason("2025 Bowman Complete Set 1-100"), "complete_set")

    def test_not_excluded_single(self):
        self.assertEqual(
            exclusion_reason("2025 Bowman Aaron Judge #99 Neon Green /399"),
            "",
        )

    def test_extract_hs_and_hash(self):
        t = "2025 Bowman #HS-11 Aaron Judge Hobby Stars"
        self.assertEqual(extract_checklist_codes(t, self.prefixes), ["HS-11"])

        t2 = "#99 2025 Bowman Aaron Judge Yankees"
        self.assertIn("99", extract_checklist_codes(t2, self.prefixes))

    def test_extract_hash_base_not_serial_fraction(self):
        p = self.prefixes
        self.assertNotIn(
            "116",
            extract_checklist_codes("2025 Bowman Chrome Aaron Judge #116/199 Refractor", p),
        )
        self.assertEqual(
            extract_checklist_codes("2025 Bowman Aaron Judge #116/199", p),
            [],
        )
        self.assertEqual(extract_checklist_codes("Judge #11/25 gold", p), [])

    def test_extract_strict_no_substring_false_positives(self):
        p = self.prefixes
        self.assertEqual(
            extract_checklist_codes("Kansas City Royals 2025 Bowman Chrome Lot", p),
            [],
        )
        self.assertEqual(extract_checklist_codes("2025 Bowman base paper lot", p), [])
        self.assertEqual(extract_checklist_codes("Brett Baty 2025 Bowman Chrome RC", p), [])
        self.assertEqual(extract_checklist_codes("Cracked Ice Refractor parallel", p), [])
        self.assertEqual(extract_checklist_codes("bandana variation SP", p), [])

    def test_extract_glued_digits_still_works(self):
        p = self.prefixes
        self.assertIn("BCP-22", extract_checklist_codes("2025 Bowman Chrome BCP22 JJ Wetherholt", p))
        self.assertIn("HS-11", extract_checklist_codes("Bowman Hobby Stars HS11 Aaron Judge", p))

    def test_match_judge_hs11(self):
        mr = match_listing_to_checklist(
            "2025 Bowman #HS-11 Aaron Judge Hobby Stars Yankees",
            self.by_key,
            self.prefixes,
        )
        self.assertEqual(mr.matched_card_number, "HS-11")
        self.assertEqual(mr.matched_player, "Aaron Judge")
        self.assertEqual(mr.match_status, "matched")

    def test_match_judge_base_99(self):
        mr = match_listing_to_checklist(
            "Aaron Judge 2025 Bowman #99 Neon Green /399",
            self.by_key,
            self.prefixes,
        )
        self.assertEqual(mr.matched_card_number, "99")
        self.assertEqual(mr.matched_player, "Aaron Judge")

    def test_process_excluded_clears_match(self):
        ex, mr = process_title(
            "2025 Bowman Aaron Judge PSA 10 #99",
            self.by_key,
            self.prefixes,
        )
        self.assertEqual(ex, "graded_or_slab")
        self.assertEqual(mr.match_status, "excluded")
        self.assertEqual(mr.matched_card_number, "")

    def test_unknown_code(self):
        mr = match_listing_to_checklist(
            "2025 Bowman HS-999 Aaron Judge",
            self.by_key,
            self.prefixes,
        )
        self.assertEqual(mr.match_status, "unmatched_code_not_on_checklist")
        self.assertEqual(mr.extracted_codes, "HS-999")

    def test_write_split_by_match_status(self):
        with tempfile.TemporaryDirectory() as td:
            merged = Path(td) / "listings_steps12.csv"
            merged.write_text(
                "item_id,title,match_status,matched_card_number,matched_checklist_player,"
                "matched_card_type,extracted_codes\n"
                "1,T1,matched,HS-1,P1,CT1,HS-1\n"
                "2,T2,matched,HS-2,P2,CT2,HS-2\n"
                "3,T3,unmatched_no_code,,,,,\n",
                encoding="utf-8",
            )
            out_dir = Path(td) / "split"
            counts = write_listings_steps12_split_by_match_status(merged, out_dir=out_dir)
            self.assertEqual(counts, {"matched": 2, "unmatched_no_code": 1})
            p_m = out_dir / "listings_step2_matched.csv"
            self.assertTrue(p_m.is_file())
            with p_m.open(newline="", encoding="utf-8") as f:
                r = csv.DictReader(f)
                self.assertEqual(r.fieldnames, ["card_number", "player_name", "card_type", "listing"])
                rows = list(r)
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                rows[0],
                {
                    "card_number": "HS-1",
                    "player_name": "P1",
                    "card_type": "CT1",
                    "listing": "T1",
                },
            )
            self.assertTrue((out_dir / "step2_split_summary.txt").is_file())


if __name__ == "__main__":
    unittest.main()
