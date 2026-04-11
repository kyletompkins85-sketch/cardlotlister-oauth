"""Tests for card_type_display_order (cheap-to-expensive ladder)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cardmatch.card_type_display_order import (
    DEFAULT_DISPLAY_ORDER_CSV,
    display_order_for_card_type,
    load_display_order_csv,
    load_merged_display_order,
    load_overrides_json,
    load_pairwise_rank_column,
    lookup_pairwise_rank_for_taxonomy,
    merge_display_orders,
    pairwise_rank_to_display_order,
    resolve_display_order,
    should_omit_display_order_row,
)


class TestPairwiseInvert(unittest.TestCase):
    def test_invert(self) -> None:
        self.assertEqual(pairwise_rank_to_display_order(1, max_pairwise_rank=5), 5)
        self.assertEqual(pairwise_rank_to_display_order(5, max_pairwise_rank=5), 1)


class TestCommittedCsv(unittest.TestCase):
    def test_csv_loads_and_base_paper_is_cheapest(self) -> None:
        p = Path(__file__).resolve().parents[1] / "card_type_display_order.csv"
        self.assertTrue(p.is_file(), msg="card_type_display_order.csv should exist")
        m = load_display_order_csv(p)
        self.assertGreater(len(m), 10)
        # Base-Paper is cheapest in pairwise export (rank 131 in pilot CSV)
        b = m.get("Base-Paper")
        self.assertIsNotNone(b)
        self.assertEqual(b, 1)
        # Rank 1 pairwise → highest display_order (cheapest is 1).
        mx = max(m.values())
        self.assertGreater(mx, 10)
        self.assertEqual(m["Base-Paper"], 1)

    def test_serial_suffix_row_matches_parent_tier(self) -> None:
        p = Path(__file__).resolve().parents[1] / "card_type_display_order.csv"
        m = load_display_order_csv(p)
        suffixed = m.get("Bowman Draft Night · Green /99")
        self.assertIsNotNone(suffixed)
        plain = m.get("Bowman Draft Night · Green")
        if plain is not None:
            self.assertEqual(plain, suffixed)

    def test_bare_draft_night_slash_n_may_be_in_csv(self) -> None:
        """Bare insert + /N may appear as exact pairwise keys after rescoring."""
        p = Path(__file__).resolve().parents[1] / "card_type_display_order.csv"
        m = load_display_order_csv(p)
        self.assertIsNotNone(m.get("Bowman Draft Night"))


class TestPairwiseInference(unittest.TestCase):
    def test_draft_night_green_slash_99_is_exact_key_in_pairwise(self) -> None:
        pilot = (
            Path(__file__).resolve().parents[2]
            / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/bowman_pairwise_card_type_rankings_with_listings.csv"
        )
        if not pilot.is_file():
            self.skipTest("pairwise CSV not present")
        ct_map, _ = load_pairwise_rank_column(pilot)
        pr, src, mk = lookup_pairwise_rank_for_taxonomy(
            "Bowman Draft Night · Green /99", ct_map
        )
        self.assertEqual(src, "exact")
        self.assertEqual(mk, "Bowman Draft Night · Green /99")
        self.assertEqual(pr, ct_map["Bowman Draft Night · Green /99"])


class TestOmitBare(unittest.TestCase):
    def test_omit_bare_slash_n(self) -> None:
        self.assertTrue(
            should_omit_display_order_row(
                "Bowman Draft Night /99", "inferred", "Bowman Draft Night"
            )
        )
        self.assertFalse(
            should_omit_display_order_row(
                "Bowman Draft Night · Green /99", "inferred", "Bowman Draft Night · Green"
            )
        )


class TestResolveOmitted(unittest.TestCase):
    def test_resolve_bare_matches_generic_tier(self) -> None:
        p = Path(__file__).resolve().parents[1] / "card_type_display_order.csv"
        m = load_display_order_csv(p)
        pilot = (
            Path(__file__).resolve().parents[2]
            / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/bowman_pairwise_card_type_rankings_with_listings.csv"
        )
        if not pilot.is_file():
            self.skipTest("pairwise CSV not present")
        r = resolve_display_order(
            "Bowman Draft Night /99",
            m,
            pairwise_card_type_csv=pilot,
        )
        if "Bowman Draft Night /99" in m:
            self.assertEqual(r, m["Bowman Draft Night /99"])
        else:
            self.assertEqual(r, m["Bowman Draft Night"])


class TestOverridesMerge(unittest.TestCase):
    def test_merge(self) -> None:
        base = {"A": 1, "B": 2}
        self.assertEqual(merge_display_orders(base, {"B": 99})["B"], 99)


class TestOverridesJson(unittest.TestCase):
    def test_loads_sparse(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            t = Path(td) / "o.json"
            t.write_text(
                json.dumps({"overrides": {"Chrome · Base": 50}}),
                encoding="utf-8",
            )
            o = load_overrides_json(t)
            self.assertEqual(o.get("Chrome · Base"), 50)


class TestLoadMerged(unittest.TestCase):
    def test_default_paths_exist(self) -> None:
        self.assertTrue(DEFAULT_DISPLAY_ORDER_CSV.is_file())

    def test_merged_includes_override(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            csv_path = td_path / "t.csv"
            csv_path.write_text(
                "display_order,pairwise_rank,card_type\n1,3,Alpha\n2,2,Beta\n",
                encoding="utf-8",
            )
            ovr = td_path / "o.json"
            ovr.write_text(
                json.dumps({"overrides": {"Beta": 1}}),
                encoding="utf-8",
            )
            m = load_merged_display_order(csv_path=csv_path, overrides_path=ovr)
            self.assertEqual(m["Alpha"], 1)
            self.assertEqual(m["Beta"], 1)


class TestLookup(unittest.TestCase):
    def test_fallback(self) -> None:
        self.assertIsNone(
            display_order_for_card_type("unknown", {"X": 1}, fallback=None)
        )
        self.assertEqual(
            display_order_for_card_type("unknown", {}, fallback=999),
            999,
        )


if __name__ == "__main__":
    unittest.main()
