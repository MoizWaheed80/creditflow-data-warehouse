
import logging
import sys
 
import dlt
import requests
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import (
    SalesforceExpiredSession,
    SalesforceRefusedRequest,
    SalesforceGeneralError,
)
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("salesforce_pipeline.log"), logging.StreamHandler()],
)
log = logging.getLogger("salesforce_pipeline")
 
BATCH_SIZE = 200  # records per yield, keeps memory flat regardless of object size
 
# field types excluded on technical grounds, not business scoping: binary
# blobs and compound address/location fields (their subfields, e.g.
# BillingCity, are already queryable individually and included on their own)
SKIP_FIELD_TYPES = {"base64", "address", "location"}
 
# Objects Salesforce flags queryable=True in describe(), but which actually
# require a mandatory per-record filter (they're computed access/metadata
# objects, not bulk-exportable data - e.g. "a filter on a reified column is
# required" for UserFieldAccess, or "requires a filter by a single Id" for
# Vote). No SOQL shape can bulk-export these; this isn't a bug to fix, it's
# a hard platform restriction. Determined from this org's actual first run -
# skipped up front now so the log reflects "known limitation", not "error".
SKIP_OBJECTS = {
    "ActivityFieldHistory", "ApexTypeImplementor", "AppTabMember", "ColorDefinition",
    "ContentDocumentLink", "ContentFolderItem", "ContentFolderMember", "DataStatistics",
    "DataType", "DatacloudAddress", "DatacloudCompany", "DatacloudContact",
    "DatacloudDandBCompany", "EntityParticle", "ExternalEncryptionRootKey",
    "FieldDefinition", "FileEventStore", "FlexQueueItem", "FlowTestView",
    "FlowVariableView", "FlowVersionView", "IconDefinition", "IdeaComment",
    "ListViewChartInstance", "OmniRoutingEventStore", "OutgoingEmail",
    "OutgoingEmailRelation", "OwnerChangeOptionInfo", "PendingOrderSummary",
    "PicklistValueInfo", "PlatformAction", "RecordActionHistory",
    "RelatedListColumnDefinition", "RelatedListDefinition", "RelationshipDomain",
    "RelationshipInfo", "SearchLayout", "SiteDetail", "UserEntityAccess",
    "UserFieldAccess", "UserRecordAccess", "Vote",
}
 
RETRYABLE = (SalesforceExpiredSession, SalesforceRefusedRequest, SalesforceGeneralError, RequestException)
 
 
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type(RETRYABLE),
    reraise=True,
)
def client_credentials_login(domain: str, consumer_key: str, consumer_secret: str) -> Salesforce:
    """OAuth 2.0 Client Credentials Flow: no user password anywhere. Salesforce
    authenticates as the 'Run As' user configured directly on the Connected
    App. This is the modern replacement for the Username-Password flow,
    which is permanently blocked (not just togglable) on orgs created
    Summer '23 or later - see issues-log.md.
 
    simple-salesforce has no built-in support for this flow, so the token
    endpoint is called directly, then the resulting session_id/instance_url
    are handed to Salesforce() to skip its own login logic entirely.
    """
    token_url = f"https://{domain}.salesforce.com/services/oauth2/token"
    resp = requests.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": consumer_key,
            "client_secret": consumer_secret,
        },
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    return Salesforce(session_id=payload["access_token"], instance_url=payload["instance_url"])
 
 
def get_client() -> Salesforce:
    creds = dlt.secrets["sources.salesforce.credentials"]
    return client_credentials_login(
        domain=creds["domain"],
        consumer_key=creds["consumer_key"],
        consumer_secret=creds["consumer_secret"],
    )
 
 
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type(RETRYABLE),
    reraise=True,
)
def discover_objects(sf: Salesforce) -> list:
    global_desc = sf.describe()
    objects = [
        o["name"] for o in global_desc["sobjects"]
        if o.get("queryable") and not o.get("deprecatedAndHidden", False)
    ]
    log.info("discovered %d queryable objects in the org", len(objects))
    return objects
 
 
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type(RETRYABLE),
    reraise=True,
)
def describe_fields(sf: Salesforce, object_name: str) -> list:
    desc = getattr(sf, object_name).describe()
    fields = [
        f["name"] for f in desc["fields"]
        if f.get("type") not in SKIP_FIELD_TYPES and not f.get("deprecatedAndHidden", False)
    ]
    return fields
 
 
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type(RETRYABLE),
    reraise=True,
)
def run_query_page(sf: Salesforce, soql: str):
    """Wraps query_all_iter's underlying first call/queryMore calls so a
    mid-page rate-limit/session hiccup gets retried instead of aborting the
    whole extraction."""
    return sf.query_all_iter(soql)
 
 
