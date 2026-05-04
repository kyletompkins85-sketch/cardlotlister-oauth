from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from cardmatch.bowman_2025_listing_display import listing_display_from_title
from cardmatch.bowman_2025_retail_flags import word_flags_for_title
from cardmatch.bowman_2025_retail_steps import (
    MATCHED_STEP3_INSERT_STATUS,
    STEP3_MATCHED_REVIEW_COLUMNS,
    btp_checklist_rows,
    checklist_code_prefixes,
    exclusion_reason,
    extract_checklist_codes,
    infer_roy_card_number_from_title,
    infer_step3_insert_by_name,
    load_card_lookup,
    match_listing_to_checklist,
    match_status_after_step3,
    player_name_for_review_csv,
    process_title,
    roy_checklist_subsets,
    rr_checklist_subsets,
    step23_pass,
    write_listings_step23_split_by_match_status,
    write_listings_step3_matched_with_serial,
    write_listings_steps12_split_by_match_status,
)


class TestBowman2025RetailSteps(unittest.TestCase):
    def test_player_name_for_review_csv(self):
        self.assertEqual(player_name_for_review_csv("Jackson Humphries"), "Ja Humphries")
        self.assertEqual(player_name_for_review_csv("Mike Trout"), "Mi Trout")
        self.assertEqual(player_name_for_review_csv("JJ"), "JJ")
        self.assertEqual(player_name_for_review_csv(""), "")

    def test_load_lookup_has_card_type_display_for_bcp(self):
        row = self.by_key.get("BCP-1")
        self.assertIsNotNone(row)
        self.assertEqual(row.card_type, "Bowman Chrome Prospects")
        self.assertEqual(row.card_type_display, "BCP")

    @classmethod
    def setUpClass(cls):
        by_key, names = load_card_lookup()
        cls.by_key = by_key
        cls.prefixes = checklist_code_prefixes(by_key)
        cls.names = names
        cls.roy_numeric, cls.roy_auto = roy_checklist_subsets(by_key)
        cls.rr_numeric, cls.rr_auto = rr_checklist_subsets(by_key)
        cls.btp_rows = btp_checklist_rows(by_key)

    def test_exclusion_lot(self):
        self.assertEqual(exclusion_reason("2025 Bowman Aaron Judge 3 Card lot"), "lot")

    def test_exclusion_non_bowman_retail_inserts(self):
        self.assertEqual(
            exclusion_reason("2025 Bowman Chrome Melt Mashers Wander Franco"),
            "non_bowman_retail_insert_melt_mashers",
        )
        self.assertEqual(
            exclusion_reason("Bowman Ascensions auto /99"),
            "non_bowman_retail_insert_ascensions",
        )
        self.assertEqual(exclusion_reason("2025 Topps GPK x Bowman"), "non_bowman_retail_insert_gpk")

    def test_exclusion_bowmans_best_and_bowman_draft(self):
        self.assertEqual(
            exclusion_reason("2025 Bowman's Best Aaron Judge Refractor"),
            "non_bowman_retail_bowmans_best",
        )
        self.assertEqual(
            exclusion_reason("2025 Bowman Draft Chrome BDC-1 Paul Skenes"),
            "non_bowman_retail_bowman_draft",
        )

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

    def test_extract_chrome_title_omits_paper_base_hash_slots(self):
        p = self.prefixes
        self.assertNotIn(
            "7",
            extract_checklist_codes("2025 Bowman Chrome - Bobby Witt Jr Mojo #7", p),
        )

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

    def test_rejected_player_mismatch_wrong_name(self):
        mr = match_listing_to_checklist(
            "2025 Bowman #HS-11 Mickey Mouse Refractor",
            self.by_key,
            self.prefixes,
        )
        self.assertEqual(mr.match_status, "rejected_player_mismatch")
        self.assertEqual(mr.matched_card_number, "")
        self.assertEqual(mr.matched_player, "")
        self.assertEqual(mr.extracted_codes, "HS-11")

    def test_infer_roy_numeric_no_auto(self):
        title = "2025 Bowman Rookie of the Year Favorites Dylan Crews"
        wf = word_flags_for_title(title)
        self.assertTrue(wf["WF_rookie_of_the_year"])
        self.assertFalse(wf["WF_auto"])
        cn, kind, sc = infer_roy_card_number_from_title(
            title, wf, "", self.roy_numeric, self.roy_auto
        )
        self.assertEqual(cn, "ROY-1")
        self.assertEqual(kind, "roy_numeric_name")
        self.assertGreaterEqual(sc, 80.0)

    def test_infer_roy_auto_initials(self):
        title = "2025 Bowman Rookie of the Year Favorites Autographs Signed Dylan Crews"
        wf = word_flags_for_title(title)
        self.assertTrue(wf["WF_rookie_of_the_year"])
        self.assertTrue(wf["WF_auto"])
        cn, kind, sc = infer_roy_card_number_from_title(
            title, wf, "", self.roy_numeric, self.roy_auto
        )
        self.assertEqual(cn, "ROY-DC")
        self.assertEqual(kind, "roy_auto_name")
        self.assertGreaterEqual(sc, 80.0)

    def test_infer_roy_skips_when_code_extracted(self):
        title = "2025 Bowman ROY-1 Dylan Crews"
        wf = word_flags_for_title(title)
        cn, kind, _ = infer_roy_card_number_from_title(
            title, wf, "ROY-1", self.roy_numeric, self.roy_auto
        )
        self.assertEqual(cn, "")
        self.assertEqual(kind, "")

    def test_infer_roy_not_triggered_by_royals(self):
        title = "2025 Bowman Kansas City Royals Dylan Crews lot"
        wf = word_flags_for_title(title)
        self.assertFalse(wf["WF_rookie_of_the_year"])
        cn, kind, _ = infer_roy_card_number_from_title(
            title, wf, "", self.roy_numeric, self.roy_auto
        )
        self.assertEqual(cn, "")
        self.assertEqual(kind, "")

    def test_infer_step3_rr_auto_initials(self):
        title = "2025 Bowman Chrome Rockstar Rookies Signed Dylan Crews"
        wf = word_flags_for_title(title)
        self.assertTrue(wf["WF_insert_rockstar_rookies"])
        self.assertTrue(wf["WF_auto"])
        cn, kind, sc = infer_step3_insert_by_name(
            title,
            wf,
            "",
            self.roy_numeric,
            self.roy_auto,
            self.rr_numeric,
            self.rr_auto,
            self.btp_rows,
        )
        self.assertEqual(cn, "RRA-DC")
        self.assertEqual(kind, "rr_auto_name")
        self.assertGreaterEqual(sc, 80.0)

    def test_infer_step3_rr_numeric_no_auto(self):
        title = "2025 Bowman Chrome Rockstar Rookies Dylan Crews"
        wf = word_flags_for_title(title)
        self.assertTrue(wf["WF_insert_rockstar_rookies"])
        self.assertFalse(wf["WF_auto"])
        cn, kind, sc = infer_step3_insert_by_name(
            title,
            wf,
            "",
            self.roy_numeric,
            self.roy_auto,
            self.rr_numeric,
            self.rr_auto,
            self.btp_rows,
        )
        self.assertEqual(cn, "RR-15")
        self.assertEqual(kind, "rr_numeric_name")
        self.assertGreaterEqual(sc, 80.0)

    def test_infer_step3_btp_name_match(self):
        title = "2025 Bowman Chrome Scouts Top 100 Roman Anthony refractor"
        wf = word_flags_for_title(title)
        self.assertTrue(wf["WF_insert_scouts_top_100"])
        cn, kind, sc = infer_step3_insert_by_name(
            title,
            wf,
            "",
            self.roy_numeric,
            self.roy_auto,
            self.rr_numeric,
            self.rr_auto,
            self.btp_rows,
        )
        self.assertEqual(cn, "BTP-1")
        self.assertEqual(kind, "btp_name")
        self.assertGreaterEqual(sc, 80.0)

    def test_infer_step3_btp_top_100_phrase(self):
        title = "2025 Bowman Top 100 Walker Jenkins"
        wf = word_flags_for_title(title)
        self.assertTrue(wf["WF_insert_top_100"])
        cn, kind, _ = infer_step3_insert_by_name(
            title,
            wf,
            "",
            self.roy_numeric,
            self.roy_auto,
            self.rr_numeric,
            self.rr_auto,
            self.btp_rows,
        )
        self.assertEqual(cn, "BTP-2")
        self.assertEqual(kind, "btp_name")

    def test_infer_step3_rr_skips_when_code_in_title(self):
        title = "2025 Bowman RR-1 Rockstar Rookies auto"
        wf = word_flags_for_title(title)
        cn, kind, _ = infer_step3_insert_by_name(
            title,
            wf,
            "RR-1",
            self.roy_numeric,
            self.roy_auto,
            self.rr_numeric,
            self.rr_auto,
            self.btp_rows,
        )
        self.assertEqual(cn, "")
        self.assertEqual(kind, "")

    def test_match_status_after_step3_insert_resolves(self):
        self.assertEqual(
            match_status_after_step3("0", "unmatched_no_code", "ROY-AA"),
            MATCHED_STEP3_INSERT_STATUS,
        )
        self.assertTrue(step23_pass("0", "unmatched_no_code", "ROY-AA"))

    def test_match_status_after_step3_step2_wins(self):
        self.assertEqual(match_status_after_step3("0", "matched", "ROY-1"), "matched")
        self.assertTrue(step23_pass("0", "matched", ""))

    def test_write_step23_split_moves_roy_to_own_bucket(self):
        with tempfile.TemporaryDirectory() as td:
            merged = Path(td) / "listings_steps12.csv"
            merged.write_text(
                "item_id,title,excluded,match_status,matched_card_number,matched_checklist_player,"
                "matched_card_type,extracted_codes,step3_inferred_card_number,step3_matched_checklist_player,"
                "step3_matched_card_type,match_status_after_step3\n"
                "1,T1,0,unmatched_no_code,,,,,ROY-AA,Adael Amador,Rookie of the Year Favorites Autographs,matched_step3_insert\n"
                "2,T2,0,unmatched_no_code,,,,,,,,,\n",
                encoding="utf-8",
            )
            out_dir = Path(td) / "s23"
            counts = write_listings_step23_split_by_match_status(merged, out_dir=out_dir)
            self.assertEqual(
                counts,
                {MATCHED_STEP3_INSERT_STATUS: 1, "unmatched_no_code": 1},
            )
            p = out_dir / "listings_step23_unmatched_no_code.csv"
            with p.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["listing"], "T2")
            still = out_dir / "listings_step23_still_unmatched_after_both.csv"
            with still.open(newline="", encoding="utf-8") as f:
                srows = list(csv.DictReader(f))
            self.assertEqual(len(srows), 1)
            self.assertEqual(srows[0]["listing"], "T2")

    def test_write_split_by_match_status(self):
        with tempfile.TemporaryDirectory() as td:
            merged = Path(td) / "listings_steps12.csv"
            merged.write_text(
                "item_id,title,match_status,matched_card_number,matched_checklist_player,"
                "matched_card_type,extracted_codes\n"
                "1,T1,matched,HS-11,P11,CT11,HS-11\n"
                "2,T2,matched,HS-1,P1,CT1,HS-1\n"
                "3,T3,matched,HS-2,P2,CT2,HS-2\n"
                "4,T4,unmatched_no_code,,,,,\n",
                encoding="utf-8",
            )
            out_dir = Path(td) / "split"
            counts = write_listings_steps12_split_by_match_status(merged, out_dir=out_dir)
            self.assertEqual(counts, {"matched": 3, "unmatched_no_code": 1})
            p_m = out_dir / "listings_step2_matched.csv"
            self.assertTrue(p_m.is_file())
            with p_m.open(newline="", encoding="utf-8") as f:
                r = csv.DictReader(f)
                self.assertEqual(
                    r.fieldnames,
                    ["card_number", "player_name", "card_type", "listing_display", "listing"],
                )
                rows = list(r)
            self.assertEqual(len(rows), 3)
            self.assertEqual([x["card_number"] for x in rows], ["HS-1", "HS-2", "HS-11"])
            self.assertEqual(
                rows[0],
                {
                    "card_number": "HS-1",
                    "player_name": "P1",
                    "card_type": "CT1",
                    "listing_display": listing_display_from_title("T2", card_number="HS-1"),
                    "listing": "T2",
                },
            )
            self.assertTrue((out_dir / "step2_split_summary.txt").is_file())

    def test_write_step3_matched_with_serial_columns_and_sort(self):
        with tempfile.TemporaryDirectory() as td:
            merged = Path(td) / "listings_steps12.csv"
            merged.write_text(
                "item_id,title,excluded,match_status,matched_card_number,matched_checklist_player,"
                "matched_card_type,extracted_codes,serial_out_of,step3_inferred_card_number,"
                "match_status_after_step3\n"
                "1,BCP-2 /499,0,matched,BCP-2,Player Two,BCP,,499,,matched\n"
                "2,BCP-2 base,0,matched,BCP-2,Player Two,BCP,,,,matched\n"
                "3,BCP-2 Yellow /250,0,matched,BCP-2,Player Two,BCP,,,,matched\n"
                "4,BCP-10 green,0,matched,BCP-10,Player Ten,BCP,,,,matched\n"
                "5,ROY-1,0,unmatched_no_code,,,,,,ROY-1,matched_step3_insert\n",
                encoding="utf-8",
            )
            out_dir = Path(td) / "s3"
            n = write_listings_step3_matched_with_serial(merged, out_dir=out_dir)
            self.assertEqual(n, 4)
            p = out_dir / "listings_step3_matched.csv"
            with p.open(newline="", encoding="utf-8") as f:
                dr = csv.DictReader(f)
                self.assertEqual(tuple(dr.fieldnames or ()), STEP3_MATCHED_REVIEW_COLUMNS)
                rows = list(dr)
            self.assertEqual(len(rows), 4)
            self.assertEqual(
                [(x["card_number"], x["serial"]) for x in rows],
                [
                    ("BCP-2", "-1"),
                    ("BCP-2", "499"),
                    ("BCP-2", "250"),
                    ("BCP-10", "-1"),
                ],
            )
            self.assertEqual(rows[1]["player_name"], "Pl Two")
            self.assertEqual(rows[1]["card_type"], "BCP")
            self.assertTrue((out_dir / "step3_matched_summary.txt").is_file())


if __name__ == "__main__":
    unittest.main()
