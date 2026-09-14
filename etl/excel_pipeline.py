import logging
import dlt
import pandas as pd

EXCEL_PATH = r"C:\Users\thecl\OneDrive\Desktop\creditflow-data-warehouse\source\Excel\Legacy_data.xlsx"
DESTINATION = "mssql"
DATASET = "bronze"

SHEETS = [
    "Loan Book 2018-2019",
    "Loan Book 2020-2021",
    "Loan Book 2022-2023",
    "SF_Accounts",
    "SF_Contacts",
    "SF_Opportunities",
    "Odoo_Customers",
    "Odoo_SalesOrders",
    "Odoo_Invoices"
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("excel_pipeline.log"), logging.StreamHandler()]
)
log = logging.getLogger("excel_pipeline")

def run():
    pipeline = dlt.pipeline(
        pipeline_name="excel_pipeline",
        destination=DESTINATION,
        dataset_name=DATASET
    )

    for sheet in SHEETS:
        table_name = "excel_" + sheet.lower().replace(" ", "_").replace("-", "_")
        try:
            df = pd.read_excel(EXCEL_PATH, sheet_name=sheet, dtype=str)
            load_info = pipeline.run(
                df,
                table_name=table_name,
                write_disposition="replace",
                schema_contract="evolve"
            )
            if load_info.has_failed_jobs:
                log.warning("'%s' had failed jobs: %s", table_name, load_info)
            else:
                log.info("%s: %d rows loaded", table_name, len(df))
        except Exception as e:
            log.warning("'%s' failed to load, skipping: %s", table_name, e)

if __name__ == "__main__":
    run()
    log.info("run finished")