from __future__ import annotations

import unittest
from pathlib import Path

from cardmatch.listing_classification import (
    classify_listing,
    classify_listings,
    pilot_result_to_scored_row,
)
from cardmatch.pilot import match_pilot
from cardmatch.player_index import load_bowman_draft_players


class TestListingClassification(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._root = Path(__file__).resolve().parents[2]
        cls._checklist = cls._root / "data" / "checklists" / "normalized" / "2025_Bowman_Draft_Normalized.csv"

    def test_classify_listing_player_and_card_type(self) -> None:
        title = "2025 Bowman Draft #BDC-1 Green Refractor Eli Willits"
        out = classify_listing(title, checklist=self._checklist)
        self.assertEqual(out.player, "Eli Willits")
        self.assertEqual(out.player_status, "matched")
        self.assertEqual(out.card_type, "Chrome · Green /99")

    def test_classify_listings_reuses_index(self) -> None:
        titles = [
            "2025 Bowman Draft #BDC-1 Green Refractor Eli Willits",
            "2025 Bowman Draft BDC-2 Chrome Xavier Neyens",
        ]
        rows = classify_listings(titles, checklist=self._checklist)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].player, "Eli Willits")
        self.assertTrue(rows[1].player)

    def test_classify_with_preloaded_index_matches_classify_listing(self) -> None:
        title = "2025 Bowman Draft #BDC-1 Green Refractor Eli Willits"
        names, last_index = load_bowman_draft_players(self._checklist)
        a = classify_listing(title, names=names, last_index=last_index)
        b = classify_listing(title, checklist=self._checklist)
        self.assertEqual(a.card_type, b.card_type)
        self.assertEqual(a.player, b.player)

    def test_pilot_result_to_scored_row_round_trip_card_type(self) -> None:
        names, last_index = load_bowman_draft_players(self._checklist)
        title = "2025 Bowman Draft #BDC-1 Green Refractor Eli Willits"
        pr = match_pilot(title, names, last_index)
        row = pilot_result_to_scored_row(title, pr)
        self.assertEqual(row["title"], title)
        self.assertIn("pilot_player_guess", row)
        out = classify_listing(title, names=names, last_index=last_index)
        from cardmatch.card_type import display_card_type_for_review

        self.assertEqual(display_card_type_for_review(row), out.card_type)


if __name__ == "__main__":
    unittest.main()
