# CreditFlow Data Warehouse — Problem Statement & Solution

## Problem Statement

CreditFlow's lending data is scattered across three disconnected systems — Salesforce (CRM) for the loan applicant pipeline, Odoo (ERP) for vendor payments and branch expenses, and manual Excel trackers for branches not yet migrated onto the CRM workflow. Leadership has no single, trusted view of branch performance or loan portfolio health, and building a combined picture means manually reconciling three sources by hand.

## Solution

Built a Python ingestion layer that lands all three sources into a SQL Server warehouse, deliberately covering two different ingestion patterns rather than one:

- **Excel → dlt → SQL Server** — file-based ingestion. Every sheet in the workbook is discovered dynamically (no hardcoded sheet list); each becomes its own raw table.
- **Salesforce → dlt → SQL Server** — API-based ingestion. Pulls via REST (simple-salesforce), with incremental extraction on Opportunity so re-runs only pull what changed, plus retry/backoff for rate limits and dynamic field discovery so schema changes on the Salesforce side don't break the pipeline.
- **Odoo → SQL Server, direct** — no framework. A Python script reads straight from Odoo's Postgres database (psycopg2) and writes straight to SQL Server (SQLAlchemy/pyodbc), full refresh per table.

Every pipeline has retry-with-backoff, per-unit failure isolation (one bad sheet/object/table doesn't kill the whole run), and logging — so it survives real-world conditions (OneDrive file locks, flaky connections, schema drift) rather than only working in the happy path.

SSIS was in the original plan for the Odoo and Excel legs but got dropped in favor of a single Python codebase — one language, one testable pipeline, and dlt's built-in schema-evolution handling instead of maintaining separate SSIS packages.

## Status

Excel ingestion is complete and confirmed working end-to-end. Salesforce and Odoo pipelines are built, not yet run against live sources. Next: Power BI reporting on top of the warehouse, with row-level security so a branch manager only sees their own branch's data.
