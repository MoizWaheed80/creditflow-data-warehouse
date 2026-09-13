"""
Ingestion method 2 of 3: API -> dlt -> SQL Server
Pulls CRM objects out of Salesforce over the REST API and lands them raw in
SQL Server (schema: raw_salesforce). Opportunity is loaded incrementally on
LastModifiedDate to demonstrate cursor-based extraction; Account/Contact are
small reference tables so they're loaded in full each run.

Auth uses the OAuth2 Consumer Key/Secret from your connected app plus a
username/password/security token (same combo seed_salesforce_data.py uses) -
adjust field names below if your org's schema differs from stock Salesforce.
"""

import dlt
from simple_salesforce import Salesforce


def get_client() -> Salesforce:
    creds = dlt.secrets["sources.salesforce.credentials"]
    return Salesforce(
        username=creds["username"],
        password=creds["password"],
        security_token=creds["security_token"],
        consumer_key=creds["consumer_key"],
        consumer_secret=creds["consumer_secret"],
        domain=creds.get("domain", "login"),  # use "test" for a sandbox org
    )


@dlt.resource(name="accounts", write_disposition="replace")
def accounts():
    sf = get_client()
    result = sf.query_all(
        "SELECT Id, Name, Industry, BillingCity, BillingCountry, "
        "CreatedDate, LastModifiedDate FROM Account"
    )
    yield result["records"]


@dlt.resource(name="contacts", write_disposition="replace")
def contacts():
    sf = get_client()
    result = sf.query_all(
        "SELECT Id, AccountId, FirstName, LastName, Email, Phone, "
        "CreatedDate, LastModifiedDate FROM Contact"
    )
    yield result["records"]


@dlt.resource(name="opportunities", write_disposition="merge", primary_key="Id")
def opportunities(
    last_modified=dlt.sources.incremental("LastModifiedDate", initial_value="2000-01-01T00:00:00Z")
):
    sf = get_client()
    soql = (
        "SELECT Id, AccountId, Name, StageName, Amount, CloseDate, "
        "CreatedDate, LastModifiedDate FROM Opportunity "
        f"WHERE LastModifiedDate > {last_modified.last_value}"
    )
    result = sf.query_all(soql)
    yield result["records"]


def run():
    pipeline = dlt.pipeline(
        pipeline_name="salesforce_to_sqlserver",
        destination="mssql",
        dataset_name="raw_salesforce",
    )
    load_info = pipeline.run([accounts(), contacts(), opportunities()])
    print(load_info)


if __name__ == "__main__":
    run()
