"""Tests for Bowman title → rank price prediction."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

import cardmatch.bowman_title_price_predict as bowman_pred
from cardmatch.bowman_title_price_predict import (
    BowmanTitlePricePrediction,
    _row_eligible_for_rank_price_prediction,
    predict_bowman_price_from_title,
    predict_bowman_prices_from_titles,
)

_REPO = Path(__file__).resolve().parents[2]
_PILOT = _REPO / "data/cardmatch_pilot/20260405_mcp_supabase_2025_bowman_draft_full"
_PL = _PILOT / "bowman_pairwise_player_rankings_with_listings.csv"
_CT = _PILOT / "bowman_pairwise_card_type_rankings_with_listings.csv"
_AG = _PILOT / "bowman_rank_price_autogluon/agModels"


class TestRowEligible(unittest.TestCase):
    def test_lot_title_excluded(self) -> None:
        row = {
            "title": "2025 Bowman Draft LOT 10 cards Eli Willits",
            "pilot_player_guess": "Eli Willits",
            "pilot_player_score": "0.90",
            "pilot_player_status": "ok",
            "pilot_is_likely_base": "0",
            "pilot_is_graded": "0",
            "pilot_is_lot": "1",
            "pilot_is_draft_night": "0",
            "pilot_is_chrome": "1",
            "pilot_is_orange_border": "0",
            "pilot_is_likely_chrome_base": "0",
            "pilot_is_snack_pack": "0",
            "pilot_is_axis": "0",
            "pilot_reason_codes": "[]",
            "matcher_version": "test",
        }
        ok, reason = _row_eligible_for_rank_price_prediction(row)
        self.assertFalse(ok)
        self.assertEqual(reason, "excluded_listing")


class TestPredictBowmanPriceFromTitle(unittest.TestCase):
    def test_excluded_returns_no_price_without_autogluon(self) -> None:
        """Pick-your titles are excluded; prediction must not load AutoGluon."""
        mock_tp = MagicMock()
        with patch.object(bowman_pred, "TabularPredictor", mock_tp):
            out = predict_bowman_price_from_title(
                "2025 Bowman Draft Pick Your Player 2025 Bowman Draft Chrome",
                player_rankings_csv=_PL,
                card_type_rankings_csv=_CT,
                autogluon_model_dir=_AG,
            )
        self.assertTrue(out.excluded)
        self.assertIsNone(out.predicted_price)
        mock_tp.load.assert_not_called()

    @unittest.skipUnless(
        os.environ.get("RUN_BOWMAN_AG_INTEGRATION") == "1",
        "set RUN_BOWMAN_AG_INTEGRATION=1 to run AutoGluon integration",
    )
    def test_integration_real_model_if_present(self) -> None:
        if not (_PL.is_file() and _CT.is_file() and _AG.is_dir()):
            self.skipTest("pairwise CSVs or agModels missing")
        out = predict_bowman_price_from_title(
            "2025 Bowman Draft #BDC-1 Green Refractor Eli Willits",
            player_rankings_csv=_PL,
            card_type_rankings_csv=_CT,
            autogluon_model_dir=_AG,
        )
        self.assertIsInstance(out, BowmanTitlePricePrediction)
        if not out.excluded:
            self.assertIsNotNone(out.predicted_price)
            self.assertGreater(out.predicted_price or 0, 0.0)

    def test_mock_predictor_returns_float(self) -> None:
        if not (_PL.is_file() and _CT.is_file()):
            self.skipTest("pairwise CSVs missing")
        fake_instance = MagicMock()
        fake_instance.predict = MagicMock(return_value=pd.Series([12.34]))
        mock_tp = MagicMock()
        mock_tp.load = MagicMock(return_value=fake_instance)

        with patch.object(bowman_pred, "TabularPredictor", mock_tp):
            out = predict_bowman_price_from_title(
                "2025 Bowman Draft #BDC-1 Green Refractor Eli Willits",
                player_rankings_csv=_PL,
                card_type_rankings_csv=_CT,
                autogluon_model_dir=_AG,
            )
        if out.excluded:
            self.skipTest("title unexpectedly excluded")
        self.assertFalse(out.excluded)
        self.assertAlmostEqual(out.predicted_price, 12.34, places=2)
        mock_tp.load.assert_called_once()
        fake_instance.predict.assert_called_once()

    def test_batch_calls_predict_once_with_two_rows(self) -> None:
        if not (_PL.is_file() and _CT.is_file()):
            self.skipTest("pairwise CSVs missing")
        t = "2025 Bowman Draft #BDC-1 Green Refractor Eli Willits"
        fake_instance = MagicMock()
        fake_instance.predict = MagicMock(return_value=pd.Series([10.0, 20.0]))
        mock_tp = MagicMock()
        mock_tp.load = MagicMock(return_value=fake_instance)

        with patch.object(bowman_pred, "TabularPredictor", mock_tp):
            outs = predict_bowman_prices_from_titles(
                [t, t],
                player_rankings_csv=_PL,
                card_type_rankings_csv=_CT,
                autogluon_model_dir=_AG,
            )
        if outs[0].excluded:
            self.skipTest("title unexpectedly excluded")
        self.assertEqual(len(outs), 2)
        self.assertAlmostEqual(outs[0].predicted_price or 0, 10.0, places=2)
        self.assertAlmostEqual(outs[1].predicted_price or 0, 20.0, places=2)
        mock_tp.load.assert_called_once()
        fake_instance.predict.assert_called_once()
        call_kw = fake_instance.predict.call_args[0][0]
        self.assertEqual(len(call_kw), 2)
