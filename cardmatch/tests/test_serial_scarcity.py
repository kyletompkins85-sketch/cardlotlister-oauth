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


if __name__ == "__main__":
    unittest.main()
