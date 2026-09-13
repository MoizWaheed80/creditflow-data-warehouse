"""
Ingestion method 3 of 3: DIRECT DB-to-DB (no dlt)
Reads straight out of the Odoo Postgres database and writes straight into
SQL Server (schema: raw_odoo). No framework, no incremental state - full
truncate-and-reload per table. This is the "direct link" method, contrasted
with the dlt-managed methods used for Excel and Salesforce.

Fully dynamic, same philosophy as the Excel pipeline: the table list is not
hardcoded anywhere in this script. Every run queries Postgres for whatever
tables actually exist in the 'public' schema right now and loads all of
them. Add a table in Odoo, it shows up next run with no code change. Drop
one, it's just gone from the next run. No column renaming, no filtering,
no reshaping - SELECT * and load as-is.

Note: Odoo's public schema includes ~400-600 tables, most of them internal
Odoo system tables (ir_*, mail_*, translation/log tables, etc), not just
business data. This will be slower and noisier than the Excel run. Odoo
stores translated fields (name, comment, etc) as JSONB, which come back as
Python dicts - these are converted to JSON strings before insert since
SQL Server has no native way to receive a raw dict as a parameter (see
make_json_safe below). Any other genuinely incompatible table (huge binary
blobs, exotic types) still gets logged and skipped rather than stopping
the run.

Handles:
- Schema drift (tables): the table list itself is discovered fresh every
  run from information_schema, not hardcoded.
- Schema drift (columns): "SELECT *" plus a table rebuild (first chunk
  replaces the target table) means whatever columns exist in a table right
  now are exactly what lands in SQL Server.
- Crashes: each table is extracted/loaded independently. If one table fails
  it's logged and the script moves on to the rest instead of dying. Exits
  non-zero at the end if anything failed, so a scheduler can flag it.
- Memory: every table is streamed in chunks via pandas' chunksize, so large
  tables don't need to fit in RAM all at once.
- Transient connection errors are retried with backoff before a table (or
  the initial table-list query) is given up on.
"""

import logging
import sys
import json

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, DBAPIError
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- source: Odoo's Postgres DB (from your docker-compose.yml) ---
PG_HOST = "localhost"
PG_PORT = 5432        # match the port you mapped in docker-compose.yml
PG_DB = "odoo_creditflow"
PG_USER = "odoo"       # match the db service user in docker-compose.yml
PG_PASSWORD = "odoo"   # match the db service password
PG_SCHEMA = "public"

# --- destination: local SQL Server, named instance, Windows auth ---
MSSQL_SERVER = r"localhost\SQLEXPRESS"
MSSQL_DB = "creditflow-data-warehouse"
TARGET_SCHEMA = "raw_odoo"

CHUNK_SIZE = 5000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("odoo_direct_load.log"), logging.StreamHandler()],
)
log = logging.getLogger("odoo_direct_load")

RETRYABLE = (OperationalError, DBAPIError, ConnectionError)


def _json_safe(value):
    # Odoo stores translated fields (name, comment, etc) as JSONB, which
    # psycopg2/pandas reads back as Python dict/list objects. pyodbc has no
    # native way to bind a dict as a SQL parameter, so it errors. This is a
    # type-compatibility fix, not a data transformation: the dict becomes
    # its exact JSON string equivalent, same information, just something
    # SQL Server (no native JSON type) can actually receive.
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value


def make_json_safe(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(_json_safe)
    return df


def get_pg_engine():
    url = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    return create_engine(url, pool_pre_ping=True)


def get_mssql_engine():
    url = (
        f"mssql+pyodbc://@{MSSQL_SERVER}/{MSSQL_DB}"
        "?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&encrypt=no"
    )
    return create_engine(url, pool_pre_ping=True)


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(RETRYABLE),
    reraise=True,
)
def discover_tables(pg_engine) -> list:
    query = text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = :schema AND table_type = 'BASE TABLE' "
        "ORDER BY table_name"
    )
    with pg_engine.connect() as conn:
        rows = conn.execute(query, {"schema": PG_SCHEMA}).fetchall()
    tables = [r[0] for r in rows]
    log.info("discovered %d tables in Postgres schema '%s'", len(tables), PG_SCHEMA)
    return tables


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(RETRYABLE),
    reraise=True,
)
def ensure_schema(engine, schema: str):
    with engine.begin() as conn:
        conn.execute(text(
            f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = '{schema}') "
            f"EXEC('CREATE SCHEMA {schema}')"
        ))


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(RETRYABLE),
    reraise=True,
)
def load_table(pg_engine, mssql_engine, table_name: str):
    log.info("extracting %s from Odoo (chunked, %d rows/chunk)...", table_name, CHUNK_SIZE)
    total_rows = 0
    first_chunk = True
    for chunk in pd.read_sql(f'SELECT * FROM "{table_name}"', pg_engine, chunksize=CHUNK_SIZE):
        chunk = make_json_safe(chunk)
        chunk.to_sql(
            table_name,
            mssql_engine,
            schema=TARGET_SCHEMA,
            if_exists="replace" if first_chunk else "append",
            index=False,
        )
        first_chunk = False
        total_rows += len(chunk)
    if first_chunk:
        # source table was empty - still (re)create an empty target table
        empty = pd.read_sql(f'SELECT * FROM "{table_name}" LIMIT 0', pg_engine)
        empty = make_json_safe(empty)
        empty.to_sql(table_name, mssql_engine, schema=TARGET_SCHEMA, if_exists="replace", index=False)
        log.info("  %s was empty, wrote empty %s.%s", table_name, TARGET_SCHEMA, table_name)
    log.info("done: %s -> %s.%s (%d rows)", table_name, TARGET_SCHEMA, table_name, total_rows)


def run():
    pg_engine = get_pg_engine()
    mssql_engine = get_mssql_engine()

    try:
        ensure_schema(mssql_engine, TARGET_SCHEMA)
    except Exception:
        log.exception("could not ensure target schema exists, aborting")
        sys.exit(1)

    try:
        tables = discover_tables(pg_engine)
    except Exception:
        log.exception("could not discover table list from Postgres, aborting")
        sys.exit(1)

    failures = []
    for i, table_name in enumerate(tables, 1):
        try:
            log.info("[%d/%d] %s", i, len(tables), table_name)
            load_table(pg_engine, mssql_engine, table_name)
        except Exception:
            log.exception("failed to load %s, skipping and continuing with the rest", table_name)
            failures.append(table_name)

    if failures:
        log.error("%d of %d tables failed this run: %s", len(failures), len(tables), failures)
        sys.exit(1)
    log.info("all %d tables loaded successfully", len(tables))


if __name__ == "__main__":
    run()