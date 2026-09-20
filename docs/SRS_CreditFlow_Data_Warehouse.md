# Software Requirements Specification
## CreditFlow Digital Lending Operations Warehouse

**Version:** 4.0
**Author:** Abdul Moiz Waheed
**Status:** Draft — Revision 4 (all three ingestion pipelines + daily orchestration complete and verified)

---

## Revision Notes

### v3 → v4
Two changes since v3:

1. **Ingestion scope narrowed to what's actually seeded.** The v3 build discovered and pulled entire schemas dynamically (363/363 Odoo tables, 1084/1126 Salesforce objects). This was deliberately scoped down: Salesforce now loads only Account, Contact, and Opportunity; Odoo now loads only `res_partner`, `account_move`, `account_move_line`, and `account_account`. Excel is unchanged (all 9 sheets). All three land in a single consolidated `bronze` schema with source-prefixed table names (`excel_*`, `odoo_*`, `salesforce_*`), replacing the earlier separate raw schemas. The 42-skipped-Salesforce-objects limitation documented in v3 no longer applies at this scope, since full-org discovery is no longer attempted.
2. **Orchestration/scheduling is now implemented.** An SSIS package (`CreditFlow_Load`) wraps all three Python scripts as Execute Process Tasks, deployed to the SSISDB catalog and run daily at 2 AM via a SQL Server Agent job, under a dedicated local service account (`svc_ssis`) rather than a personal login. Each load logs to a `bronze.etl_run_log` table. This required a second SQL Server instance (a default-instance SQL Server 2025 Developer Edition install) purely to host the SSISDB catalog and Agent, since SQL Server Express — which hosts the actual warehouse data — supports neither. See the issues log for the full permissions/DNS troubleshooting path.

Section 2.4, Section 3, Functional Requirements, and Section 8 below are updated accordingly.

### v2 → v3
All three ingestion pipelines are now built, run against live sources, and verified:
- **Excel:** all 10 sheets loaded.
- **Odoo:** 363/363 tables loaded (was previously "built, not yet run").
- **Salesforce:** 1084/1126 objects loaded; scope also widened from the originally planned Accounts/Contacts/Opportunities to a fully dynamic discovery of every queryable object in the org via `describe()`. Authentication required a full rewrite to OAuth 2.0 Client Credentials Flow, since this org has both SOAP login and the standard OAuth username-password flow disabled. The 42 unreached objects are Salesforce metadata/access-computation objects that no tool can bulk-query (mandatory per-record filter by platform design) — documented and explicitly skipped rather than treated as failures.
- The Odoo leg's scope also widened from the originally planned `res_partner`/`account_move` to a fully dynamic discovery of every table in the Postgres database (~360 tables), not a hardcoded list.
- Section 3 and Functional Requirements statuses below updated accordingly. Silver/Gold layers, Power BI, RLS, and orchestration remain not started.

*(Note, per v3→v4 above: the full-dynamic-discovery scope described in this note was subsequently narrowed back down to only the seeded tables/objects.)*

### v1 → v2
Three things changed between planning and build, and this revision reflects reality rather than the original plan:

1. **CRM source is Salesforce, not HubSpot.** The project moved to Salesforce Developer Edition early in implementation. All CRM references below are updated accordingly.
2. **SSIS was dropped in favor of direct Python ingestion.** Both the Odoo and Excel sources were originally planned to go through SSIS. In practice, everything was built in Python instead: dlt for Excel and Salesforce, and a direct psycopg2/SQLAlchemy script for Odoo (bypassing the Odoo API layer and reading its Postgres database directly). This keeps the whole ingestion layer in one language, makes schema-drift handling and testing easier, and was a deliberate choice to practice both an API-based ingestion pattern (Salesforce) and a direct DB-to-DB pattern (Odoo) side by side. *(Note, per v3→v4 above: SSIS was later reintroduced, but purely as an orchestration/scheduling layer wrapping these same Python scripts — the ingestion logic itself is still 100% Python.)*
3. **The Excel source is one workbook with a broader role than originally scoped.** It's not just a manual branch tracker — it's a single workbook (`Legacy_Excel.xlsx`) containing both the true legacy loan-book ledgers *and* the staging data used to seed the Salesforce and Odoo instances. Section 3 reflects the real sheet structure.

