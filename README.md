# CreditFlow: Digital Lending Operations Warehouse

A data warehouse and BI platform consolidating loan pipeline (CRM), vendor operations (ERP), and manual branch reporting (Excel) for a fictional digital lending company. Built to demonstrate an end-to-end analytics engineering workflow: requirements, governance, ingestion, modeling, QA, and reporting.

## Problem statement
Digital lenders typically run on three disconnected systems of record: a CRM for the loan origination pipeline, an ERP for vendor and back-office operations, and years of manual Excel-based branch reporting that predates either system. None of these talk to each other, so nobody has a single, trustworthy view of loan book performance across origination channel, vendor, and branch history. Reporting is manual, slow to produce, inconsistent between branches, and impossible to secure at a granular level (e.g. a branch manager seeing only their own branch's numbers).

CreditFlow addresses this by building a governed, dimensional warehouse that unifies all three sources into one star schema, with a BI layer that's fast enough for daily use, secured with row-level security, and usable from both desktop and mobile.

## Status
🚧 In progress.

Done:
- SRS complete
- Self-hosted Odoo (ERP source) set up via Docker (Postgres 16 + Odoo 18)
- CRM source decided: Salesforce (Developer Edition, API-based ingestion) instead of HubSpot
- SQL Server destination configured (local SQLEXPRESS instance, TCP/IP enabled)
- Excel ingestion pipeline (`etl/excel_pipeline.py`) complete and confirmed working — all 9 legacy sheets loading successfully

In progress:
- Salesforce and Odoo ingestion pipelines
- Medallion layer builds (Bronze → Silver → Gold) and star schema modeling
- Fabric Mirroring / Power BI Direct Lake setup

## Architecture
```
Salesforce (CRM) ──dlt (API)────┐
Odoo (ERP)       ──dlt (DB)─────┼──> Staging ──> Bronze ──> Silver ──> Gold (star schema)
Excel (manual)   ──dlt (file)───┘                                        │
                                                                          ▼
                                            SQL Server ──Fabric Mirroring──> OneLake
                                                                          │
                                                                          ▼
                                           Power BI (Direct Lake) — desktop + mobile, RLS
```
SSIS handles scheduling/orchestration on top of the dlt pipelines rather than ingestion itself.

## Repo structure
- `docs/` — SRS, data dictionary, governance docs
- `infra/odoo/` — Docker setup for the self-hosted ERP source
- `source/odoo/` — Odoo/Postgres docker-compose stack and config
- `source/salesforce/` — Salesforce config and seed data scripts
- `source/Excel/` — legacy Excel export (9 sheets spanning 2018–2023 loan books + CRM/ERP snapshots)
- `etl/` — dlt pipelines (`excel_pipeline.py`, Salesforce, Odoo)
- `sql/` — warehouse DDL, medallion layer scripts, QA checks
- `powerbi/` — the .pbix report

## Tech stack
SQL Server, SSIS, dlt, Python, Power BI, Odoo (self-hosted), Salesforce API, Microsoft Fabric (Mirroring, OneLake), Docker.

## SDLC / methodology
- **Requirements-first**: build starts from a full SRS (`docs/SRS.md`) before any ingestion work, so scope and data dictionary are agreed up front.
- **Agile/Scrum**: work is broken into small, sequential milestones (source setup → one pipeline at a time → modeling → serving layer → reporting) rather than built end-to-end in one pass.
- **Git version control**: full history in the `creditflow-data-warehouse` GitHub repo, including working through real issues along the way (e.g. secrets accidentally committed and caught by GitHub push protection, fixed by untracking the files, rotating credentials, and correcting a misnamed `.gitignore`).
- **Data governance**: credentials and config are gitignored and rotated when exposed; the data dictionary and governance docs live in `docs/` alongside the SRS.
- **Ad hoc analysis**: validation queries and spot-checks run against each layer as it's built, not just at the end.
- **Documentation**: problems solved and decisions made (e.g. Docker virtualization fixes, Odoo master password issue, CRM source swap) are being written up as the project completes, so the repo doubles as a build log.

## Setup
See `docs/SRS.md` for full requirements.
