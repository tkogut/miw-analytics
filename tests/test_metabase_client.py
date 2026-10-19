"""
Unit tests for MetabaseClient security invariants and read-only enforcement.
"""

import unittest
from pathlib import Path
import sys

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from metabase_client import MetabaseClient, ReadOnlyViolationError


class TestMetabaseClientReadOnly(unittest.TestCase):
    def setUp(self):
        self.client = MetabaseClient(
            base_url="https://dummy.reports",
            user="test@miw.group",
            password="dummy_password",
            database_id=15,
            session_cache_path="/tmp/test_session_cache.json",
        )

    def test_valid_select_queries(self):
        valid_queries = [
            "SELECT 1;",
            "SELECT id, name FROM res_company WHERE id = 1;",
            "WITH monthly_sales AS (SELECT to_char(date_order, 'YYYY-MM') as m, sum(amount_untaxed) as s FROM sale_order GROUP BY m) SELECT * FROM monthly_sales;",
            "EXPLAIN SELECT * FROM res_currency;",
            "   \n  SELECT * FROM sale_order; -- comment with insert into something\n",
        ]
        for q in valid_queries:
            try:
                self.client.validate_read_only(q)
            except Exception as e:
                self.fail(f"Valid query failed read-only check: {q} with error: {e}")

    def test_forbidden_mutating_queries(self):
        forbidden_queries = [
            "INSERT INTO res_company (name) VALUES ('Test');",
            "UPDATE res_company SET name = 'Test' WHERE id = 1;",
            "DELETE FROM sale_order WHERE id = 1;",
            "DROP TABLE sale_order;",
            "ALTER TABLE sale_order ADD COLUMN test VARCHAR;",
            "TRUNCATE TABLE sale_order;",
            "EXECUTE some_procedure();",
            "CREATE TABLE test_table (id int);",
            "GRANT ALL ON sale_order TO public;",
        ]
        for q in forbidden_queries:
            with self.subTest(query=q):
                with self.assertRaises(ReadOnlyViolationError):
                    self.client.validate_read_only(q)

    def test_empty_query(self):
        with self.assertRaises(ValueError):
            self.client.validate_read_only("")


if __name__ == "__main__":
    unittest.main()