---

## 1. Introduction

### 1.1 Purpose
This document specifies the requirements for a data warehouse and reporting platform that consolidates lending operations data for CreditFlow, a fictional digital consumer lending company, so that branch performance, loan portfolio health, and vendor payables can be monitored from a single trusted source.

### 1.2 Scope
The system will ingest data from CreditFlow's CRM (loan applicant pipeline), ERP (internal vendor payments and expenses), and manual branch-level Excel trackers, consolidate it into a governed SQL Server warehouse, and expose it through Power BI reports for desktop and mobile.

Out of scope: loan origination decisioning, core banking transaction processing, and any real customer or financial data. All data used in this project is synthetic.

### 1.3 Intended Audience
Branch operations managers, loan portfolio analysts, a compliance/governance reviewer, and executive leadership (report consumers). Data engineering and BI development (build team, one person).

### 1.4 Definitions and Acronyms
| Term | Meaning |
|---|---|
| ERP | Enterprise Resource Planning (Odoo, internal ops) |
| CRM | Customer Relationship Management (Salesforce, loan pipeline) |
| ETL/ELT | Extract-Transform-Load / Extract-Load-Transform |
| SSIS | SQL Server Integration Services — used for daily orchestration/scheduling of the three Python ingestion scripts (see Revision Notes, v3→v4); the ingestion logic itself remains Python, not SSIS Data Flow |
| RLS | Row-Level Security |
| PII | Personally Identifiable Information |
| KYC | Know Your Customer (identity/verification fields) |
| OAuth CC Flow | OAuth 2.0 Client Credentials Flow — the auth method used for the Salesforce connection (see Revision Notes, v2→v3) |
| Medallion Architecture | Bronze (raw) / Silver (conformed) / Gold (business marts) layering |

---

## 2. Overall Description

### 2.1 Business Context
CreditFlow operates through regional branches. Loan officers track applicants in Salesforce. Branch admins log vendor invoices and expenses in Odoo. Some branches still record manual loan approval steps in Excel because they haven't been migrated onto the CRM workflow yet. Leadership currently has no single view across these three sources.

### 2.2 Product Perspective
A new, standalone analytics platform. It reads from source systems on a schedule; it does not write back to them.

### 2.3 User Classes and Characteristics
- **Branch Manager** — needs branch-scoped performance metrics only (RLS-restricted).
- **Loan Operations Analyst** — needs cross-branch visibility into pipeline and disbursal metrics.
- **Compliance Reviewer** — needs an auditable data dictionary and PII handling record, not raw report access.
- **Executive** — needs summary KPIs, mobile-friendly.

### 2.4 Operating Environment
- SQL Server Express (local instance, named instance `SQLEXPRESS`) as the warehouse — database `creditflow-data-warehouse`, Windows Authentication
- Python scripts for all ingestion: dlt for Excel and Salesforce, a direct psycopg2/SQLAlchemy script for Odoo
- Orchestration/scheduling implemented via an SSIS package (`CreditFlow_Load`) deployed to the SSISDB catalog and run daily (2 AM) by a SQL Server Agent job, under a dedicated local service account (`svc_ssis`). This requires a second, separate SQL Server instance (default-instance SQL Server 2025 Developer Edition) purely to host the SSISDB catalog and Agent, since SQL Server Express supports neither — the warehouse data itself stays on the original SQLEXPRESS instance.
- Power BI Desktop + Power BI Service for publishing
- Self-hosted Odoo Community Edition (Docker) as the ERP source
- Salesforce Developer Edition (free tier) as the CRM source

