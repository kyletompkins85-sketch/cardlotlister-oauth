from __future__ import annotations

import unittest

from cardmatch.bowman_pilot_triples import bowman_pilot_row_to_triple


class TestBowmanPilotTriples(unittest.TestCase):
    def test_excludes_lot_like_listing_counts(self) -> None:
        row = {
            "pilot_player_guess": "Test Player",
            "price": "9.99",
            "shipping_cost": "",
            "title": "LOT OF 10 2025 Bowman Draft Chrome Prospects",
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": "[]",
        }
        self.assertIsNone(bowman_pilot_row_to_triple(row))

    def test_keeps_normal_listing(self) -> None:
        row = {
            "pilot_player_guess": "Test Player",
            "price": "9.99",
            "shipping_cost": "",
            "title": "2025 Bowman Draft Eli Willits 1st Bowman Chrome #BDC-1 Nationals",
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_likely_base": "0",
            "pilot_reason_codes": '["not_likely_base", "nb_chrome", "nb_bdc"]',
        }
        t = bowman_pilot_row_to_triple(row)
        self.assertIsNotNone(t)
        self.assertEqual(t[0], "Test Player")


if __name__ == "__main__":
    unittest.main()
