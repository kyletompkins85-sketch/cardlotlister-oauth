from __future__ import annotations

import unittest
from pathlib import Path

from cardmatch.pipeline import _price_round_dollar, _review_slice_compact_row
from cardmatch.player_index import default_checklist_path
from cardmatch.player_index import load_bdc_player_rank
from cardmatch.review_slice import row_matches_classification_focus
from cardmatch.taxonomy import bdc_serial_denominator_color_map, build_composite_card_type
from cardmatch.card_type import row_primary_card_type


class TestBdcPlayerRank(unittest.TestCase):
    def test_load_bdc_player_rank_maps_bdc_1_to_200(self) -> None:
        checklist = default_checklist_path(Path(__file__).resolve().parents[2])
        m = load_bdc_player_rank(checklist, 200)
        self.assertEqual(m.get("Eli Willits"), 1)
        self.assertEqual(m.get("Xavier Neyens"), 2)
        self.assertEqual(m.get("Kade Anderson"), 3)


class TestReviewSliceRow(unittest.TestCase):
    def test_price_round_dollar(self) -> None:
        self.assertEqual(_price_round_dollar("0.99"), "1")
        self.assertEqual(_price_round_dollar("2.49"), "2")
        self.assertEqual(_price_round_dollar("2.5"), "2")
        self.assertEqual(_price_round_dollar(""), "")
        self.assertEqual(_price_round_dollar(None), "")

    def test_card_type_column(self) -> None:
        r = _review_slice_compact_row(
            {
                "pilot_player_guess": "Test Player",
                "pilot_is_likely_base": "1",
                "pilot_is_snack_pack": "0",
                "pilot_is_axis": "0",
                "pilot_is_orange_border": "0",
                "pilot_is_likely_chrome_base": "0",
                "pilot_reason_codes": "[]",
                "price": "10.2",
                "title": "2025 Bowman Draft Test",
            }
        )
        self.assertEqual(r["card_type"], "Base-Paper")
        self.assertEqual(r["price"], "10")

        r2 = _review_slice_compact_row(
            {
                "pilot_player_guess": "X",
                "pilot_is_likely_base": "0",
                "pilot_reason_codes": "[]",
                "price": "5",
                "title": "t",
            }
        )
        self.assertEqual(r2["card_type"], "Base-Paper")

        r3 = _review_slice_compact_row(
            {
                "pilot_player_guess": "Braden Montgomery",
                "pilot_is_likely_base": "0",
                "pilot_is_orange_border": "1",
                "pilot_is_snack_pack": "0",
                "pilot_is_axis": "0",
                "pilot_is_likely_chrome_base": "0",
                "pilot_reason_codes": "[]",
                "price": "40",
                "title": "#BD-18 Orange Border",
            }
        )
        self.assertEqual(r3["card_type"], "Chrome · Orange /25")

        r4 = _review_slice_compact_row(
            {
                "pilot_player_guess": "Eli Willits",
                "pilot_is_likely_base": "0",
                "pilot_is_likely_chrome_base": "1",
                "pilot_is_snack_pack": "0",
                "pilot_is_axis": "0",
                "pilot_is_orange_border": "0",
                "pilot_reason_codes": "[]",
                "price": "10",
                "title": "2025 Bowman Draft #BDC-1 Eli Willits Chrome",
            }
        )
        self.assertEqual(r4["card_type"], "Chrome · Base")

        r5 = _review_slice_compact_row(
            {
                "pilot_player_guess": "Sean Youngerman",
                "pilot_is_likely_base": "0",
                "pilot_is_likely_chrome_base": "0",
                "pilot_is_snack_pack": "1",
                "pilot_is_axis": "0",
                "pilot_is_orange_border": "0",
                "pilot_reason_codes": "[]",
                "price": "150",
                "title": "Snack Pack Peanuts",
            }
        )
        self.assertEqual(r5["card_type"], "Snack-Pack")

        r_axis = _review_slice_compact_row(
            {
                "pilot_player_guess": "Eli Willits",
                "pilot_is_axis": "1",
                "pilot_is_snack_pack": "0",
                "pilot_is_orange_border": "0",
                "pilot_is_likely_chrome_base": "0",
                "pilot_is_likely_base": "0",
                "pilot_reason_codes": "[]",
                "price": "25",
                "title": "2025 Bowman Axis #A-1 Eli Willits Nationals",
            }
        )
        self.assertEqual(r_axis["card_type"], "Bowman Axis · Base")

    def test_classification_focus_base(self) -> None:
        self.assertTrue(
            row_matches_classification_focus(
                {"pilot_is_likely_base": "0", "pilot_is_likely_chrome_base": "1"},
                "base",
            )
        )
        self.assertFalse(
            row_matches_classification_focus({"pilot_is_likely_base": "1"}, "base")
        )
        self.assertFalse(
            row_matches_classification_focus(
                {"pilot_is_likely_base": "0", "pilot_is_likely_chrome_base": "0"},
                "base",
            )
        )

    def test_classification_focus_paper_base(self) -> None:
        self.assertTrue(
            row_matches_classification_focus({"pilot_is_likely_base": "1"}, "paper_base")
        )
        self.assertFalse(
            row_matches_classification_focus(
                {"pilot_is_likely_base": "0", "pilot_is_likely_chrome_base": "1"},
                "paper_base",
            )
        )

    def test_classification_focus_axis(self) -> None:
        self.assertTrue(
            row_matches_classification_focus({"pilot_is_axis": "1"}, "axis"),
        )
        self.assertFalse(
            row_matches_classification_focus({"pilot_is_axis": "0"}, "axis"),
        )

    def test_classification_focus_refractor(self) -> None:
        r_bdc_ref = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "2025 Bowman Draft #BDC-1 Refractor",
        }
        self.assertTrue(row_matches_classification_focus(r_bdc_ref, "refractor"))

    def test_classification_focus_refractor_includes_image_variation(self) -> None:
        r_iv = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "JoJo Parker Refractor Image Variation #BDC-8 Blue Jays",
        }
        self.assertTrue(row_matches_classification_focus(r_iv, "refractor"))

    def test_classification_focus_refractor_and_chrome_plain(self) -> None:
        r_plain = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "2025 Bowman Draft #BDC-1 Eli Willits Chrome Refractor",
        }
        self.assertTrue(
            row_matches_classification_focus(r_plain, "refractor_and_chrome_plain"),
        )
        r_gen = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "Some listing without BDC chrome ladder",
        }
        self.assertTrue(
            row_matches_classification_focus(r_gen, "refractor_and_chrome_plain"),
        )
        r_green = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "2025 Bowman Draft #BDC-1 Green Refractor Eli Willits",
        }
        self.assertFalse(
            row_matches_classification_focus(r_green, "refractor_and_chrome_plain"),
        )
        r_num = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_numbered_serial"]',
            "title": "2025 Bowman Draft Player Sky Blue /499 #BD-1",
        }
        self.assertEqual(row_primary_card_type(r_num), "Chrome · Sky Blue /499")
        self.assertFalse(
            row_matches_classification_focus(r_num, "refractor_and_chrome_plain"),
        )
        r_nb_serial_stays_parallel = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_numbered_serial"]',
            "title": "listing with no serial denominator",
        }
        self.assertTrue(
            row_matches_classification_focus(r_nb_serial_stays_parallel, "refractor_and_chrome_plain"),
        )
        r_cpa = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Chrome Prospect Autographs Eli Willits #CPA-EW Refractor",
        }
        self.assertTrue(
            row_matches_classification_focus(r_cpa, "refractor_and_chrome_plain"),
        )
        r_college = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Kade Anderson LSU College Variation SP Card #BDC-3",
        }
        self.assertTrue(
            row_matches_classification_focus(r_college, "refractor_and_chrome_plain"),
        )

    def test_classification_focus_chrome_refractor_plain(self) -> None:
        r_plain = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "2025 Bowman Draft #BDC-1 Eli Willits Chrome Refractor",
        }
        self.assertTrue(row_matches_classification_focus(r_plain, "chrome_refractor_plain"))
        r_ref_auto = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor", "nb_auto"]',
            "title": "2025 Bowman Draft #BDC-1 Eli Willits Chrome Refractor Auto",
        }
        self.assertEqual(row_primary_card_type(r_ref_auto), "Chrome · Auto · Refractor")
        self.assertFalse(row_matches_classification_focus(r_ref_auto, "chrome_refractor_plain"))
        r_spot = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Eli Willits Spotlight SSP Refractor",
        }
        self.assertFalse(row_matches_classification_focus(r_spot, "chrome_refractor_plain"))
        r_axis_ref = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Eli Willits Axis Refractor #A-1",
        }
        self.assertTrue(row_matches_classification_focus(r_axis_ref, "refractor"))
        r_axis_plain = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "2025 Bowman Draft Axis #A-1 Eli Willits Nationals",
        }
        self.assertFalse(row_matches_classification_focus(r_axis_plain, "refractor"))

    def test_classification_focus_bdc_chrome_prospect_auto(self) -> None:
        r_cpa_auto = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Chrome Prospect Autographs Eli Willits #CPA-EW Refractor",
        }
        self.assertTrue(
            row_matches_classification_focus(r_cpa_auto, "bdc_chrome_prospect_auto"),
        )
        r_bdc_ref = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "2025 Bowman Draft #BDC-1 Refractor",
        }
        self.assertFalse(
            row_matches_classification_focus(r_bdc_ref, "bdc_chrome_prospect_auto"),
        )
        r_parallel_auto = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "Eli Willits Achromatic Auto /250 #BDC-1",
        }
        self.assertFalse(
            row_matches_classification_focus(r_parallel_auto, "bdc_chrome_prospect_auto"),
        )

    def test_classification_focus_bdc_chrome_prospect_bare_line(self) -> None:
        r_plain = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc"]',
            "title": "2025 Bowman Draft #BDC-1 Eli Willits Chrome",
        }
        # Bare **Chrome** is coerced to **· Base** or **Base-Paper**; never matches `bdc_chrome_prospect`.
        self.assertEqual(row_primary_card_type(r_plain), "Chrome · Base")
        self.assertFalse(row_matches_classification_focus(r_plain, "bdc_chrome_prospect"))
        r_ref = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "2025 Bowman Draft #BDC-1 Refractor",
        }
        self.assertFalse(row_matches_classification_focus(r_ref, "bdc_chrome_prospect"))

    def test_classification_focus_other_legacy_default(self) -> None:
        r_no_chrome = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "mystery listing",
        }
        self.assertTrue(row_matches_classification_focus(r_no_chrome, "other"))
        r_chrome = {
            **r_no_chrome,
            "title": "Bowman Chrome something",
        }
        self.assertTrue(row_matches_classification_focus(r_chrome, "other"))
        r_bdc_base = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "1",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "2025 Bowman Draft #BDC-1",
        }
        self.assertFalse(row_matches_classification_focus(r_bdc_base, "other"))

    def test_classification_focus_bdc_chrome_prospect_parallel(self) -> None:
        r_parallel = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["nb_numbered_serial"]',
            "title": "junk listing no chrome",
        }
        self.assertTrue(row_matches_classification_focus(r_parallel, "bdc_chrome_prospect_parallel"))
        r_ref = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "2025 Bowman Draft #BDC-1 Refractor",
        }
        self.assertFalse(row_matches_classification_focus(r_ref, "bdc_chrome_prospect_parallel"))

    def test_nb_numbered_serial_legacy_resolves_serial_to_colored_parallel(self) -> None:
        """When composite does not apply, `nb_numbered_serial` still maps denominator → hobby ladder."""
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["nb_numbered_serial"]',
            "title": "Some Player RC 15/250",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Purple /250")
        self.assertFalse(row_matches_classification_focus(r, "bdc_chrome_prospect_parallel"))

    def test_classification_focus_unknown_player(self) -> None:
        self.assertTrue(
            row_matches_classification_focus(
                {"pilot_player_status": "unknown", "pilot_player_guess": ""},
                "unknown_player",
            )
        )
        self.assertTrue(
            row_matches_classification_focus(
                {"pilot_player_status": "matched", "pilot_player_guess": "(unknown player)"},
                "unknown_player",
            )
        )
        self.assertFalse(
            row_matches_classification_focus(
                {"pilot_player_status": "matched", "pilot_player_guess": "Eli Willits"},
                "unknown_player",
            )
        )

    def test_classification_focus_primary_exact(self) -> None:
        rc = {"primary_card_type_exact": "Chrome · Orange /25"}
        r_match = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_orange_border", "nb_numbered_serial"]',
            "title": "2025 Bowman Draft #BDC-1 Orange Border /25",
        }
        self.assertTrue(
            row_matches_classification_focus(r_match, "primary_exact", review_config=rc),
        )
        self.assertFalse(
            row_matches_classification_focus(r_match, "primary_exact", review_config={}),
        )