### 2.5 Assumptions and Dependencies
- All source data is synthetic/seeded, not real customer data.
- Odoo is ingested via a direct PostgreSQL connection to its underlying database, bypassing the Odoo API layer entirely. This is only feasible because the instance is self-hosted with direct DB access — a hosted/managed Odoo instance would not allow this and would require the API instead.
- This org's Salesforce security settings (SOAP login disabled, OAuth username-password flow disabled) meant the standard simple-salesforce auth path did not work; OAuth 2.0 Client Credentials Flow was required instead (see Revision Notes, v2→v3, and the issues log for the full troubleshooting path).
- Scheduled runs execute under a dedicated Windows service account (`svc_ssis`) rather than a personal login, so the schedule does not depend on any specific person being signed in.

---

## 3. Data Sources

| Source | System | Data Extracted | Ingestion Method | Frequency |
|---|---|---|---|---|
| Loan pipeline | Salesforce (CRM) | Account, Contact, Opportunity (scoped to the objects actually seeded, not a full-org discovery) | dlt (REST API via simple-salesforce), OAuth 2.0 Client Credentials Flow auth | Daily, 2 AM — SQL Server Agent job running the SSIS package |
| Vendor operations | Odoo (ERP, self-hosted Postgres) | `res_partner`, `account_move`, `account_move_line`, `account_account` (scoped to the tables actually seeded) | Direct DB-to-DB: Python reads Postgres via psycopg2 in chunks and writes to SQL Server via SQLAlchemy/pyodbc | Daily, 2 AM — SQL Server Agent job running the SSIS package |
| Legacy ledger + CRM/ERP seed data | Excel — single workbook (`Legacy_Excel.xlsx`) | All 9 sheets: `Loan Book <year range>` (true legacy ledger, one sheet per period, 2018–2023) plus staging sheets originally used to seed Salesforce (`SF_Accounts`, `SF_Contacts`, `SF_Opportunities`) and Odoo (`Odoo_Customers`, `Odoo_SalesOrders`, `Odoo_Invoices`) | dlt (Python: pandas/openpyxl); every sheet loaded as its own raw table | Daily, 2 AM — SQL Server Agent job running the SSIS package |

All three sources land as raw, untransformed tables in a single `bronze` schema (source-prefixed: `excel_*`, `odoo_*`, `salesforce_*`) — this satisfies FR-1 (staging layer) in full. Silver/Gold conformance (FR-2, FR-3) has not been built yet.

---

## 4. Functional Requirements

- **FR-1:** The system shall ingest data from all three sources listed above into a staging layer without transformation. — *Implemented for all three sources and running on an automated daily schedule: Excel (9/9 sheets), Odoo (4/4 seeded tables), Salesforce (3/3 seeded objects), all landing in the `bronze` schema.*
- **FR-2:** The system shall conform staged data into a Silver layer with standardized types, deduplicated keys, and consistent branch/officer identifiers across sources. — *Not started.*
- **FR-3:** The system shall build a Gold-layer star schema with fact tables for loan pipeline events and vendor payments, and shared dimensions for branch, loan officer, and date. — *Not started.*
- **FR-4:** The system shall expose a Power BI report including: disbursal time by branch, default/decline rate by branch, vendor AR aging, and loan pipeline funnel by stage. — *Not started.*
- **FR-5:** The Power BI report shall include a dedicated mobile layout for at least the executive summary page. — *Not started.*
- **FR-6:** The system shall enforce row-level security so a Branch Manager role sees only their own branch's data. — *Not started.*
- **FR-7:** The system shall run automated data quality checks after each load and log failures. — *Partially implemented at the ingestion level: each script retries transient failures, isolates per-table/per-object/per-sheet failures so one bad unit doesn't block the rest, and logs to a per-pipeline log file with a non-zero exit code on any real failure. SSIS additionally logs every run's outcome per source to `bronze.etl_run_log`, giving a durable, queryable success/failure history across runs. No dedicated post-load QA suite yet.*
- **FR-8 (new):** The system shall run all ingestion on an unattended daily schedule with no manual intervention. — *Implemented: SSIS package `CreditFlow_Load` deployed to the SSISDB catalog, run daily at 2 AM by a SQL Server Agent job under a dedicated service account (`svc_ssis`); 16+ consecutive successful runs logged as of this revision.*

