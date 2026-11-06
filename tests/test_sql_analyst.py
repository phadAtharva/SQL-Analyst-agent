import importlib
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from Models.schema import JudgeSchema


database_module = types.ModuleType("utils.database")
database_module.Database = Mock()
with patch.dict(sys.modules, {"utils.database": database_module}):
    sql_analyst = importlib.import_module("agents.sql_analyst")


class SqlAnalystTests(unittest.TestCase):
    def run_graph(self, decision):
        database = Mock()
        database.schema_details.return_value = "Table: payments\nColumn: payment_method"
        database.execute_query.return_value = "[('credit_card',)]"

        low_llm = Mock()
        low_llm.invoke.side_effect = [
            SimpleNamespace(content="What payment methods are available?"),
            SimpleNamespace(content="Credit card is available."),
        ]
        judge = Mock()
        judge.invoke.return_value = JudgeSchema(is_safe=decision, comments="Test decision")
        medium_llm = Mock()
        medium_llm.invoke.return_value = SimpleNamespace(
            content="SELECT DISTINCT payment_method FROM payments LIMIT 10"
        )
        medium_llm.with_structured_output.return_value = judge

        input_schema = {
            "messages": [],
            "user_question": "What payment methods are available?",
            "curated_ques": "",
            "prompt_query_context": "",
            "generated_sql_query": "",
            "is_safe": "No",
            "comments": "",
            "sql_query_execution_result": "",
            "final_answer": "",
        }
        with patch.object(sql_analyst, "Database", return_value=database), patch.object(
            sql_analyst, "pick_llm",
            side_effect=lambda level: low_llm if level == "low" else medium_llm,
        ):
            result = sql_analyst.sql_analyst.invoke(input_schema)

        database.schema_details.assert_called_once_with("public")
        generator_prompt = medium_llm.invoke.call_args.args[0]
        self.assertIn("What payment methods are available?", generator_prompt)
        self.assertIn("Table: payments", generator_prompt)
        medium_llm.with_structured_output.assert_called_once_with(
            JudgeSchema, method="json_schema"
        )
        self.assertIn("SELECT DISTINCT payment_method", judge.invoke.call_args.args[0])
        self.assertEqual(result["is_safe"], decision)
        self.assertEqual(result["comments"], "Test decision")
        return database, result

    def test_approved_query_is_executed(self):
        database, result = self.run_graph("Yes")
        database.execute_query.assert_called_once_with(
            "SELECT DISTINCT payment_method FROM payments LIMIT 10"
        )
        self.assertEqual(result["final_answer"], "Credit card is available.")

    def test_rejected_query_is_not_executed(self):
        database, result = self.run_graph("No")
        database.execute_query.assert_not_called()
        self.assertIn("Query canceled", result["final_answer"])


if __name__ == "__main__":
    unittest.main()
