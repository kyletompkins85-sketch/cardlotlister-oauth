from __future__ import annotations

import unittest
from unittest.mock import patch

import tempfile
from pathlib import Path

from cardmatch.card_type import (
    _listing_counts_by_card_type_sort_key,
    legacy_primary_card_type,
    parse_axis_insert_number,
    row_is_graded_listing,
    row_primary_card_type,
    write_listing_count_reports,
)
from cardmatch.taxonomy import finalize_bdc_composite_string


class TestCardType(unittest.TestCase):
    def test_paper_base(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "1",
            "pilot_reason_codes": "[]",
        }
        self.assertEqual(row_primary_card_type(r), "Base-Paper")

    def test_nb_auto_without_chrome_in_title_is_cpa_auto_not_base_paper(self) -> None:
        """Legacy path used to fall through to **Base-Paper** when title had no *chrome* but ``nb_auto`` fired."""
        r = {
            "title": "2025 Bowman Draft Joe Player 1st Auto - Tigers Prospect",
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_auto"]',
        }
        self.assertEqual(
            row_primary_card_type(r),
            finalize_bdc_composite_string("Chrome · Auto"),
        )

    def test_chrome_base(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "1",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Base")

    def test_bare_bdc_nb_coerces_to_base_or_paper(self) -> None:
        r_chrome_word = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc"]',
            "title": "2025 Bowman Draft #BDC-1 Eli Willits Chrome",
        }
        self.assertEqual(row_primary_card_type(r_chrome_word), "Chrome · Base")
        r_no_chrome_word = {
            **r_chrome_word,
            "title": "2025 Bowman Draft #BDC-1 Eli Willits",
        }
        self.assertEqual(row_primary_card_type(r_no_chrome_word), "Base-Paper")

    def test_refractor_uses_last_nb(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Refractor")

    def test_chrome_bdc_refractor_plain(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "2025 Bowman Draft #BDC-1 Eli Willits Chrome Refractor",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Refractor")

    def test_chrome_bdc_refractor_sky_blue(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_sky_blue", "nb_refractor"]',
            "title": "2025 Bowman Draft #BDC-1 Eli Willits Chrome Sky Blue Refractor",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Sky Blue /499")

    def test_chrome_bdc_x_fractor(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_x_fractor"]',
            "title": "2025 Bowman Draft #BDC-1 X-Fractor Eli Willits",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · X-Fractor")

    def test_chrome_prospect_autographs_over_refractor(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Chrome Prospect Autographs Eli Willits #CPA-EW Refractor",
        }
        self.assertEqual(
            row_primary_card_type(r),
            "Chrome · Auto",
        )

    def test_cpa_auto_blue_slash_150_without_mojo_word(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Kade Anderson 1st Auto Blue /150 Mariners CPA-KA",
        }
        self.assertEqual(
            row_primary_card_type(r),
            "Chrome · Auto · Blue /150",
        )

    def test_cpa_auto_serial_499_maps_sky_blue(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Eli Willits Chrome Prospect Autographs /499 #CPA-EW Auto",
        }
        self.assertEqual(
            row_primary_card_type(r),
            "Chrome · Auto · Sky Blue /499",
        )

    def test_lsu_in_title_is_college_variation_not_plain_cpa(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "KADE ANDERSON Chrome Auto Autograph Mariners 1st Bowman LSU",
        }
        self.assertEqual(
            row_primary_card_type(r),
            "Chrome Prospect College Variations · Auto",
        )

    def test_spotlight(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Eli Willits Spotlight SSP Refractor",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman Spotlight")

    def test_final_draft(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Eli Willits Final Draft FD-11 Refractor Insert Case Hit",
        }
        self.assertEqual(row_primary_card_type(r), "Final Draft")

    def test_chrome_refractor_aqua_reptilian(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Xavier Neyens Aqua Reptilian Refractor /125 Astros #BDC-2",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Aqua Reptilian")

    def test_chrome_refractor_steel_100(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Xavier Neyens #BDC-2 Chrome Steel Metal Refractor #/100",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Steel Metal /100")

    def test_etched_in_glass(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "KADE ANDERSON 1st Etched In Glass Refractor #BDC-3 SSP",
        }
        self.assertEqual(row_primary_card_type(r), "Etched in Glass")

    def test_chrome_refractor_fuschia_199(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Kade Anderson Fuchsia Reptilian Refractor /199 #BDC-3",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Fuchsia Reptilian /199")

    def test_chrome_refractor_blue_150_mojo(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Kade Anderson 1st Blue Mojo Refractor /150 BDC-3",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Blue /150")

    def test_refractor_aqua_125_wave(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Max Belyeu 1st Aqua Wave Refractor /125 #BDC-5 Rockies",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Aqua /125")

    def test_image_variation_without_bdc_in_title(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "JoJo Parker Refractor Image Variation - Blue Jays",
        }
        self.assertEqual(row_primary_card_type(r), "Image Variations")

    def test_chrome_x_fractor_without_bdc_path(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Eli Willits 1st Prospect X-Fractor Refractor Nationals",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · X-Fractor")

    def test_chrome_refractor_sparkles(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "SPENCER JONES Sparkly Refractor BDC-9 Yankees",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Sparkle")

    def test_sparkle_non_adjacent_refractor(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Steele Hall Sparkle 1st Refractor Reds",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Sparkle")

    def test_speckle_refractor_phrasing(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "ELI WILLITS - SP Chrome 1st Speckle Refractor Nationals",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Speckle Refractor")

    def test_fuchsia_reptilian_short_print_wording(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Gage Wood 1st Fuchsia Reptilian Short Print Refractor /199",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Fuchsia Reptilian /199")

    def test_pink_reptilian_maps_fuchsia_line(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Billy Carlson Pink Reptilian Refractor 34/199",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Fuchsia Reptilian /199")

    def test_refractor_slash_199_maps_fuchsia_reptilian(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "TYLER BREMNER Refractor /199 RC Angels",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Fuchsia Reptilian /199")

    def test_gum_ball_is_snack_pack_from_classifier(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Gum Ball Refractor SSP VERY RARE BDC-27 Mason Peters",
        }
        self.assertEqual(row_primary_card_type(r), "Snack-Pack")

    def test_peanuts_snack_pack_line(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Eduardo Tait peanuts refractor",
        }
        self.assertEqual(row_primary_card_type(r), "Snack-Pack")

    def test_logo_refractor_slash_35_serial(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Michael Salina True Refractor /35 #BDC-76",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Logo Refractor /35")

    def test_x_refractor_two_word_phrase(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Luke Dickerson Nationals X Refractor",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · X-Fractor")

    def test_mini_diamond_vip_refractor(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "2025 Bowman Travis Bazzana #VIP-8 Mini Diamond Refractor VIP RC Insert #1 Draft",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Mini Diamond")

    def test_refractor_aqua_word_order(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Griffin Hugus Refractor Aqua",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Aqua /125")

    def test_refractor_blue_word_order(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Felnin Celesten Refractor Blue",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Blue /150")

    def test_blue_sapphire_refractor(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Jonny Farmelo Blue Sapphire Refractor BDC-163",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Sapphire")

    def test_graded_bgs_over_parallel(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Kade Anderson 1st Purple Refractor AUTO BGS 9.5 GM Mariners",
        }
        self.assertEqual(row_primary_card_type(r), "Graded")
        self.assertTrue(row_is_graded_listing(r))

    def test_image_variation_bdc(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "JoJo Parker Refractor Image Variation #BDC-8 Blue Jays",
        }
        self.assertEqual(row_primary_card_type(r), "Image Variations")

    def test_chrome_refractor_blue(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "ELI WILLITS 1st Bowman Chrome Blue Refractor /150 - BDC-1",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Blue /150")

    def test_chrome_bdc_green_refractor(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc", "nb_refractor"]',
            "title": "2025 Bowman Draft #BDC-1 Green Refractor Eli Willits",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Green /99")

    def test_prized_prospects_slash_99_infer_green_without_color_word(self) -> None:
        """PP /99 is the green parallel; infer from serial when title omits *green* (same hobby ladder as Chrome)."""
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Prized Prospects #PP-6 Billy Carlson 7/99 RC",
        }
        self.assertEqual(row_primary_card_type(r), "Prized Prospects · Green /99")

    def test_prized_prospects_slash_99_auto_infer_green(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "2025 Bowman Draft Kade Anderson Prized Prospects Auto 12/99 Mariners",
        }
        self.assertEqual(row_primary_card_type(r), "Prized Prospects · Auto · Green /99")

    def test_prized_prospects_slash_50_infer_gold_without_color_word(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "2025 Bowman Draft Prized Prospects #PP-1 Player 12/50 RC",
        }
        self.assertEqual(row_primary_card_type(r), "Prized Prospects · Gold /50")

    def test_bowman_draft_night_slash_99_infer_green(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "2025 Bowman Draft Night BDN-3 Player 7/99 Nationals",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman Draft Night · Green /99")

    def test_bowman_in_action_slash_99_infer_green(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "2025 Bowman In Action BIA-1 Player 7/99 Nationals",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman In Action · Green /99")

    def test_bowman_in_action_slash_150_infer_mini_diamond(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Bowman In Action Mini Diamond Refractor /150 Player RC",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman In Action · Mini Diamond /150")

    def test_snack_pack_flag_over_reasons(self) -> None:
        r = {
            "pilot_is_snack_pack": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_snack_pack"]',
        }
        self.assertEqual(row_primary_card_type(r), "Snack-Pack")

    def test_axis_flag(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "2025 Bowman Draft Axis #A-1 Eli Willits Nationals",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman Axis · Base")

    def test_axis_refractor(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Eli Willits Axis Refractor #A-1",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman Axis · Parallel")

    def test_axis_mini_diamond(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Axis Mini Diamond #A-5 Player",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman Axis · Mini Diamond")

    def test_axis_green(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "2025 Bowman Axis Green /99 #A-12",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman Axis · Green")

    def test_axis_slash_99_is_green(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Kayson Cunningham A-8 Axis /99",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman Axis · Green")

    def test_axis_slash_50_is_gold(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Billy Carlson 2/50, Axis, Prized Prospects & Base Chrome",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman Axis · Gold")

    def test_axis_orange_before_refractor(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "#A-1 Eli Willits Axis Orange Refractor /25",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman Axis · Orange")

    def test_axis_superfractor(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "2025 Bowman Axis Superfractor 1/1 #A-3",
        }
        self.assertEqual(row_primary_card_type(r), "Bowman Axis · Superfractor")

    def test_bdc_superfractor_without_chrome_in_title(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Easton Carmichael Superfractor 1/1",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Superfractor")

    def test_bdc_magenta_printing_plate(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Liam Doyle 1st Bowman Magenta Printing Plate 1/1",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Magenta Printing Plate")

    def test_legacy_printing_plate_nb_auto_without_wf_auto_stays_non_auto(self) -> None:
        """``nb_auto`` next to ``nb_printing_plate`` must not imply **Chrome · Auto** without ``WF_auto``."""
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["nb_auto", "nb_printing_plate"]',
            "title": "dummy",
        }
        fake_flags = {
            "WF_printing_plate": True,
            "WF_auto": False,
            "WF_lot": False,
            "WF_pick": False,
            "WF_set_builder": False,
            "WF_complete_set": False,
            "WF_presale": False,
            "WF_snack_pack": False,
            "WF_axis": False,
            "WF_orange_border": False,
            "WF_graded": False,
        }
        with (
            patch("cardmatch.card_type.build_composite_card_type", return_value=None),
            patch("cardmatch.card_type._flags_for_row", return_value=fake_flags),
            patch("cardmatch.card_type._legacy_from_title_flags", return_value=None),
        ):
            self.assertEqual(legacy_primary_card_type(r), "Chrome · Printing Plate /1")

    def test_bdc_true_black_slash_10(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Brandon Compton True Black 10/10 1st Bowman",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · True Black /10")

    def test_bdc_black_geometric_slash_10(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Ty Harvey Geometric Black Bowman Chrome 1st /10",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Black Geometric /10")

    def test_base_paper_black_border_bd_number(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "#BD-163 Jonny Farmelo Black Border #/1",
        }
        self.assertEqual(row_primary_card_type(r), "Base-Paper · Black Border")

    def test_base_paper_black_border_bowman_paper_no_bd_hash(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
            "title": "Konnor Griffin 2025 BOWMAN DRAFT BLACK BORDER PAPER Pirates 1/1",
        }
        self.assertEqual(row_primary_card_type(r), "Base-Paper · Black Border")

    def test_nb_numbered_serial_recovers_print_run_when_year_parsed_as_serial(self) -> None:
        r = {
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_numbered_serial"]',
            "title": "MASON MCCONNAUGHEY Purple Geometric /250/2025 Bowman Draft Baseball",
        }
        self.assertEqual(row_primary_card_type(r), "Chrome · Purple /250")

    def test_parse_axis_insert_number(self) -> None:
        self.assertEqual(parse_axis_insert_number("2025 Bowman Axis #A-12 Nationals"), 12)
        self.assertEqual(parse_axis_insert_number("Axis A-3 Chrome"), 3)
        self.assertEqual(parse_axis_insert_number("no axis number"), 999999)

    def test_relocate_trailing_auto_after_product_segment(self) -> None:
        from cardmatch.taxonomy import relocate_trailing_auto_immediately_after_first_segment

        self.assertEqual(
            relocate_trailing_auto_immediately_after_first_segment(
                "Chrome · Green /99 · Auto"
            ),
            "Chrome · Auto · Green /99",
        )
        self.assertEqual(
            relocate_trailing_auto_immediately_after_first_segment("Chrome /10 · Auto"),
            "Chrome · Auto /10",
        )

    def test_finalize_bdc_aqua_parallel_family_collapses(self) -> None:
        self.assertEqual(
            finalize_bdc_composite_string("Chrome · Aqua Wave · Wave · Auto"),
            "Chrome · Auto · Aqua /125",
        )
        self.assertEqual(
            finalize_bdc_composite_string("Chrome · Aqua · Lava · Auto"),
            "Chrome · Auto · Aqua /125",
        )
        self.assertEqual(
            finalize_bdc_composite_string("Chrome · Aqua Reptilian"),
            "Chrome · Aqua Reptilian",
        )
        self.assertEqual(
            finalize_bdc_composite_string("Chrome · Green · Lava · Auto"),
            "Chrome · Auto · Green /99",
        )
        self.assertEqual(
            finalize_bdc_composite_string("Chrome · Gold · Wave · Shimmer · Auto"),
            "Chrome · Auto · Gold /50",
        )

    def test_listing_counts_exclude_lot_graded_pick_complete_set(self) -> None:
        rows = [
            {
                "pilot_is_snack_pack": "0",
                "pilot_is_axis": "0",
                "pilot_is_orange_border": "0",
                "pilot_is_likely_chrome_base": "0",
                "pilot_is_likely_base": "0",
                "pilot_is_graded": "1",
                "pilot_reason_codes": "[]",
                "title": "2025 Bowman PSA 10 #BDC-1",
                "pilot_player_guess": "A",
            },
            {
                "pilot_is_snack_pack": "0",
                "pilot_is_axis": "0",
                "pilot_is_orange_border": "0",
                "pilot_is_likely_chrome_base": "0",
                "pilot_is_likely_base": "0",
                "pilot_is_graded": "0",
                "pilot_reason_codes": '["nb_lot"]',
                "title": "Lot of 10 Bowman Draft",
                "pilot_player_guess": "B",
            },
            {
                "pilot_is_snack_pack": "0",
                "pilot_is_axis": "0",
                "pilot_is_orange_border": "0",
                "pilot_is_likely_chrome_base": "0",
                "pilot_is_likely_base": "0",
                "pilot_is_graded": "0",
                "pilot_reason_codes": '["nb_pick_or_set_builder"]',
                "title": "Pick your player Bowman",
                "pilot_player_guess": "C",
            },
            {
                "pilot_is_snack_pack": "0",
                "pilot_is_axis": "0",
                "pilot_is_orange_border": "0",
                "pilot_is_likely_chrome_base": "0",
                "pilot_is_likely_base": "0",
                "pilot_is_graded": "0",
                "pilot_reason_codes": '["nb_complete_set"]',
                "title": "Complete set 2025 Bowman Draft",
                "pilot_player_guess": "D",
            },
            {
                "pilot_is_snack_pack": "0",
                "pilot_is_axis": "0",
                "pilot_is_orange_border": "0",
                "pilot_is_likely_chrome_base": "0",
                "pilot_is_likely_base": "0",
                "pilot_is_graded": "0",
                "pilot_reason_codes": "[]",
                "title": "2025 Bowman Draft #BDC-1 Eli Willits Chrome Refractor",
                "pilot_player_guess": "Eli Willits",
            },
        ]
        with tempfile.TemporaryDirectory() as d:
            _, _, counts = write_listing_count_reports(rows, Path(d))
        self.assertEqual(counts.get("Graded", 0), 0)
        self.assertEqual(counts.get("Lot / multi-card", 0), 0)
        self.assertEqual(counts.get("Pick / set builder", 0), 0)
        self.assertEqual(counts.get("Complete set", 0), 0)
        self.assertEqual(counts["Chrome · Refractor"], 1)

    def test_listing_counts_by_card_type_sort_key(self) -> None:
        """Group → non-auto before auto → count descending."""
        items = [
            ("Chrome · Auto · Refractor", 1),
            ("Chrome · Refractor", 2),
            ("Chrome · Green /99", 1),
            ("Bowman Axis · Base", 5),
        ]
        ordered = sorted(items, key=_listing_counts_by_card_type_sort_key)
        self.assertEqual(
            [x[0] for x in ordered],
            [
                "Bowman Axis · Base",
                "Chrome · Refractor",
                "Chrome · Green /99",
                "Chrome · Auto · Refractor",
            ],
        )


if __name__ == "__main__":
    unittest.main()