class TestBdcSerialLadder(unittest.TestCase):
    def test_bdc_serial_denominator_color_map(self) -> None:
        m = bdc_serial_denominator_color_map()
        self.assertEqual(m.get(5), "Red")
        self.assertEqual(m.get(99), "Green")
        self.assertEqual(m.get(100), "Steel Metal")
        self.assertEqual(m.get(199), "Fuchsia Reptilian")
        self.assertEqual(m.get(35), "Logo Refractor")

    def test_serial_only_infer_red_and_steel(self) -> None:
        self.assertEqual(
            build_composite_card_type(
                {"title": "2025 Bowman Draft #BDC-1 Eli Willits 1/5"},
            ),
            "Chrome · Red",
        )
        self.assertEqual(
            build_composite_card_type(
                {"title": "2025 Bowman #BDC-50 Player 12/100"},
            ),
            "Chrome · Steel Metal /100",
        )

    def test_product_group_appends_serial_from_flags(self) -> None:
        """Insert-line composite includes classifier print run when serial_out_of is set."""
        self.assertEqual(
            build_composite_card_type(
                {
                    "title": "2025 Bowman Draft Kade Anderson Draft Night 25 RC BDN-3 Mariners /99 Green",
                },
            ),
            "Bowman Draft Night · Green /99",
        )

    def test_product_group_finalize_attaches_serial_to_color_not_mini_diamond(self) -> None:
        """BDC-style ladder: /50 maps to Gold segment before Mini Diamond (not Mini Diamond /50)."""
        self.assertEqual(
            build_composite_card_type(
                {
                    "title": "2025 Bowman Draft Night Gold Mini Diamond /50 BDN-1 Player",
                },
            ),
            "Bowman Draft Night · Gold /50 · Mini Diamond",
        )

    def test_product_group_green_lava_collapses_like_bdc(self) -> None:
        """Green + Lava collapses to Green /99 before generic suffix."""
        self.assertEqual(
            build_composite_card_type(
                {
                    "title": "2025 Bowman Draft Night Green Lava /99 BDN-2 Player",
                },
            ),
            "Bowman Draft Night · Green /99",
        )

    def test_pick_row_not_bare_bdc(self) -> None:
        r = {
            "title": "2025 Bowman Draft Pick Your Player #BDC-1",
            "pilot_is_likely_base": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_reason_codes": "[]",
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
        }
        self.assertEqual(row_primary_card_type(r), "Pick / set builder")


if __name__ == "__main__":
    unittest.main()
