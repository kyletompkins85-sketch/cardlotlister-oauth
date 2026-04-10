"""Tests for :mod:`cardmatch.serial_scarcity`."""

from __future__ import annotations

import unittest

from cardmatch.serial_scarcity import serial_scarcity_from_flags


class TestSerialScarcity(unittest.TestCase):
    def test_numbered(self) -> None:
        v, numbered = serial_scarcity_from_flags({"serial_out_of": 5})
        self.assertTrue(numbered)
        self.assertAlmostEqual(v, 0.2)

    def test_unnumbered(self) -> None:
        v, numbered = serial_scarcity_from_flags({})
        self.assertFalse(numbered)
        self.assertIsNone(v)


if __name__ == "__main__":
    unittest.main()
