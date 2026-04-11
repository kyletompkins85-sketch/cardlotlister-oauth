from __future__ import annotations

import unittest

from cardmatch.pairwise_price_rankings import (
    PairwiseEntityStats,
    aggregate_listing_count_and_avg_price_by_card_type,
    aggregate_listing_count_and_avg_price_by_player,
    aggregate_listing_count_and_median_price_by_player_for_card_type,
    build_ranking_export_rows,
    coerce_sim_rows,
    listing_triples_to_sim_rows,
    run_monte_carlo_card_type_rankings_same_player,
    run_monte_carlo_player_rankings_same_card_type,
    run_pairwise_monte_carlo_rankings,
)


class TestPairwisePriceRankings(unittest.TestCase):
    def test_triples_round_trip(self) -> None:
        t = listing_triples_to_sim_rows(
            [
                ("A", "T1", 1.0),
                ("A", "T2", 2.0),
                ("B", "T1", 3.0),
            ]
        )
        self.assertEqual(len(t), 3)

    def test_card_type_sim_deterministic_small(self) -> None:
        rows = listing_triples_to_sim_rows(
            [
                ("P", "Cheap", 1.0),
                ("P", "Expensive", 10.0),
            ]
        )
        r = run_monte_carlo_card_type_rankings_same_player(rows, iterations=200, seed=1)
        self.assertEqual(r.phase1_scored_duels, 200)
        self.assertEqual(r.phase2_scored_duels, 0)
        self.assertEqual(r.iterations_made, 200)
        by_name = {s.name: s for s in r.stats}
        self.assertIn("Cheap", by_name)
        self.assertIn("Expensive", by_name)
        self.assertGreater(by_name["Expensive"].win_rate, by_name["Cheap"].win_rate)

    def test_player_sim_deterministic_small(self) -> None:
        rows = listing_triples_to_sim_rows(
            [
                ("CheapPlayer", "CT", 1.0),
                ("ExpensivePlayer", "CT", 20.0),
            ]
        )
        r = run_monte_carlo_player_rankings_same_card_type(rows, iterations=200, seed=2)
        self.assertEqual(r.iterations_made, 200)
        by_name = {s.name: s for s in r.stats}
        self.assertGreater(by_name["ExpensivePlayer"].win_rate, by_name["CheapPlayer"].win_rate)

    def test_card_type_phase2_min_duels_per_type(self) -> None:
        rows = listing_triples_to_sim_rows(
            [
                ("P", "A", 1.0),
                ("P", "B", 10.0),
                ("Q", "A", 2.0),
                ("Q", "B", 3.0),
            ]
        )
        r = run_monte_carlo_card_type_rankings_same_player(
            rows, iterations=10, min_duels_per_card_type=40, seed=0
        )
        self.assertEqual(r.phase1_scored_duels, 10)
        self.assertGreater(r.phase2_scored_duels, 0)
        by_name = {s.name: s for s in r.stats}
        for name in ("A", "B"):
            self.assertGreaterEqual(by_name[name].played, 40)

    def test_run_bundle_triples(self) -> None:
        triples = [
            ("P", "A", 1.0),
            ("P", "B", 5.0),
            ("Q", "A", 2.0),
            ("Q", "B", 3.0),
        ]
        b = run_pairwise_monte_carlo_rankings(triples, iterations=100, seed=3)
        self.assertGreater(len(b.same_player_card_types.stats), 0)
        self.assertGreater(len(b.same_card_type_players.stats), 0)

    def test_coerce_five_tuple(self) -> None:
        rows = coerce_sim_rows([("a", "b", 1.0, "s", "t")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], "s")

    def test_aggregate_listing_stats(self) -> None:
        rows = listing_triples_to_sim_rows(
            [
                ("P", "T1", 10.0),
                ("P", "T1", 20.0),
                ("Q", "T2", 5.0),
            ]
        )
        bp = aggregate_listing_count_and_avg_price_by_player(rows)
        self.assertEqual(bp["P"], (2, 15.0))
        self.assertEqual(bp["Q"], (1, 5.0))
        bct = aggregate_listing_count_and_avg_price_by_card_type(rows)
        self.assertEqual(bct["T1"], (2, 15.0))
        self.assertEqual(bct["T2"], (1, 5.0))

    def test_aggregate_player_for_one_card_type_median(self) -> None:
        rows = listing_triples_to_sim_rows(
            [
                ("P", "Base-Paper", 10.0),
                ("P", "Base-Paper", 20.0),
                ("P", "Chrome · Refractor", 100.0),
                ("Q", "Base-Paper", 5.0),
            ]
        )
        bp = aggregate_listing_count_and_median_price_by_player_for_card_type(rows, card_type="Base-Paper")
        self.assertEqual(bp["P"], (2, 15.0))
        self.assertEqual(bp["Q"], (1, 5.0))

    def test_build_ranking_export_rows(self) -> None:
        stats = [
            PairwiseEntityStats(name="b", wins=1, losses=1, win_rate=0.5, avg_win_margin=1.0, played=2),
            PairwiseEntityStats(name="a", wins=3, losses=1, win_rate=0.75, avg_win_margin=2.0, played=4),
        ]
        listing = {"a": (10, 2.0), "b": (5, 4.0)}
        rows = build_ranking_export_rows(stats, listing, name_field="player_name", descending_win_rate=True)
        self.assertEqual(rows[0]["rank"], 1)
        self.assertEqual(rows[0]["player_name"], "a")
        self.assertEqual(rows[0]["listing_count"], 10)
        self.assertEqual(rows[0]["avg_listing_price"], 2.0)
        self.assertEqual(rows[1]["player_name"], "b")


if __name__ == "__main__":
    unittest.main()
