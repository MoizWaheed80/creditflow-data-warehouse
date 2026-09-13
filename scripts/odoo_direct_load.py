"""
Ingestion method 3 of 3: DIRECT DB-to-DB (no dlt)
Reads straight out of the Odoo Postgres database and writes straight into
SQL Server (schema: raw_odoo). No framework, no incremental state - just a
full truncate-and-reload per table, which is the point: this is the "direct
link" method, contrasted with the dlt-managed methods used for Excel and
Salesforce.

Update ODOO_TABLES below to match what's actually in your Odoo instance.
res_partner (customers) is standard Odoo. account_move (invoices) is used
here as a stand-in for loan transactions unless you've added a custom
lending module with its own model.
"""

from sqlalchemy import create_engine, text
import pandas as pd

# --- source: Odoo's Postgres DB (from your docker-compose.yml) ---
PG_HOST = "localhost"
PG_PORT = 5432        # match the port you mapped in docker-compose.yml
PG_DB = "odoo_creditflow"
PG_USER = "odoo"       # match the db service user in docker-compose.yml
PG_PASSWORD = "odoo"   # match the db service password

# --- destination: local SQL Server, Windows auth ---
MSSQL_SERVER = "localhost"
MSSQL_DB = "CreditFlow_Raw"
TARGET_SCHEMA = "raw_odoo"

# (source_table, target_table)
ODOO_TABLES = [
    ("res_partner", "res_partner"),
    ("account_move", "account_move"),
]


def get_pg_engine():
    url = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    return create_engine(url)


def get_mssql_engine():
    url = (
        f"mssql+pyodbc://@{MSSQL_SERVER}/{MSSQL_DB}"
        "?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&encrypt=no"
    )
    return create_engine(url)


def ensure_schema(engine, schema: str):
    with engine.begin() as conn:
        conn.execute(text(
            f"IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = '{schema}') "
            f"EXEC('CREATE SCHEMA {schema}')"
        ))


def run():
    pg_engine = get_pg_engine()
    mssql_engine = get_mssql_engine()
    ensure_schema(mssql_engine, TARGET_SCHEMA)

    for source_table, target_table in ODOO_TABLES:
        print(f"extracting {source_table} from Odoo...")
        df = pd.read_sql(f"SELECT * FROM {source_table}", pg_engine)
        print(f"loading {len(df)} rows into {TARGET_SCHEMA}.{target_table}...")
        df.to_sql(
            target_table,
            mssql_engine,
            schema=TARGET_SCHEMA,
            if_exists="replace",
            index=False,
        )
    print("done")


if __name__ == "__main__":
    run()
