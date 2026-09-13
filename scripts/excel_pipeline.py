"""
Ingestion method 1 of 3: FILE -> dlt -> SQL Server
Reads the legacy Excel ledger and lands it raw in SQL Server (schema: raw_excel).
Full snapshot load each run (write_disposition="replace") since a flat file has no
reliable "changed since" marker on its own.
"""

import dlt
import pandas as pd

EXCEL_PATH = "CRM_ERP_Legacy_Practice_Data.xlsx"  # update to the real file path
SHEET_NAME = "Legacy_Excel_RAW"


@dlt.resource(name="legacy_excel_raw", write_disposition="replace")
def legacy_excel_raw():
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    # normalize headers so SQL Server gets clean column names, not "Customer Name"
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    yield df.to_dict(orient="records")


def run():
    pipeline = dlt.pipeline(
        pipeline_name="excel_to_sqlserver",
        destination="mssql",
        dataset_name="raw_excel",
    )
    load_info = pipeline.run(legacy_excel_raw())
    print(load_info)


if __name__ == "__main__":
    run()
