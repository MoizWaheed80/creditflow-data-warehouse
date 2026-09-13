"""
Ingestion method 1 of 3: FILE -> dlt -> SQL Server

Fully dynamic, no manual transformation: every sheet in the workbook becomes
its own raw table in SQL Server (schema: raw_excel). Sheets aren't filtered
or hardcoded by name - whatever sheets exist in the file right now get
loaded, so adding/removing/renaming a sheet needs no code change here.

Column names and values are passed through exactly as pandas reads them -
nothing is renamed, retyped, or reshaped in this script. dlt's own naming
convention does automatically turn e.g. "Loan Book 2018-2019" into the table
name loan_book_2018_2019 and "Customer Name" into the column customer_name
when it writes to SQL Server - that's dlt normalizing identifiers so they're
valid SQL, not a transformation applied here.

Resilience:
- schema_contract="evolve" + write_disposition="replace" per sheet: a sheet
  gaining/losing a column, or the workbook gaining/losing a whole sheet,
  doesn't crash the run.
- retry on file/sheet reads: the source lives in OneDrive, which frequently
  throws PermissionError/OSError while a file is syncing or not yet fully
  downloaded locally.
- each sheet loads independently; if one sheet fails, the rest still load
  and the failure is logged and reported at the end.
"""

import logging
import sys

import dlt
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

EXCEL_PATH = r"C:\Users\thecl\OneDrive\Desktop\creditflow-data-warehouse\source\Excel\Legacy_data.xlsx"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("excel_pipeline.log"), logging.StreamHandler()],
)
log = logging.getLogger("excel_pipeline")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type((PermissionError, FileNotFoundError, OSError)),
    reraise=True,
)
def open_workbook() -> pd.ExcelFile:
    log.info("opening %s", EXCEL_PATH)
    return pd.ExcelFile(EXCEL_PATH)


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type((PermissionError, FileNotFoundError, OSError)),
    reraise=True,
)
def read_sheet(workbook: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    # no column renaming, no dtype changes, no added columns - raw pass-through
    return workbook.parse(sheet_name)


def build_resource(workbook: pd.ExcelFile, sheet_name: str):
    @dlt.resource(name=sheet_name, write_disposition="replace", schema_contract="evolve")
    def _resource():
        df = read_sheet(workbook, sheet_name)
        log.info("%s: %d rows, %d columns: %s", sheet_name, len(df), len(df.columns), list(df.columns))
        yield df.to_dict(orient="records")

    return _resource


def run():
    workbook = open_workbook()
    sheet_names = workbook.sheet_names
    log.info("found %d sheets: %s", len(sheet_names), sheet_names)

    pipeline = dlt.pipeline(
        pipeline_name="excel_to_sqlserver",
        destination="mssql",
        dataset_name="raw_excel",
    )

    failures = []
    for sheet_name in sheet_names:
        try:
            resource = build_resource(workbook, sheet_name)
            load_info = pipeline.run(resource())
            log.info("%s: %s", sheet_name, load_info)
            if load_info.has_failed_jobs:
                raise RuntimeError(f"{sheet_name} load had failed jobs: {load_info}")
        except Exception:
            log.exception("failed to load sheet '%s', skipping and continuing with the rest", sheet_name)
            failures.append(sheet_name)

    if failures:
        log.error("sheets that failed this run: %s", failures)
        sys.exit(1)
    log.info("all sheets loaded successfully")


if __name__ == "__main__":
    run()
