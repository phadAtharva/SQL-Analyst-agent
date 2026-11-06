import os
import re
from contextlib import closing

import psycopg2
from dotenv import load_dotenv

load_dotenv()

MAX_ROWS = 100
SENSITIVE_COLUMN = re.compile(
    r"(?i)(email|phone|first_?name|last_?name|full_?name|address|"
    r"license_?plate|transaction_?id|password|secret|token|latitude|longitude)"
)
EMAIL = re.compile(r"(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b")
PHONE = re.compile(r"(?<!\w)\+?\d[\d ()-]{8,}\d(?!\w)")


class DatabaseError(RuntimeError):
    """A database operation failed without exposing connection details."""


def _validate_query(query: str) -> str:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("SQL query must not be empty.")
    query = query.strip()
    if len(query) > 20000:
        raise ValueError("SQL query is too long.")
    if ";" in query or "--" in query or "/*" in query or "*/" in query:
        raise ValueError("SQL comments and semicolons are not allowed.")
    if not re.match(r"(?is)^(select|with)\b", query):
        raise ValueError("Only SELECT queries are allowed.")
    return query


def _redact(value: object, column: str) -> object:
    if SENSITIVE_COLUMN.search(column):
        return "[REDACTED]"
    if isinstance(value, str):
        return PHONE.sub("[REDACTED]", EMAIL.sub("[REDACTED]", value))
    return value


class Database:
    def __init__(self):
        url = os.getenv("PG_DB_URL")
        if not url:
            raise DatabaseError("PG_DB_URL is not configured.")
        try:
            self.conn = psycopg2.connect(url, connect_timeout=10)
        except psycopg2.Error:
            raise DatabaseError("Could not connect to the database.") from None

    def schema_details(self, schema_name: str) -> str:
        if not isinstance(schema_name, str) or not schema_name.strip():
            self.conn.close()
            raise ValueError("Schema name must not be empty.")
        try:
            with closing(self.conn), self.conn, self.conn.cursor() as cursor:
                cursor.execute(
                    """SELECT table_name, column_name, data_type
                       FROM information_schema.columns
                       WHERE table_schema = %s
                       ORDER BY table_name, ordinal_position""",
                    (schema_name,),
                )
                rows = cursor.fetchall()
            lines = [f"Schema: {schema_name}"]
            previous = None
            for table, column, data_type in rows:
                if table != previous:
                    lines.append(f"Table: {table}")
                    previous = table
                lines.append(f"    Column name: {column}, DataType: {data_type}")
            return "\n".join(lines)
        except psycopg2.Error:
            raise DatabaseError("Could not retrieve database schema.") from None

    def execute_query(self, query: str) -> str:
        try:
            query = _validate_query(query)
        except ValueError:
            self.conn.close()
            raise
        try:
            with closing(self.conn), self.conn, self.conn.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("SET LOCAL statement_timeout = '10s'")
                # Wrapping in a subquery makes PostgreSQL reject multiple statements
                # and commands that cannot appear as a SELECT subquery.
                cursor.execute(
                    f"SELECT * FROM ({query}) AS analyst_result LIMIT {MAX_ROWS + 1}"
                )
                columns = [column.name for column in cursor.description]
                rows = cursor.fetchmany(MAX_ROWS + 1)
                truncated = len(rows) > MAX_ROWS
                sanitized = [
                    [_redact(value, name) for name, value in zip(columns, row)]
                    for row in rows[:MAX_ROWS]
                ]
                return str({"columns": columns, "rows": sanitized, "truncated": truncated})
        except psycopg2.Error:
            raise DatabaseError("Database query failed or was rejected.") from None
