from __future__ import annotations

import unittest
from pathlib import Path

from cardmatch.pilot import match_pilot
from cardmatch.player_index import default_checklist_path, load_bowman_draft_players


class TestPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        checklist = default_checklist_path(Path(__file__).resolve().parents[2])
        cls.names, cls.last_index = load_bowman_draft_players(checklist)

    def test_eli_willits_plain(self) -> None:
        r = match_pilot(
            "2025 Bowman Draft Eli Willits Washington Nationals Base",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertIn("Willits", r.player_guess)
        self.assertTrue(r.is_likely_base)

    def test_prized_not_base(self) -> None:
        r = match_pilot(
            "Eli Willits 2025 Bowman Draft Prized Prospects #PP-1",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertTrue(any("not_likely_base" in x or x.startswith("nb_") for x in r.reason_codes))

    def test_axis_not_base(self) -> None:
        r = match_pilot(
            "#A-1 Eli Willits Axis Insert Washington Nationals",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertTrue(r.is_axis)
        self.assertIn("nb_axis", r.reason_codes)

    def test_draft_night_not_base(self) -> None:
        r = match_pilot(
            "#BDN-1 Eli Willits Night Insert Nationals",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_draft_night)
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_draft_night", r.reason_codes)

    def test_bowman_draft_night_phrase_flagged(self) -> None:
        r = match_pilot(
            "2025 Bowman Draft Night #BDN-5 Eli Willits Nationals",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_draft_night)

    def test_draft_day_phrase_is_draft_night_not_base(self) -> None:
        r = match_pilot(
            "Seth Hernandez Draft Day",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_draft_night)
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_draft_night", r.reason_codes)

    def test_bdc_chrome_base_not_paper_base(self) -> None:
        r = match_pilot(
            "2025 Bowman Chrome Draft #BDC-1 Eli Willits Washington Nationals",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_bdc", r.reason_codes)
        self.assertTrue(r.is_chrome)
        self.assertTrue(r.is_likely_chrome_base)

    def test_snack_pack_not_chrome_base(self) -> None:
        r = match_pilot(
            "Sean Youngerman Snack Pack Peanuts SSP Phillies BDC-109",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_chrome_base)
        self.assertTrue(r.is_snack_pack)
        self.assertIn("nb_snack_pack", r.reason_codes)

    def test_popcorn_ssp_named_snack_pack_line(self) -> None:
        r = match_pilot(
            "James Tibbs III Popcorn SSP Dodgers #BD-74",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_snack_pack)
        self.assertIn("nb_snack_pack", r.reason_codes)

    def test_sunflower_seed_snack_pack_line(self) -> None:
        r = match_pilot(
            "Antonio Jimenez Sunflower Seed SSP Mets 1st Bowman #BD-56",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_snack_pack)

    def test_bubble_gum_snack_pack_line(self) -> None:
        r = match_pilot(
            "Matthew Fisher Bubblegum SSP 1st Bowman Phillies BDC-106",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_snack_pack)

    def test_gum_ball_snack_pack_line(self) -> None:
        r = match_pilot(
            "Mason Peters Gum Ball Refractor SSP BDC-27",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_snack_pack)
        self.assertIn("nb_snack_pack", r.reason_codes)

    def test_peanuts_snack_pack_line(self) -> None:
        r = match_pilot(
            "Eduardo Tait peanuts refractor SSP",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_snack_pack)
        self.assertIn("nb_snack_pack", r.reason_codes)

    def test_blue_geometric_not_chrome_base(self) -> None:
        r = match_pilot(
            "Chrome Blue Geometric #BDC-163 Jonny Farmelo",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_chrome_base)
        self.assertIn("nb_blue_geometric", r.reason_codes)

    def test_sparkle_parallel_not_chrome_base(self) -> None:
        r = match_pilot(
            "BDC-148 Ethan Hedges VERY RARE Sparkle",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_chrome_base)
        self.assertIn("nb_sparkle", r.reason_codes)

    def test_aqua_geometric_not_chrome_base(self) -> None:
        r = match_pilot(
            "#BDC-74 James Tibbs III Chrome Aqua Geometric",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_chrome_base)
        self.assertIn("nb_aqua", r.reason_codes)

    def test_mini_diamond_not_chrome_base(self) -> None:
        r = match_pilot(
            "#BDC-54 Marcus Phillips 1st Mini Diamonds",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_chrome_base)
        self.assertIn("nb_mini_diamond", r.reason_codes)

    def test_sky_blue_parallel_not_chrome_base(self) -> None:
        r = match_pilot(
            "JoJo Parker Sky Blue Chrome Parallel BDC-8",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_chrome_base)
        self.assertIn("nb_sky_blue", r.reason_codes)

    def test_blue_sky_word_order_not_chrome_base(self) -> None:
        r = match_pilot(
            "#BDC98 Aroon Escobar BLUE SKY - SP",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_chrome_base)
        self.assertIn("nb_sky_blue", r.reason_codes)

    def test_college_variation_sp_not_chrome_base(self) -> None:
        r = match_pilot(
            "Kade Anderson LSU College Variation SP Card #BDC-3",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_chrome_base)
        self.assertIn("nb_college_variation", r.reason_codes)

    def test_complete_chrome_set_not_chrome_base(self) -> None:
        r = match_pilot(
            "Complete 200 Card Base Chrome Set BDC1-200 Willits Hernandez",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_chrome_base)
        self.assertIn("nb_complete_set", r.reason_codes)

    def test_bowman_chrome_without_bdc_not_paper_base(self) -> None:
        r = match_pilot(
            "Ethan Conrad 1st Bowman Chrome QTY AVAIL CUBS",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_chrome)
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_chrome", r.reason_codes)
        self.assertFalse(r.is_likely_chrome_base)

    def test_orange_border_not_plain_base(self) -> None:
        r = match_pilot(
            "#BD-18 Braden Montgomery Orange Border",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_orange_border)
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_orange_border", r.reason_codes)

    def test_bowman_in_action_not_base(self) -> None:
        r = match_pilot(
            "Bowman in Action Eli Willits #BIA-1 Washington Nationals",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_bowman_in_action", r.reason_codes)

    def test_x_fractor_not_base(self) -> None:
        r = match_pilot(
            "2025 Bowman Chrome Draft Eli Willits X-Fractor #BD-1 Nationals",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_x_fractor", r.reason_codes)

    def test_image_variation_not_base(self) -> None:
        r = match_pilot(
            "Eli Willits Chrome Image Variation SP SSP Prospect Nationals",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_image_variation", r.reason_codes)

    def test_bowman_spotlight_not_base(self) -> None:
        r = match_pilot(
            "2025 Bowman Draft Eli Willits Bowman Spotlights SSP CASE HIT #BS-1 Nationals",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_bowman_spotlight", r.reason_codes)

    def test_chrome_prospect_autographs_not_base(self) -> None:
        r = match_pilot(
            'Chrome Prospect Autographs Eli Willits #CPA-EW (AU, RC)',
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_chrome_prospect_autographs", r.reason_codes)

    def test_cpa_sticker_not_base(self) -> None:
        r = match_pilot(
            "#CPA-EW Eli Willits Chrome Auto Nationals",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_chrome_prospect_autographs", r.reason_codes)

    def test_etched_in_glass_not_base(self) -> None:
        r = match_pilot(
            "Kade Anderson Chrome Etched In Glass Variation SSP Mariners",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_etched_in_glass", r.reason_codes)

    def test_etched_in_class_typo_not_base(self) -> None:
        r = match_pilot(
            "Xavier Neyens Etched In Class SSP Astros 1ST PROSPECT",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_etched_in_glass", r.reason_codes)

    def test_ethced_in_glass_typo_not_chrome_base(self) -> None:
        r = match_pilot(
            "2025 Gavin Fien Chrome Ethced In Glass Variations #BDC-15",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_chrome_base)
        self.assertIn("nb_etched_in_glass", r.reason_codes)

    def test_sapphire_not_base(self) -> None:
        r = match_pilot(
            "Sapphire Edition - Xavier Neyens #BDC-2 (RC)",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_sapphire", r.reason_codes)

    def test_crystallized_not_base(self) -> None:
        r = match_pilot(
            "Jojo Parker Crystallized 1st SSP",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_crystallized", r.reason_codes)

    def test_final_draft_not_base(self) -> None:
        r = match_pilot(
            "Eli Willits Final Draft Case Hit SSP Nationals #FD-11",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_final_draft", r.reason_codes)

    def test_unknown_player(self) -> None:
        r = match_pilot(
            "2025 Bowman Draft Complete Set 1-200",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "unknown")

    def test_chrome_paper_lot_out_of_scope(self) -> None:
        r = match_pilot(
            "2025 Bowman Draft Chrome Paper Lot Of 15 Boston Red Sox Franklin Arias",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_lot)
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_lot", r.reason_codes)

    def test_paper_card_lot_out_of_scope(self) -> None:
        r = match_pilot(
            "Roc Riggio 2025 Bowman Draft Prospects Paper 5 Card Lot Colorado Rockies",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_lot)
        self.assertFalse(r.is_likely_base)

    def test_chrome_paper_lot_sirota_out_of_scope(self) -> None:
        r = match_pilot(
            "2025 1st Chrome Paper Lot 5 Los Angeles Dodgers Mike Sirota",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_lot)
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_lot", r.reason_codes)

    def test_chrome_and_base_mixed_lot_not_base(self) -> None:
        r = match_pilot(
            "Liam Doyle 1st Bowman Lot- Chrome and Base Cardinals",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_likely_base)

    def test_bd_number_bulk_lot_out_of_scope(self) -> None:
        r = match_pilot(
            "(10) 2025 Bowman Draft Steele Hall 1st Rookie Card Lot #BD-20 Cincinnati Reds RC",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_lot)
        self.assertFalse(r.is_likely_base)

    def test_graded_psa_not_likely_base(self) -> None:
        r = match_pilot(
            "2025 Bowman Draft Eli Willits Washington Nationals PSA 10 BD-1",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertTrue(r.is_graded)
        self.assertFalse(r.is_likely_base)
        self.assertIn("nb_graded", r.reason_codes)

    def test_ungraded_not_flagged_graded(self) -> None:
        r = match_pilot(
            "2025 Bowman Draft Eli Willits Washington Nationals Ungraded BD-1",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "matched")
        self.assertFalse(r.is_graded)


if __name__ == "__main__":
    unittest.main()
