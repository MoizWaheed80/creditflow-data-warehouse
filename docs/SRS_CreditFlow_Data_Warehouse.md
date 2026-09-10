# Software Requirements Specification
## CreditFlow Digital Lending Operations Warehouse

**Version:** 1.0
**Author:** Abdul Moiz Waheed
**Status:** Draft

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
| CRM | Customer Relationship Management (HubSpot, loan pipeline) |
| ETL/ELT | Extract-Transform-Load / Extract-Load-Transform |
| SSIS | SQL Server Integration Services |
| RLS | Row-Level Security |
| PII | Personally Identifiable Information |
| KYC | Know Your Customer (identity/verification fields) |
| Medallion Architecture | Bronze (raw) / Silver (conformed) / Gold (business marts) layering |

---

## 2. Overall Description

### 2.1 Business Context
CreditFlow operates through regional branches. Loan officers track applicants in HubSpot. Branch admins log vendor invoices and expenses in Odoo. Some branches still record manual loan approval steps in Excel because they haven't been migrated onto the CRM workflow yet. Leadership currently has no single view across these three sources.

### 2.2 Product Perspective
A new, standalone analytics platform. It reads from source systems on a schedule; it does not write back to them.

### 2.3 User Classes and Characteristics
- **Branch Manager** — needs branch-scoped performance metrics only (RLS-restricted).
- **Loan Operations Analyst** — needs cross-branch visibility into pipeline and disbursal metrics.
- **Compliance Reviewer** — needs an auditable data dictionary and PII handling record, not raw report access.
- **Executive** — needs summary KPIs, mobile-friendly.

### 2.4 Operating Environment
- SQL Server (on-prem or Azure SQL) as the warehouse
- SSIS + SQL Server Agent for scheduled ingestion of Odoo and Excel
- dlt for HubSpot ingestion
- Power BI Desktop + Power BI Service for publishing
- Self-hosted Odoo Community Edition (Docker) as the ERP source
- HubSpot free CRM tier as the CRM source

### 2.5 Assumptions and Dependencies
- All source data is synthetic/seeded, not real customer data.
- HubSpot free tier's API limits (contact/record caps) are sufficient for a demo-scale dataset.
- Odoo's external API is only available on self-hosted or custom-plan instances, not the hosted free tier; this project self-hosts.

---

## 3. Data Sources

| Source | System | Data Extracted | Ingestion Method | Frequency |
|---|---|---|---|---|
| Loan pipeline | HubSpot (CRM) | Applicants, deal stages, loan officer, branch, amount requested | dlt (REST API) | Daily |
| Vendor operations | Odoo (ERP, self-hosted) | Vendor invoices, branch expenses, payment status | SSIS | Daily |
| Manual branch tracker | Excel | Loan approvals not yet in CRM, branch-reported disbursal dates | SSIS (file watcher) | Weekly |

---

## 4. Functional Requirements

- **FR-1:** The system shall ingest data from all three sources listed above into a staging layer without transformation.
- **FR-2:** The system shall conform staged data into a Silver layer with standardized types, deduplicated keys, and consistent branch/officer identifiers across sources.
- **FR-3:** The system shall build a Gold-layer star schema with fact tables for loan pipeline events and vendor payments, and shared dimensions for branch, loan officer, and date.
- **FR-4:** The system shall expose a Power BI report including: disbursal time by branch, default/decline rate by branch, vendor AR aging, and loan pipeline funnel by stage.
- **FR-5:** The Power BI report shall include a dedicated mobile layout for at least the executive summary page.
- **FR-6:** The system shall enforce row-level security so a Branch Manager role sees only their own branch's data.
- **FR-7:** The system shall run automated data quality checks after each load and log failures.

## 5. Non-Functional Requirements

- **NFR-1 (Performance):** Daily loads shall complete within a defined window (e.g., under 30 minutes) so morning reporting is available on schedule.
- **NFR-2 (Data Quality):** No Gold-layer fact table row may be missing a required dimension key; QA checks shall block promotion to Gold on failure.
- **NFR-3 (Security):** RLS shall be enforced at the Power BI model level, not just filtered in visuals.
- **NFR-4 (Auditability):** Every table shall be traceable to its source system and load timestamp via metadata columns.
- **NFR-5 (Maintainability):** All ETL logic shall be version-controlled in Git with a documented rollback path.

---

## 6. Data Governance

- **Data Dictionary:** Every Gold-layer table and column documented with business definition, source system, and owner.
- **PII/KYC Classification:** Applicant name, contact info, and any identity fields are classified as sensitive and excluded from the analytics Gold layer entirely (only branch-level aggregates are surfaced) — this project does not warehouse real PII even synthetically beyond what's needed to demonstrate classification.
- **Access Control:** Role mapping (Branch Manager, Analyst, Compliance, Executive) documented and implemented via Power BI RLS roles tied to Azure AD/Entra groups or static role tables.

---

## 7. System Architecture (Overview)

```
HubSpot (CRM)  ──dlt──┐
Odoo (ERP)     ──SSIS─┼──> Staging ──> Bronze ──> Silver ──> Gold (star schema) ──> Power BI (+ mobile layout, RLS)
Excel (manual) ──SSIS─┘
```

QA checks run between Bronze→Silver and Silver→Gold. Full architecture diagram to be added to the repo README.

---

## 8. Success Metrics / Acceptance Criteria

- All three sources ingesting on schedule with zero manual intervention for 2 consecutive weeks.
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
