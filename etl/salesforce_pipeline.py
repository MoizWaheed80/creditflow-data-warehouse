import logging
import sys

import dlt
import requests
from simple_salesforce import Salesforce

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("salesforce_pipeline.log"), logging.StreamHandler()]
)
log = logging.getLogger("salesforce_pipeline")

TARGET_DATASET = "bronze"
OBJECTS = ["Account", "Contact", "Opportunity"]

# compound/binary fields Salesforce can't return in a flat query -
# their subfields (e.g. BillingCity) are already included on their own
SKIP_FIELD_TYPES = {"base64", "address", "location"}


def get_client() -> Salesforce:
    creds = dlt.secrets["sources.salesforce.credentials"]
    token_url = f"https://{creds['domain']}.salesforce.com/services/oauth2/token"
    resp = requests.post(token_url, data={
        "grant_type": "client_credentials",
        "client_id": creds["consumer_key"],
        "client_secret": creds["consumer_secret"],
    })
    resp.raise_for_status()
    payload = resp.json()
    return Salesforce(session_id=payload["access_token"], instance_url=payload["instance_url"])


def get_fields(sf: Salesforce, object_name: str) -> list:
    desc = getattr(sf, object_name).describe()
    return [f["name"] for f in desc["fields"] if f.get("type") not in SKIP_FIELD_TYPES]


def build_resource(sf: Salesforce, object_name: str, fields: list):
    table_name = "salesforce_" + object_name.lower()

    @dlt.resource(name=table_name, write_disposition="replace", schema_contract="evolve")
    def _resource():
        soql = f"SELECT {', '.join(fields)} FROM {object_name}"
        for record in sf.query_all_iter(soql):
            record.pop("attributes", None)
            yield record

    return _resource


def run():
    sf = get_client()
    pipeline = dlt.pipeline(
        pipeline_name="salesforce_bronze",
        destination="mssql",
        dataset_name=TARGET_DATASET
    )

    for object_name in OBJECTS:
        try:
            fields = get_fields(sf, object_name)
            resource = build_resource(sf, object_name, fields)
            pipeline.run(resource())
            log.info("%s loaded", object_name)
        except Exception as e:
            log.warning("'%s' failed to load, skipping: %s", object_name, e)

    log.info("run finished")


if __name__ == "__main__":
    run()