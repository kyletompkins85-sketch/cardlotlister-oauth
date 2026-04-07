"""Regression: multi-SKU / pick-your-inventory titles must set WF_pick or WF_set_builder."""

from __future__ import annotations

import unittest

from cardmatch.bowman_z10 import classify_bowman_title


class TestBowmanClassifierPickInventory(unittest.TestCase):
    def test_singles_paper_bd_range_flags_pick(self) -> None:
        for t in (
            "Singles Paper BD1-BD200",
            "Singles Paper BD1-BD200 Combined Shipping!",
            "singles paper bd1-bd200",
        ):
            with self.subTest(t):
                wf = classify_bowman_title(t)
                self.assertTrue(
                    wf.get("WF_pick") or wf.get("WF_set_builder"),
                    f"expected pick/set flag: {wf!r}",
                )

    def test_build_your_set_flags_set_builder(self) -> None:
        t = "2025 Bowman/Chrome/Draft - Chrome Prospects & Rookies - Build Your Set"
        wf = classify_bowman_title(t)
        self.assertTrue(wf.get("WF_set_builder") or wf.get("WF_pick"), wf)

    def test_bdc_range_with_card_minimum_flags_pick(self) -> None:
        t = "Baseball, bdc1-bdc200,6 card minimum,20% off, free ship"
        wf = classify_bowman_title(t)
        self.assertTrue(wf.get("WF_pick"), wf)

    def test_inserts_multi_line_flags_pick(self) -> None:
        t = "inserts - In Action, Prized Prospets, Axis, Draft Night"
        wf = classify_bowman_title(t)
        self.assertTrue(wf.get("WF_pick"), wf)

    def test_single_card_title_not_flagged_by_singles_range(self) -> None:
        t = "2025 Bowman Draft #BDC-1 Eli Willits Chrome"
        wf = classify_bowman_title(t)
        self.assertFalse(wf.get("WF_pick"), wf)

    def test_singles_volume_discounts_flags_pick(self) -> None:
        t = "Singles - volume discounts - FREE SHIPPING"
        wf = classify_bowman_title(t)
        self.assertTrue(wf.get("WF_pick"), wf)

    def test_parallels_mojos_chrome_prospects_flags_pick(self) -> None:
        t = "Parallels, Mojos, Chrome Prospects and Inserts"
        wf = classify_bowman_title(t)
        self.assertTrue(wf.get("WF_pick"), wf)


if __name__ == "__main__":
    unittest.main()
