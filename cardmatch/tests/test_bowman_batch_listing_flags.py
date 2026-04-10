"""Tests for batch observed-price spread ratio and inversion flags."""

from __future__ import annotations

import unittest
from pathlib import Path

from cardmatch.bowman_batch_listing_flags import (
    analyze_batch_observed_flags,
    cheaper_than_worse_tier_in_batch,
    spread_ratio_second_over_first,
)
from cardmatch.bowman_title_price_predict import classify_bowman_titles_for_batch

_REPO = Path(__file__).resolve().parents[2]
_PILOT = _REPO / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full"


class TestSpreadRatio(unittest.TestCase):
    def test_two_prices(self) -> None:
        self.assertAlmostEqual(spread_ratio_second_over_first([100.0, 200.0]), 2.0)

    def test_tie_at_bottom_ratio_one(self) -> None:
        self.assertAlmostEqual(spread_ratio_second_over_first([100.0, 100.0, 200.0]), 1.0)

    def test_single_price_none(self) -> None:
        self.assertIsNone(spread_ratio_second_over_first([50.0]))

    def test_empty_none(self) -> None:
        self.assertIsNone(spread_ratio_second_over_first([]))


class TestInversionSynthetic(unittest.TestCase):
    def test_serial_example_only_middle_tier_flagged(self) -> None:
        """/10 min below /50 min; other tiers not flagged."""
        ct_map = {
            "t1": 1,
            "t5": 2,
            "t10": 3,
            "t50": 4,
            "t100": 5,
        }
        min_price_by_ct = {
            "t1": 1000.0,
            "t5": 500.0,
            "t10": 150.0,
            "t50": 200.0,
            "t100": 25.0,
        }
        ct_median = 3.0
        self.assertFalse(
            cheaper_than_worse_tier_in_batch(1000.0, "t1", min_price_by_ct, ct_map, ct_median)
        )
        self.assertFalse(
            cheaper_than_worse_tier_in_batch(500.0, "t5", min_price_by_ct, ct_map, ct_median)
        )
        self.assertTrue(
            cheaper_than_worse_tier_in_batch(150.0, "t10", min_price_by_ct, ct_map, ct_median)
        )
        self.assertFalse(
            cheaper_than_worse_tier_in_batch(200.0, "t50", min_price_by_ct, ct_map, ct_median)
        )
        self.assertFalse(
            cheaper_than_worse_tier_in_batch(25.0, "t100", min_price_by_ct, ct_map, ct_median)
        )

    def test_t10_expensive_listing_not_flagged(self) -> None:
        ct_map = {"t10": 3, "t50": 4}
        min_price_by_ct = {"t10": 300.0, "t50": 200.0}
        self.assertFalse(
            cheaper_than_worse_tier_in_batch(300.0, "t10", min_price_by_ct, ct_map, 3.0)
        )


class TestAnalyzeBatchObservedFlags(unittest.TestCase):
    def test_analyze_parallel_indices(self) -> None:
        """a is better (rank 1) than b (rank 2); listings on a cheaper than b's floor are flagged."""
        ct_map = {"a": 1, "b": 2}
        n = 4
        flags = analyze_batch_observed_flags(
            card_type_norm_by_index=["a", "a", "b", "b"],
            classification_excluded=[False, False, False, False],
            classification_batch_error=[None] * n,
            listing_prices=[10.0, 20.0, 50.0, 60.0],
            ct_map=ct_map,
            ct_median=1.0,
            is_serial_listing=[True, True, True, True],
        )
        self.assertEqual(len(flags), 4)
        self.assertAlmostEqual(flags[0].spread_ratio, 2.0)
        self.assertAlmostEqual(flags[1].spread_ratio, 2.0)
        self.assertAlmostEqual(flags[2].spread_ratio, 60.0 / 50.0)
        self.assertAlmostEqual(flags[3].spread_ratio, 60.0 / 50.0)
        self.assertTrue(flags[0].cheaper_than_worse_tier)
        self.assertTrue(flags[1].cheaper_than_worse_tier)
        self.assertFalse(flags[2].cheaper_than_worse_tier)
        self.assertFalse(flags[3].cheaper_than_worse_tier)

    def test_inversion_na_when_not_serial(self) -> None:
        """Non-serial rows get null inversion even when raw tier math would apply."""
        ct_map = {"a": 1, "b": 2}
        n = 2
        flags = analyze_batch_observed_flags(
            card_type_norm_by_index=["a", "b"],
            classification_excluded=[False, False],
            classification_batch_error=[None] * n,
            listing_prices=[10.0, 50.0],
            ct_map=ct_map,
            ct_median=1.0,
            is_serial_listing=[False, True],
        )
        self.assertIsNone(flags[0].cheaper_than_worse_tier)
        self.assertFalse(flags[1].cheaper_than_worse_tier)


class TestClassifyBatchLotExcluded(unittest.TestCase):
    def test_lot_title_excluded(self) -> None:
        """Same structural exclusion as rank-price prediction."""
        out = classify_bowman_titles_for_batch(
            ["2025 Bowman Draft LOT 10 cards Eli Willits"],
            checklist=None,
        )
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].excluded)
        self.assertEqual(out[0].exclude_reason, "excluded_listing")
        self.assertIsNotNone(out[0].pilot_result)


if __name__ == "__main__":
    unittest.main()
