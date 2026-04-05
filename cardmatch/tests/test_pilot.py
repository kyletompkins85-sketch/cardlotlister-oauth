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

    def test_unknown_player(self) -> None:
        r = match_pilot(
            "2025 Bowman Draft Complete Set 1-200",
            self.names,
            self.last_index,
        )
        self.assertEqual(r.player_status, "unknown")


if __name__ == "__main__":
    unittest.main()
