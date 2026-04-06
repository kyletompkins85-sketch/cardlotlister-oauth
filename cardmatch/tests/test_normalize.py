from __future__ import annotations

import unittest

from cardmatch.normalize import abridge_listing_title


class TestAbridge(unittest.TestCase):
    def test_strips_2025_bowman_draft(self) -> None:
        self.assertEqual(
            abridge_listing_title("2025 Bowman Draft Eli Willits Nationals"),
            "Eli Willits Nationals",
        )

    def test_strips_bowman_draft_mid_string(self) -> None:
        self.assertEqual(
            abridge_listing_title("Eli Willits 2025 Bowman Draft Prized Prospects"),
            "Eli Willits Prized Prospects",
        )

    def test_uppercase(self) -> None:
        t = abridge_listing_title("2025 BOWMAN DRAFT CHROME Mason Peters #BDC-27")
        self.assertNotIn("Bowman Draft", t)
        self.assertIn("Mason Peters", t)

    def test_draft_glued_to_1st(self) -> None:
        t = abridge_listing_title("2025 Bowman Draft1st Prospect Paper Base Eli Willits")
        self.assertNotIn("Bowman Draft", t)
        self.assertIn("Eli Willits", t)


if __name__ == "__main__":
    unittest.main()
