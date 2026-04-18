"""Tests for card_type_display_order (cheap-to-expensive ladder)."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from cardmatch.card_type_display_order import (
    DEFAULT_DISPLAY_ORDER_CSV,
    DISPLAY_ORDER_WHEN_PAIRWISE_UNKNOWN,
    dense_renumber_display_order_column,
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
from cardmatch.taxonomy import insert_line_card_type_collapsed_for_display


class TestDenseRenumber(unittest.TestCase):
    def test_dense_renumber_keeps_sentinel_and_error_types(self) -> None:
        rows = [
            {"display_order": 50, "card_type": "A"},
            {"display_order": 999, "card_type": "Bowman In Action · Blue /150"},
            {"display_order": 9, "card_type": "B"},
        ]
        dense_renumber_display_order_column(rows)
        self.assertEqual(rows[0]["display_order"], 1)
        self.assertEqual(rows[1]["display_order"], 999)
        self.assertEqual(rows[2]["display_order"], 2)


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

    def test_committed_csv_has_no_fallback_rank_match_rows(self) -> None:
        p = Path(__file__).resolve().parents[1] / "card_type_display_order.csv"
        with p.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                self.assertNotEqual(
                    (row.get("rank_match") or "").strip().lower(),
                    "fallback",
                    msg=f"Committed CSV should omit no-pairwise types: {row!r}",
                )

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

    def test_omit_insert_line_exact_when_collapses_to_explicit(self) -> None:
        """Omit exact pairwise rows that duplicate explicit insert ladder labels after collapse."""
        self.assertTrue(
            should_omit_display_order_row(
                "Prized Prospects /99", "exact", "Prized Prospects /99"
            )
        )
        self.assertTrue(
            should_omit_display_order_row(
                "Prized Prospects /99 · Auto", "exact", "Prized Prospects /99 · Auto"
            )
        )
        self.assertTrue(
            should_omit_display_order_row(
                "Prized Prospects /50", "exact", "Prized Prospects /50"
            )
        )
        self.assertTrue(
            should_omit_display_order_row(
                "Bowman Draft Night /99", "exact", "Bowman Draft Night /99"
            )
        )
        self.assertTrue(
            should_omit_display_order_row(
                "Bowman In Action /99", "exact", "Bowman In Action /99"
            )
        )
        self.assertTrue(
            should_omit_display_order_row(
                "Bowman In Action /150", "exact", "Bowman In Action /150"
            )
        )
        self.assertFalse(
            should_omit_display_order_row(
                "Prized Prospects · Green /99", "exact", "Prized Prospects · Green /99"
            )
        )
        self.assertEqual(
            insert_line_card_type_collapsed_for_display("Prized Prospects /250"),
            "Prized Prospects · Purple /250",
        )


class TestResolveOmitted(unittest.TestCase):
    def test_resolve_prized_prospects_bare_slash_n_maps_to_green_in_merged(self) -> None:
        """Stale bare PP /N keys resolve via the same ladder label as taxonomy."""
        m = {"Prized Prospects · Green /99": 17}
        self.assertEqual(
            resolve_display_order("Prized Prospects /99", m, pairwise_card_type_csv=None),
            17,
        )

    def test_resolve_bowman_draft_night_bare_slash_99_maps_to_green_in_merged(self) -> None:
        m = {"Bowman Draft Night · Green /99": 40}
        self.assertEqual(
            resolve_display_order("Bowman Draft Night /99", m, pairwise_card_type_csv=None),
            40,
        )

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
        elif "Bowman Draft Night · Green /99" in m:
            self.assertEqual(r, m["Bowman Draft Night · Green /99"])
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


class TestPairwiseUnknownSentinel(unittest.TestCase):
    def test_resolve_uses_999_when_no_pairwise_match(self) -> None:
        pilot = (
            Path(__file__).resolve().parents[2]
            / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/bowman_pairwise_card_type_rankings_with_listings.csv"
        )
        if not pilot.is_file():
            self.skipTest("pairwise CSV not present")
        m = load_display_order_csv(DEFAULT_DISPLAY_ORDER_CSV)
        r = resolve_display_order(
            "__zz_nonexistent_card_type__",
            m,
            pairwise_card_type_csv=pilot,
        )
        self.assertEqual(r, DISPLAY_ORDER_WHEN_PAIRWISE_UNKNOWN)

    def test_resolve_inferred_auto_matches_non_auto_display_order(self) -> None:
        """``… · Auto`` tiers not in the CSV still resolve via pairwise inference (same rank as base)."""
        pilot = (
            Path(__file__).resolve().parents[2]
            / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/bowman_pairwise_card_type_rankings_with_listings.csv"
        )
        if not pilot.is_file():
            self.skipTest("pairwise CSV not present")
        merged = load_merged_display_order()
        auto_ct = "Prized Prospects · Auto · Red /5"
        if auto_ct in merged:
            self.skipTest("auto row present in merged map")
        base = merged.get("Prized Prospects · Red /5")
        if base is None:
            self.skipTest("base red /5 not in display order CSV")
        r = resolve_display_order(auto_ct, merged, pairwise_card_type_csv=pilot)
        self.assertEqual(r, base)

    def test_infer_missing_chrome_slash_three_auto(self) -> None:
        pilot = (
            Path(__file__).resolve().parents[2]
            / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full/bowman_pairwise_card_type_rankings_with_listings.csv"
        )
        if not pilot.is_file():
            self.skipTest("pairwise CSV not present")
        merged = load_merged_display_order()
        do = display_order_for_card_type(
            "Chrome /3 · Auto",
            merged,
            infer_missing=True,
            pairwise_card_type_csv=pilot,
        )
        self.assertIsInstance(do, int)
        self.assertLess(do, DISPLAY_ORDER_WHEN_PAIRWISE_UNKNOWN)
        self.assertEqual(
            resolve_display_order(
                "Chrome /3 · Auto", merged, pairwise_card_type_csv=pilot
            ),
            resolve_display_order(
                "Chrome · Auto /3", merged, pairwise_card_type_csv=pilot
            ),
        )


if __name__ == "__main__":
    unittest.main()
