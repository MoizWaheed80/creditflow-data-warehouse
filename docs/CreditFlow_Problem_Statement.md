# CreditFlow Data Warehouse — Problem Statement & Solution

## Problem Statement

CreditFlow's lending data is scattered across three disconnected systems — Salesforce (CRM) for the loan applicant pipeline, Odoo (ERP) for vendor payments and branch expenses, and manual Excel trackers for branches not yet migrated onto the CRM workflow. Leadership has no single, trusted view of branch performance or loan portfolio health, and building a combined picture means manually reconciling three sources by hand.

## Solution

Built a Python ingestion layer that lands all three sources into a single SQL Server `bronze` schema (source-prefixed tables: `excel_*`, `odoo_*`, `salesforce_*`), deliberately covering two different ingestion patterns rather than one:

- **Excel → dlt → SQL Server** — file-based ingestion. Every sheet in the workbook is loaded as its own raw table: three years of legacy loan-book ledgers (2018–2023) plus the original staging sheets used to seed Salesforce and Odoo.
- **Salesforce → dlt → SQL Server** — API-based ingestion of Account, Contact, and Opportunity. Authenticates via OAuth 2.0 Client Credentials Flow, since this org has both SOAP login and the username-password OAuth flow disabled. Retry/backoff on rate limits and session errors, per-object failure isolation.
- **Odoo → SQL Server, direct** — no framework. A Python script reads `res_partner`, `account_move`, `account_move_line`, and `account_account` directly from Odoo's Postgres database via psycopg2, writes to SQL Server via SQLAlchemy/pyodbc, full refresh per table. Converts Odoo's JSONB translated-field columns to JSON strings so they can bind through pyodbc.

An earlier version of the Odoo and Salesforce legs discovered and pulled entire schemas dynamically with no scoping (800+ Odoo tables, hundreds of Salesforce objects). This was deliberately narrowed down to only the tables/objects actually seeded with data, keeping the warehouse focused rather than carrying hundreds of empty tables.

Every pipeline has retry-with-backoff, per-unit failure isolation (one bad sheet/object/table doesn't kill the whole run), and logging — so it survives real-world conditions (OneDrive file locks, flaky connections, schema drift) rather than only working in the happy path.

**Orchestration:** All three scripts are now orchestrated by an SSIS package (`CreditFlow_Load`) deployed to a SQL Server Agent job that runs daily at 2 AM, with each load logged to a `bronze.etl_run_log` table. The job runs the scripts under a dedicated local service account (`svc_ssis`), so the schedule doesn't depend on anyone being signed in.

## Status

All three ingestion pipelines and the daily orchestration are complete and verified working end-to-end against live sources:

- **Excel:** all 9 sheets loaded successfully.
- **Odoo:** all 4 seeded tables loaded successfully (`res_partner`, `account_move`, `account_move_line`, `account_account`).
- **Salesforce:** Account, Contact, and Opportunity loaded successfully via OAuth 2.0 Client Credentials Flow.
- **Orchestration:** SQL Server Agent job runs the SSIS package daily; 16+ consecutive successful runs logged in `bronze.etl_run_log` with zero manual intervention.

Next: Silver/Gold layer transformations, Power BI reporting on top of the warehouse, row-level security so a branch manager only sees their own branch's data.
