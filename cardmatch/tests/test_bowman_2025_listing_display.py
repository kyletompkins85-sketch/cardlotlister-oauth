from __future__ import annotations

import unittest

from cardmatch.bowman_2025_listing_display import listing_display_from_title


class TestBowman2025ListingDisplay(unittest.TestCase):
    def test_order_team_then_rc_then_strip_year_bowman_prospects(self):
        t = (
            "2025 Bowman Toronto Blue Jays Bo Bichette RC Rookie Card 1st Bowman "
            "Bowman Chrome Prospects BCP-1 Refractor"
        )
        out = listing_display_from_title(t)
        self.assertNotIn("Toronto", out)
        self.assertNotIn("Blue Jays", out)
        self.assertNotIn("RC", out)
        self.assertNotIn("Rookie Card", out)
        self.assertNotIn("1st Bowman", out)
        self.assertNotIn("Bowman", out)
        self.assertNotIn("Prospects", out)
        self.assertNotIn("Prospect", out)
        self.assertNotIn("2025", out)
        self.assertIn("Chrome", out)
        self.assertIn("BCP-1", out)

    def test_bowman_hyphen_chrome_prospects_leaves_chrome(self):
        self.assertEqual(
            listing_display_from_title("2025 Bowman - Chrome Prospects Walker Jenkins BCP-1").strip(),
            "Chrome Walker Jenkins BCP-1",
        )

    def test_chrome_preserved_bowman_prospects_removed(self):
        s = listing_display_from_title(
            "Bowman - Chrome Prospects and later Bowman Chrome Prospects text"
        )
        self.assertIn("Chrome", s)
        self.assertNotIn("Bowman", s)
        self.assertNotIn("Prospects", s)
        self.assertEqual(s.count("Chrome"), 2)

    def test_extra_noise_words_and_bang(self):
        out = listing_display_from_title(
            "2025 Topps Bowman!!! baseball edition — Free shipping! Chrome BCP-1"
        )
        self.assertNotIn("Topps", out, msg=repr(out))
        self.assertNotIn("baseball", out)
        self.assertNotIn("edition", out)
        self.assertNotIn("shipping", out)
        self.assertNotIn("!", out)
        self.assertIn("Chrome", out)

    def test_spaced_hyphen_removed(self):
        self.assertEqual(
            listing_display_from_title("Walker Jenkins Bowman - Chrome Blue").strip(),
            "Walker Jenkins Chrome Blue",
        )

    def test_prefix_card_number_chrome_serial_then_rest(self):
        title = (
            "2025 Bowman Walker Jenkins Chrome Blue Refractor BCP-1 /150 "
            "Minnesota Twins RC"
        )
        out = listing_display_from_title(title, card_number="BCP-1")
        self.assertTrue(out.startswith("BCP-1 Chrome /150 "), msg=repr(out))
        self.assertIn("Chrome", out)
        self.assertNotIn("BCP-1 BCP-1", out)
        self.assertNotIn("/150 /150", out)

    def test_prefix_without_serial_when_none_in_title(self):
        title = "2025 Bowman Chrome Walker Jenkins BCP-1 Refractor"
        out = listing_display_from_title(title, card_number="BCP-1")
        self.assertTrue(out.startswith("BCP-1 Chrome "), msg=repr(out))
        self.assertNotIn("/150", out)
        self.assertIn("Chrome", out)

    def test_sapphire_stays_in_tail_not_chrome_peel(self):
        out = listing_display_from_title(
            "2025 TOPPS BOWMAN CHROME SAPPHIRE ZYHIR HOPE #BCP-2",
            card_number="BCP-2",
        )
        self.assertTrue(out.startswith("BCP-2 Chrome "), msg=repr(out))
        lo = out.lower()
        self.assertIn("sapphire", lo)
        # Sapphire is a parallel modifier: after the peeled ``Chrome``, not bundled into it.
        self.assertLess(lo.index("chrome"), lo.index("sapphire"), msg=repr(out))

    def test_singular_prospect_dropped(self):
        out = listing_display_from_title(
            "2025 Bowman Walker Jenkins Chrome Prospect Blue BCP-1",
            card_number="BCP-1",
        )
        self.assertNotIn("Prospect", out, msg=repr(out))
        self.assertTrue(out.startswith("BCP-1 Chrome "), msg=repr(out))

    def test_standalone_1st_dropped(self):
        out = listing_display_from_title("2025 Bowman Chrome 1st Year Player BCP-1")
        self.assertNotIn("1st", out, msg=repr(out))
