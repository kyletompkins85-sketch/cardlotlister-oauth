from __future__ import annotations

import unittest
from pathlib import Path

from cardmatch.player_index import default_checklist_path, load_bowman_draft_players
from cardmatch.player_match import expand_concatenated_names, guess_player_from_title


class TestPlayerMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        checklist = default_checklist_path(Path(__file__).resolve().parents[2])
        cls.names, cls.last_index = load_bowman_draft_players(checklist)

    def test_expand_concatenated_names(self) -> None:
        self.assertEqual(
            expand_concatenated_names("WalkerJenkins Axis #A-14"),
            "Walker Jenkins Axis #A-14",
        )

    def test_walker_jenkins_smashed(self) -> None:
        g, sc, _ = guess_player_from_title(
            "WalkerJenkins Axis #A-14 Minnesota Twins",
            self.names,
            self.last_index,
        )
        self.assertEqual(g, "Walker Jenkins")
        self.assertGreaterEqual(sc, 99.0)

    def test_mc_donald_not_split(self) -> None:
        t = expand_concatenated_names("John McDonald Chrome")
        self.assertEqual(t, "John McDonald Chrome")

    def test_typo_lastname_gonalez(self) -> None:
        g, sc, _ = guess_player_from_title(
            "Insert Josuar Gonalez #A-17 Giants",
            self.names,
            self.last_index,
        )
        self.assertEqual(g, "Josuar Gonzalez")
        self.assertGreaterEqual(sc, 55.0)

    def test_typo_gonalez_axis_insert_title(self) -> None:
        g, sc, _ = guess_player_from_title(
            "Josuar Gonalez Axis insert A-17 Giants",
            self.names,
            self.last_index,
        )
        self.assertEqual(g, "Josuar Gonzalez")
        self.assertGreaterEqual(sc, 55.0)

    def test_leo_devries_lowercase_v(self) -> None:
        """DeVries split uses e+V only when V is caps; lowercase 'devries' must still match."""
        g, sc, _ = guess_player_from_title(
            "leo devries axis a-19 athletics",
            self.names,
            self.last_index,
        )
        self.assertEqual(g, "Leo De Vries")
        self.assertGreaterEqual(sc, 55.0)


if __name__ == "__main__":
    unittest.main()
