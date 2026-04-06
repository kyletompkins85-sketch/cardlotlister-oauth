from __future__ import annotations

import unittest

from cardmatch.worker_fetch import (
    dedupe_rows_by_run_and_item,
    filter_rows_exclude_title_substrings,
)


class TestWorkerFetchHelpers(unittest.TestCase):
    def test_filter_excludes_substrings(self) -> None:
        rows = [
            {"title": "2025 Bowman Draft Foo"},
            {"title": "2024 Bowman Draft Bar"},
        ]
        out = filter_rows_exclude_title_substrings(rows, ["2024"])
        self.assertEqual(len(out), 1)
        self.assertIn("Foo", out[0]["title"])

    def test_dedupe_by_run_and_item(self) -> None:
        rows = [
            {"run_id": "a", "item_id": "1", "title": "x"},
            {"run_id": "a", "item_id": "1", "title": "dup"},
            {"run_id": "a", "item_id": "2", "title": "y"},
        ]
        out = dedupe_rows_by_run_and_item(rows)
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