## 5. Non-Functional Requirements

- **NFR-1 (Performance):** Daily loads shall complete within a defined window (e.g., under 30 minutes) so morning reporting is available on schedule. — *Comfortably met: all three legs combined complete in well under a minute per run (observed ~15–20 seconds), based on `bronze.etl_run_log` timestamps.*
- **NFR-2 (Data Quality):** No Gold-layer fact table row may be missing a required dimension key; QA checks shall block promotion to Gold on failure. — *N/A until Gold layer exists.*
- **NFR-3 (Security):** RLS shall be enforced at the Power BI model level, not just filtered in visuals. — *Not started.*
- **NFR-4 (Auditability):** Every table shall be traceable to its source system and load timestamp via metadata columns. — *Partially satisfied: dlt automatically adds `_dlt_load_id` and `_dlt_id` metadata columns to every loaded table for Excel and Salesforce. The direct Odoo script does not yet add equivalent load metadata — worth adding a load-timestamp column there for parity. `bronze.etl_run_log` separately tracks load-level (not row-level) run history for all three sources.*
- **NFR-5 (Maintainability):** All ETL logic shall be version-controlled in Git with a documented rollback path. — *ETL scripts are in Git (`etl/`); documented rollback path not yet written.*
- **NFR-6 (Reliability, new):** Scheduled runs shall not depend on any individual user's Windows session being active. — *Implemented: the SQL Server Agent job runs under a dedicated local service account (`svc_ssis`), independent of any personal login.*

---

## 6. Data Governance

- **Data Dictionary:** Every Gold-layer table and column documented with business definition, source system, and owner. — *Not started; no Gold layer yet.*
- **PII/KYC Classification:** Applicant name, contact info, and any identity fields are classified as sensitive and excluded from the analytics Gold layer entirely (only branch-level aggregates are surfaced) — this project does not warehouse real PII even synthetically beyond what's needed to demonstrate classification.
- **Access Control:** Role mapping (Branch Manager, Analyst, Compliance, Executive) documented and implemented via Power BI RLS roles tied to Azure AD/Entra groups or static role tables. — *Not started.*

---

## 7. System Architecture (Overview)

```
                    SQL Server Agent (daily, 2 AM)
                             │
                    SSIS package: CreditFlow_Load
                    (runs as svc_ssis service account)
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
Salesforce (CRM) ──dlt──┐    │    ┌──direct── Odoo (ERP)
                         │    │    │
                         └────┼────┘
                              │
                    Excel (workbook) ──dlt──┘
                              │
                              ▼
                  bronze schema (SQL Server)
                  excel_* / odoo_* / salesforce_*
                  + bronze.etl_run_log
                              │
                              ▼
                    Silver ──> Gold (star schema) ──> Power BI (+ mobile layout, RLS)
```

Current state: Bronze/Raw layer complete and running on an automated daily schedule, confirmed working end-to-end against live sources (Excel, Odoo, and Salesforce). QA checks between Bronze→Silver and Silver→Gold are planned but not built, since those layers don't exist yet. Full architecture diagram to be added to the repo README.

---

## 8. Success Metrics / Acceptance Criteria

- All three sources ingesting on schedule with zero manual intervention for 2 consecutive weeks. — *In progress: SQL Server Agent job now runs daily; 16+ consecutive successful runs logged in `bronze.etl_run_log` as of this revision, with the unattended-schedule clock now running toward the 2-week target.*
- QA suite catches at least one seeded bad-data scenario during testing (proves the checks actually work, not just exist).
- Power BI report loads correctly under each of the four defined RLS roles, showing only permitted data.
- Mobile layout renders correctly on a phone-sized viewport.

## 9. Out of Scope
- Real customer data of any kind.
- Loan underwriting/decisioning logic.
- Integration with a real core banking system.

---

## Appendix A: Glossary
See Section 1.4 for acronyms. Full data dictionary maintained separately in `/docs/data_dictionary.md`.
