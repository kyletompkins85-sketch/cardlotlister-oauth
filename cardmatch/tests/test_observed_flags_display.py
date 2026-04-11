"""Tests for :mod:`cardmatch.observed_flags_display`."""

from __future__ import annotations

import unittest

from cardmatch.observed_flags_display import short_card_type_display_for_api


class TestShortCardTypeDisplay(unittest.TestCase):
    def test_base_paper(self) -> None:
        self.assertEqual(short_card_type_display_for_api("Base-Paper"), "base")

    def test_base_paper_black_border(self) -> None:
        self.assertEqual(
            short_card_type_display_for_api("Base-Paper · Black Border"),
            "base · Black Border",
        )

    def test_bdc_chrome_base(self) -> None:
        self.assertEqual(short_card_type_display_for_api("Chrome · Base"), "Chrome")

    def test_legacy_bdc_chrome_prospect_prefix(self) -> None:
        self.assertEqual(short_card_type_display_for_api("BDC Chrome Prospect · Base"), "Chrome")

    def test_bdc_chrome_auto(self) -> None:
        self.assertEqual(short_card_type_display_for_api("Chrome · Auto"), "Chrome Auto")

    def test_bdc_parallel(self) -> None:
        self.assertEqual(
            short_card_type_display_for_api("Chrome · Green /99"),
            "Chrome Green /99",
        )

    def test_bowman_draft_night_green(self) -> None:
        self.assertEqual(
            short_card_type_display_for_api("Bowman Draft Night · Green"),
            "Draft Night Green",
        )

    def test_bowman_draft_night_green_serial(self) -> None:
        self.assertEqual(
            short_card_type_display_for_api("Bowman Draft Night · Green /99"),
            "Draft Night Green /99",
        )

    def test_bowman_draft_night_gold_stack(self) -> None:
        self.assertEqual(
            short_card_type_display_for_api("Bowman Draft Night · Gold · Mini Diamond · Auto"),
            "Draft Night Gold · Mini Diamond · Auto",
        )

    def test_other_types_unchanged(self) -> None:
        self.assertEqual(short_card_type_display_for_api("Graded"), "Graded")


if __name__ == "__main__":
    unittest.main()
