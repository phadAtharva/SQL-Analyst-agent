# Data agent

The SQL analyst sends the question, database schema, and sample table rows to
the configured Groq model. Review the data before using it with an external
model provider.

The SQL safety judge is an LLM, not a security boundary. Configure `PG_DB_URL`
with a PostgreSQL role restricted to read-only access to the intended data.

Local `.env` files, editor settings, CSV data, and generated schema and graph
outputs are excluded from Git. Configure `PG_DB_URL` and `GROQ_API_KEY` locally.
To use `feed_db.py`, provide the required CSV files in a local `data` directory.

Run the local graph regression tests without Groq or database access:

```powershell
uv run python -m unittest discover -s tests -p test_sql_analyst.py -v
```