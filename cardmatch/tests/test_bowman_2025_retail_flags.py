from __future__ import annotations

import unittest

from cardmatch.bowman_2025_retail_flags import (
    GROUP_FLAG_KEYS,
    WF_FLAG_KEYS,
    group_flags_for_word_flags,
    word_and_group_flags_for_title,
    word_flags_for_title,
    wf_grp_as_flat_str_dict,
)


class TestBowman2025RetailFlags(unittest.TestCase):
    def test_wf_count_slim_not_draft_dump(self):
        self.assertLessEqual(len(WF_FLAG_KEYS), 50)
        self.assertGreaterEqual(len(WF_FLAG_KEYS), 25)
        self.assertEqual(len(GROUP_FLAG_KEYS), 20)

    def test_all_grp_reserved_false_for_now(self):
        wf = word_flags_for_title("2025 Bowman Chrome Refractor Auto CPA-JW /99 LOT")
        grp = group_flags_for_word_flags(wf)
        self.assertTrue(all(not v for v in grp.values()))

    def test_selling_flags_kansas_city_royals_no_roy_insert(self):
        wf = word_flags_for_title("Kansas City Royals 2025 Bowman Chrome")
        self.assertFalse(wf["WF_insert_roy_favorites"])
        self.assertFalse(wf["WF_rookie_of_the_year"])

    def test_wf_rookie_of_the_year_phrase_and_roy_code(self):
        self.assertTrue(word_flags_for_title("2025 Bowman Rookie of the Year insert")["WF_rookie_of_the_year"])
        self.assertTrue(word_flags_for_title("2025 Bowman #ROY-5 SP")["WF_rookie_of_the_year"])
        self.assertTrue(word_flags_for_title("Bowman ROY-12 refractor")["WF_rookie_of_the_year"])

    def test_wf_auto_and_signed(self):
        self.assertTrue(word_flags_for_title("2025 Bowman BPA-1 auto /99")["WF_auto"])
        self.assertTrue(word_flags_for_title("2025 Bowman signed on card")["WF_auto"])
        self.assertTrue(word_flags_for_title("CPA-JW autograph")["WF_auto"])

    def test_wf_lot(self):
        self.assertTrue(word_flags_for_title("2025 Bowman 3 card lot")["WF_lot"])

    def test_doc_paper_chrome_clues(self):
        wf = word_flags_for_title("true blue paper 2025 Bowman")
        self.assertTrue(wf["WF_true_blue"])
        self.assertTrue(wf["WF_paper"])
        wf2 = word_flags_for_title("2025 Bowman Chrome Refractor")
        self.assertTrue(wf2["WF_chrome"])
        self.assertTrue(wf2["WF_refractor"])

    def test_wf_chrome_from_checklist_codes_without_word_chrome(self):
        self.assertTrue(word_flags_for_title("2025 Bowman BCP-22 JJ Wetherholt")["WF_chrome"])
        self.assertTrue(word_flags_for_title("Bowman CPA-JW auto")["WF_chrome"])
        self.assertTrue(word_flags_for_title("CRA-CM Coby Mayo")["WF_chrome"])
        self.assertFalse(word_flags_for_title("Kansas City Royals 2025 Bowman")["WF_chrome"])

    def test_wf_paper_from_checklist_codes_without_word_paper(self):
        self.assertTrue(word_flags_for_title("2025 Bowman BP-22 Walker Jenkins")["WF_paper"])
        self.assertTrue(word_flags_for_title("BPA-CC Charlie Condon")["WF_paper"])
        self.assertTrue(word_flags_for_title("PRV-CM Coby Mayo")["WF_paper"])

    def test_bowmans_best(self):
        self.assertTrue(
            word_flags_for_title("2025 Bowman's Best Aaron Judge Refractor")["WF_bowmans_best"]
        )
        self.assertTrue(word_flags_for_title("2025 Bowmans Best Chrome")["WF_bowmans_best"])

    def test_bowman_draft(self):
        self.assertTrue(word_flags_for_title("2025 Bowman Draft Chrome BDC-1")["WF_bowman_draft"])
        self.assertFalse(word_flags_for_title("2025 Bowman Chrome Draft pick")["WF_bowman_draft"])

    def test_wf_insert_top_100_and_rockstart_typo(self):
        self.assertTrue(word_flags_for_title("2025 Bowman Top 100 Roman Anthony")["WF_insert_top_100"])
        self.assertTrue(
            word_flags_for_title("2025 Bowman Chrome Rockstart Rookies auto")["WF_insert_rockstar_rookies"]
        )

    def test_serial_fraction_wf(self):
        wf = word_flags_for_title("Aaron Judge Neon Green 116/199 2025 Bowman")
        self.assertTrue(wf["WF_serial_fraction"])

    def test_wf_non_bowman_retail_insert_flags(self):
        t = (
            ("2025 Bowman Melt Mashers SP", "WF_insert_melt_mashers"),
            ("Bowman Chrome Ascensions auto", "WF_insert_ascensions"),
            ("2025 GPK insert", "WF_insert_gpk"),
            ("It Came to the League refractor", "WF_insert_it_came_to_the_league"),
            ("Meteoric Rise gold /50", "WF_insert_meteoric_rise"),
            ("Max Volume parallel", "WF_insert_max_volume"),
            ("Adios green shimmer", "WF_insert_adios"),
        )
        for title, key in t:
            with self.subTest(title=title):
                self.assertTrue(word_flags_for_title(title)[key], msg=key)

    def test_wf_grp_flat_dict_order(self):
        wf, grp = word_and_group_flags_for_title("2025 Bowman #99")
        flat = wf_grp_as_flat_str_dict(wf, grp)
        keys = list(flat.keys())
        self.assertEqual(keys[0], "WF_complete_set")
        self.assertTrue(keys.index("grp_reserved_01") > keys.index("WF_line_chrome_prospects"))


if __name__ == "__main__":
    unittest.main()
