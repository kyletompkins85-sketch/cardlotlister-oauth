"""Tests for :mod:`cardmatch.serial_scarcity`."""

from __future__ import annotations

import unittest

from cardmatch.serial_scarcity import is_serial_listing_from_bowman_flags, serial_scarcity_from_flags


class TestSerialScarcity(unittest.TestCase):
    def test_numbered(self) -> None:
        v, numbered = serial_scarcity_from_flags({"serial_out_of": 5})
        self.assertTrue(numbered)
        self.assertAlmostEqual(v, 0.2)

    def test_unnumbered(self) -> None:
        v, numbered = serial_scarcity_from_flags({})
        self.assertFalse(numbered)
        self.assertIsNone(v)

    def test_is_serial_from_serial_out_of(self) -> None:
        self.assertTrue(is_serial_listing_from_bowman_flags({"serial_out_of": 99}))

    def test_is_serial_from_is_numbered(self) -> None:
        self.assertTrue(is_serial_listing_from_bowman_flags({"is_numbered": True}))

    def test_is_serial_false(self) -> None:
        self.assertFalse(is_serial_listing_from_bowman_flags({}))

    def test_title_slash_print_run(self) -> None:
        self.assertTrue(
            is_serial_listing_from_bowman_flags({}, title="2025 Bowman Draft Green /10 Eli Willits")
        )

    def test_title_slash_one(self) -> None:
        self.assertTrue(
            is_serial_listing_from_bowman_flags({}, title="2025 Bowman Chrome Prospect Speckle /1")
        )

    def test_title_fraction_serial(self) -> None:
        self.assertTrue(is_serial_listing_from_bowman_flags({}, title="SSP 1/1 Eli Willits"))

    def test_title_year_after_slash_skipped(self) -> None:
        self.assertFalse(
            is_serial_listing_from_bowman_flags({}, title="/2025 Bowman Draft Chrome Prospect")
        )

    def test_fullwidth_slash_print_run(self) -> None:
        self.assertTrue(
            is_serial_listing_from_bowman_flags({}, title="Green \uFF0F99 Eli Willits")
        )

    def test_hash_slash_print_run(self) -> None:
        self.assertTrue(is_serial_listing_from_bowman_flags({}, title="#/99"))

    def test_hash_digits_print_run(self) -> None:
        self.assertTrue(is_serial_listing_from_bowman_flags({}, title="# 150"))


if __name__ == "__main__":
    unittest.main()