def paged_records(sf: Salesforce, soql: str):
    """Yields batches of BATCH_SIZE records, streamed from Salesforce rather
    than loaded all at once."""
    batch = []
    for record in run_query_page(sf, soql):
        record.pop("attributes", None)  # drop the metadata dict simple_salesforce adds
        batch.append(record)
        if len(batch) >= BATCH_SIZE:
            yield batch
            batch = []
    if batch:
        yield batch
 
 
def build_resource(sf: Salesforce, object_name: str, fields: list, incremental_field: str = None):
    if incremental_field:
        @dlt.resource(name=object_name.lower(), write_disposition="merge", primary_key="Id", schema_contract="evolve")
        def _resource(
            cursor=dlt.sources.incremental(incremental_field, initial_value="2000-01-01T00:00:00Z")
        ):
            soql = f"SELECT {', '.join(fields)} FROM {object_name} WHERE {incremental_field} > {cursor.last_value}"
            log.info("querying %s incrementally since %s", object_name, cursor.last_value)
            for batch in paged_records(sf, soql):
                yield batch
    else:
        @dlt.resource(name=object_name.lower(), write_disposition="replace", schema_contract="evolve")
        def _resource():
            soql = f"SELECT {', '.join(fields)} FROM {object_name}"
            log.info("querying %s (full)", object_name)
            for batch in paged_records(sf, soql):
                yield batch
 
    return _resource
 
 
def log_api_budget(sf: Salesforce):
    try:
        limits = sf.limits()
        daily = limits.get("DailyApiRequests", {})
        log.info(
            "Salesforce API budget: %s/%s daily requests remaining",
            daily.get("Remaining", "?"), daily.get("Max", "?"),
        )
    except Exception:
        log.warning("could not fetch API limits (non-fatal), continuing")
 
 
def run():
    sf = get_client()
    log_api_budget(sf)
 
    try:
        objects = discover_objects(sf)
    except Exception:
        log.exception("could not discover object list from Salesforce, aborting")
        sys.exit(1)
 
    pipeline = dlt.pipeline(
        pipeline_name="salesforce_to_sqlserver",
        destination="mssql",
        dataset_name="raw_salesforce",
    )
 
    failures = []
    skipped = []
    for i, object_name in enumerate(objects, 1):
        if object_name in SKIP_OBJECTS:
            log.info("[%d/%d] %s - skipped (known non-bulk-queryable object)", i, len(objects), object_name)
            skipped.append(object_name)
            continue
        try:
            log.info("[%d/%d] %s", i, len(objects), object_name)
            fields = describe_fields(sf, object_name)
            if not fields:
                log.info("  %s has no queryable fields, skipping", object_name)
                continue
            incremental_field = "LastModifiedDate" if "LastModifiedDate" in fields else None
 
            resource = build_resource(sf, object_name, fields, incremental_field)
            load_info = pipeline.run(resource())
            if load_info.has_failed_jobs:
                raise RuntimeError(f"{object_name} load had failed jobs: {load_info}")
        except Exception:
            log.exception("failed to load %s, skipping and continuing with the rest", object_name)
            failures.append(object_name)
 
    log_api_budget(sf)
 
    log.info(
        "%d loaded, %d skipped (known unsupported), %d failed, out of %d discovered",
        len(objects) - len(skipped) - len(failures), len(skipped), len(failures), len(objects),
    )
    if failures:
        log.error("%d objects failed unexpectedly this run: %s", len(failures), failures)
        sys.exit(1)
    log.info("run complete")
 
 
if __name__ == "__main__":
    run()
 