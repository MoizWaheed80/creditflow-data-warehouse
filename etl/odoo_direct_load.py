import logging
import sys
import json

from sqlalchemy import create_engine, text
import pandas as pd

# --- source: Odoo's Postgres DB ---
PG_URL = "postgresql+psycopg2://odoo:odoo@localhost:5432/odoo_creditflow"

# --- destination: local SQL Server ---
MSSQL_URL = (
    r"mssql+pyodbc://@localhost\SQLEXPRESS/creditflow-data-warehouse"
    "?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&encrypt=no"
)
TARGET_SCHEMA = "bronze"

TABLES = [
    "res_partner",
    "account_move",
    "account_move_line",
    "account_account",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("odoo_direct_load.log"), logging.StreamHandler()]
)
log = logging.getLogger("odoo_direct_load")


def json_safe(df: pd.DataFrame) -> pd.DataFrame:
    # Odoo stores translated fields as JSONB -> comes back as dict/list.
    # SQL Server has no way to receive that, so convert to a JSON string.
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(lambda v: json.dumps(v, default=str) if isinstance(v, (dict, list)) else v)
    return df


def load_table(pg_engine, mssql_engine, table_name: str):
    df = pd.read_sql(f'SELECT * FROM "{table_name}"', pg_engine)
    df = json_safe(df)
    target_name = "odoo_" + table_name
    df.to_sql(target_name, mssql_engine, schema=TARGET_SCHEMA, if_exists="replace", index=False)
    log.info("%s: %d rows loaded", target_name, len(df))


def run():
    pg_engine = create_engine(PG_URL)
    mssql_engine = create_engine(MSSQL_URL)

    with mssql_engine.begin() as conn:
        conn.execute(text(
            f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = '{TARGET_SCHEMA}') "
            f"EXEC('CREATE SCHEMA {TARGET_SCHEMA}')"
        ))

    for table_name in TABLES:
        try:
            load_table(pg_engine, mssql_engine, table_name)
        except Exception as e:
            log.warning("'%s' failed to load, skipping: %s", table_name, e)

    log.info("run finished")


if __name__ == "__main__":
    run()