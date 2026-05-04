from __future__ import annotations

import unittest
from pathlib import Path

from cardmatch.bowman_2025_retail_batch_deals import RetailBatchInputItem, analyze_retail_batch_deals
from cardmatch.bowman_2025_retail_combo_catalog import load_combo_sort_index
from cardmatch.bowman_2025_retail_steps import load_retail_api_context, retail_steps_row_extensions


_REPO = Path(__file__).resolve().parents[2]
_COMBO = _REPO / "data/checklists/normalized/2025_Bowman_retail_card_type_serial_combos_observed.csv"


class TestRetailBatchDeals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = load_retail_api_context()
        cls.combo = load_combo_sort_index(_COMBO)

    def test_retail_extensions_matches_process_title_shape(self):
        title = "2025 Bowman Aaron Judge #99 Yankees"
        ext = retail_steps_row_extensions(title, self.ctx)
        self.assertEqual(ext["excluded"], "0")
        self.assertEqual(ext["match_status_after_step3"], "matched")
        self.assertEqual(ext["matched_card_type"], "Base")

    def test_spread_ratios_three_prices_same_cluster(self):
        t = "2025 Bowman #99 Aaron Judge Yankees"
        items = [
            RetailBatchInputItem(title=t, price=10.0, id="a"),
            RetailBatchInputItem(title=t, price=12.0, id="b"),
            RetailBatchInputItem(title=t, price=15.0, id="c"),
        ]
        results, groups = analyze_retail_batch_deals(items, self.ctx, self.combo)
        self.assertEqual(len(results), 3)
        mins = [r for r in results if r["listing_price"] == 10.0]
        self.assertEqual(len(mins), 1)
        self.assertAlmostEqual(mins[0]["spread_ratio"], 12.0 / 10.0, places=6)
        self.assertAlmostEqual(mins[0]["spread_ratio_third"], 15.0 / 10.0, places=6)
        self.assertIsNotNone(mins[0]["savings_vs_second_listing_pct"])
        self.assertAlmostEqual(mins[0]["savings_vs_second_listing_pct"], (12.0 - 10.0) / 12.0, places=6)
        hi = [r for r in results if r["listing_price"] == 15.0][0]
        self.assertIsNone(hi["spread_ratio"])
        # Draft-style grouping string: same display_name but serial in key when not -1
        self.assertEqual(results[0]["card_type"], "Paper")
        self.assertEqual(results[0]["card_type_display_order"], 1)

    def test_excluded_no_spread(self):
        items = [
            RetailBatchInputItem(title="2025 Bowman Aaron Judge 3 Card lot", price=5.0),
        ]
        results, _groups = analyze_retail_batch_deals(items, self.ctx, self.combo)
        self.assertTrue(results[0]["excluded"])
        self.assertIsNone(results[0]["spread_ratio"])
        self.assertIsNone(results[0]["canonical_card_type"])

    def test_card_type_includes_serial_for_distinct_groups(self):
        """Mirrors Draft: client groups by `card_type` — must embed /serial when not -1."""
        t99 = "2025 Bowman #99 Aaron Judge Yankees"
        t399 = "2025 Bowman - Mike Trout #1 Green /399"
        items = [
            RetailBatchInputItem(title=t99, price=5.0),
            RetailBatchInputItem(title=t399, price=50.0),
        ]
        results, groups = analyze_retail_batch_deals(items, self.ctx, self.combo)
        self.assertNotEqual(results[0]["card_type"], results[1]["card_type"])
        self.assertIn("/399", results[1]["card_type"])

    def test_player_key_splits_cohorts(self):
        t = "2025 Bowman #99 Aaron Judge Yankees"
        items = [
            RetailBatchInputItem(title=t, price=10.0, player_key="Judge"),
            RetailBatchInputItem(title=t, price=20.0, player_key="Other"),
        ]
        results, groups = analyze_retail_batch_deals(items, self.ctx, self.combo)
        self.assertNotEqual(results[0]["player_group_key"], results[1]["player_group_key"])
        self.assertEqual(len(groups), 2)
