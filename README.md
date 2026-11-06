# Data agent

The SQL analyst sends the question, database schema (without sample rows), and
query results to the configured Groq model. Common sensitive columns and
email/phone patterns in results are redacted on a best-effort basis. Redaction
cannot identify every sensitive value, including renamed columns; use a
dedicated database role and views that expose only data safe to share.

The SQL safety judge is an LLM, not a security boundary. Configure `PG_DB_URL`
with a PostgreSQL role restricted to read-only access to the intended data.
Queries are also run in a read-only transaction, with a 10-second statement
timeout and a maximum of 100 result rows. Queries must be a single SELECT or
WITH query without comments or semicolons. PostgreSQL functions may have
side effects even in read-only transactions; restrict function permissions.

Local `.env` files, editor settings, CSV data, and generated schema and graph
outputs are excluded from Git. Configure `PG_DB_URL` and `GROQ_API_KEY` locally.
To use `feed_db.py`, provide the required CSV files in a local `data` directory.
The loader does not clear existing rows by default. `uv run python feed_db.py
--replace` explicitly deletes the existing contents of the five tables before
loading; use this only when replacement is intended.

Run the local graph regression tests without Groq or database access:

```powershell
uv run python -m unittest discover -s tests -v
```