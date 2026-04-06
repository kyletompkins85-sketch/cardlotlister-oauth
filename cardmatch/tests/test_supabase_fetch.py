from __future__ import annotations

import unittest

from cardmatch.supabase_fetch import search_q_to_sql_ilike


class TestSearchQToSqlIlike(unittest.TestCase):
    def test_bowman_draft(self) -> None:
        self.assertEqual(search_q_to_sql_ilike("2025 bowman draft"), "%2025%bowman%draft%")


if __name__ == "__main__":
    unittest.main()
