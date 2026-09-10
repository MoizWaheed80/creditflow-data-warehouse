# CreditFlow: Digital Lending Operations Warehouse

A data warehouse and BI platform consolidating loan pipeline (CRM), vendor operations (ERP), and manual branch reporting (Excel) for a fictional digital lending company. Built to demonstrate an end-to-end analytics engineering workflow: requirements, governance, ingestion, modeling, QA, and reporting.

## Status
🚧 In progress. Currently: SRS complete, self-hosted Odoo (ERP source) set up via Docker.

## Architecture
```
HubSpot (CRM)  ──dlt──┐
Odoo (ERP)     ──SSIS─┼──> Staging ──> Bronze ──> Silver ──> Gold (star schema) ──> Power BI (+ mobile layout, RLS)
Excel (manual) ──SSIS─┘
```

## Repo structure
- `docs/` — SRS, data dictionary, governance docs
- `infra/odoo/` — Docker setup for the self-hosted ERP source
- `etl/` — dlt pipelines and SSIS package exports
- `sql/` — warehouse DDL, medallion layer scripts, QA checks
- `powerbi/` — the .pbix report

## Tech stack
SQL Server, SSIS, dlt, Python, Power BI, Odoo (self-hosted), HubSpot API, Docker.

## Setup
See `docs/SRS.md` for full requirements. Odoo setup instructions in `infra/odoo/`.

