import ast
import unittest
from unittest.mock import MagicMock, patch

import psycopg2

from utils.database import Database, DatabaseError, _validate_query


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.cursor = self.conn.cursor.return_value.__enter__.return_value
        self.env = patch.dict("os.environ", {"PG_DB_URL": "postgresql://test"})
        self.connect = patch("utils.database.psycopg2.connect", return_value=self.conn)
        self.env.start()
        self.connect.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.connect.stop)

    def test_schema_is_parameterized_and_contains_no_sample_rows(self):
        self.cursor.fetchall.return_value = [("users", "email", "text")]
        schema = Database().schema_details("public' OR true --")
        query, parameters = self.cursor.execute.call_args.args
        self.assertIn("table_schema = %s", query)
        self.assertEqual(parameters, ("public' OR true --",))
        self.assertIn("Column name: email", schema)
        self.assertNotIn("Sample Data", schema)
        self.conn.close.assert_called_once()

    def test_query_is_bounded_read_only_and_redacted(self):
        self.cursor.description = [
            type("Column", (), {"name": name})()
            for name in ("email", "note", "count")
        ]
        self.cursor.fetchmany.return_value = [
            ("person@example.com", "call +1 234 567 8901", 3)
        ]
        result = ast.literal_eval(Database().execute_query("SELECT email, note, count FROM users"))
        self.assertEqual(result["rows"], [["[REDACTED]", "call [REDACTED]", 3]])
        self.assertFalse(result["truncated"])
        calls = self.cursor.execute.call_args_list
        self.assertEqual(calls[0].args[0], "SET TRANSACTION READ ONLY")
        self.assertIn("statement_timeout", calls[1].args[0])
        self.assertIn("LIMIT 101", calls[2].args[0])
        self.conn.close.assert_called_once()

    def test_result_limit_and_duplicate_columns(self):
        self.cursor.description = [type("Column", (), {"name": "count"})()] * 2
        self.cursor.fetchmany.return_value = [(1, 2)] * 101
        result = ast.literal_eval(Database().execute_query("SELECT 1, 2"))
        self.assertEqual(len(result["rows"]), 100)
        self.assertEqual(result["rows"][0], [1, 2])
        self.assertTrue(result["truncated"])

    def test_rejects_bad_statements_and_closes_connection(self):
        for query in ("", "DELETE FROM users", "SELECT 1; DROP TABLE users",
                      "SELECT 1 -- comment", "SELECT 1 /* comment */"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                Database().execute_query(query)
        self.assertEqual(self.conn.close.call_count, 5)
        self.cursor.execute.assert_not_called()

    def test_query_failure_is_reported_without_server_error_details(self):
        self.cursor.execute.side_effect = psycopg2.OperationalError("sensitive details")
        with self.assertRaisesRegex(DatabaseError, "Database query failed") as error:
            Database().execute_query("SELECT 1")
        self.assertNotIn("sensitive details", str(error.exception))
        self.conn.close.assert_called_once()

    def test_missing_connection_url(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaisesRegex(
            DatabaseError, "PG_DB_URL"
        ):
            Database()

    def test_allows_select_and_with(self):
        self.assertEqual(_validate_query(" SELECT 1 "), "SELECT 1")
        self.assertEqual(_validate_query("WITH t AS (SELECT 1) SELECT * FROM t"),
                         "WITH t AS (SELECT 1) SELECT * FROM t")


if __name__ == "__main__":
    unittest.main()
