# CreditFlow Data Warehouse — Problem Statement & Solution

## Problem Statement

CreditFlow's lending data is scattered across three disconnected systems — Salesforce (CRM) for the loan applicant pipeline, Odoo (ERP) for vendor payments and branch expenses, and manual Excel trackers for branches not yet migrated onto the CRM workflow. Leadership has no single, trusted view of branch performance or loan portfolio health, and building a combined picture means manually reconciling three sources by hand.

## Solution

Built a Python ingestion layer that lands all three sources into a SQL Server warehouse, deliberately covering two different ingestion patterns rather than one:

- **Excel → dlt → SQL Server** — file-based ingestion. Every sheet in the workbook is discovered dynamically (no hardcoded sheet list); each becomes its own raw table.
- **Salesforce → dlt → SQL Server** — API-based ingestion. Every queryable object in the org is discovered dynamically via `describe()` (no hardcoded object list), with per-object field discovery and incremental extraction wherever a `LastModifiedDate` field exists (full replace otherwise). Authenticates via OAuth 2.0 Client Credentials Flow, since this org has both SOAP login and the username-password OAuth flow disabled. Retry/backoff on rate limits and session errors, per-object failure isolation, and an explicit skip-list for the small set of Salesforce metadata objects that can never be bulk-queried by any tool (they require a mandatory per-record filter by platform design).
- **Odoo → SQL Server, direct** — no framework. A Python script discovers every table in Odoo's Postgres database dynamically via `information_schema` (no hardcoded table list, covering ~360 tables), reads via psycopg2 in chunks, and writes to SQL Server via SQLAlchemy/pyodbc, full refresh per table. Converts Odoo's JSONB translated-field columns to JSON strings so they can bind through pyodbc.

Every pipeline has retry-with-backoff, per-unit failure isolation (one bad sheet/object/table doesn't kill the whole run), and logging — so it survives real-world conditions (OneDrive file locks, flaky connections, schema drift, platform-level query restrictions) rather than only working in the happy path.

SSIS was in the original plan for the Odoo and Excel legs but got dropped in favor of a single Python codebase — one language, one testable pipeline, and dlt's built-in schema-evolution handling instead of maintaining separate SSIS packages.

## Status

All three ingestion pipelines are complete and verified working end-to-end against live sources:

- **Excel:** all 10 sheets loaded successfully.
- **Odoo:** 363/363 tables loaded successfully.
- **Salesforce:** 1084/1126 objects loaded; the remaining 42 are Salesforce metadata/access-computation objects with no bulk-query path (documented platform limitation, not a pipeline defect) and are cleanly logged as skipped rather than failed.

Next: Silver/Gold layer transformations, Power BI reporting on top of the warehouse, row-level security so a branch manager only sees their own branch's data, and orchestration/scheduling for recurring runs.
