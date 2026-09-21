/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.excel_sf_accounts
   Target: silver.excel_sf_accounts
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.excel_sf_accounts', 'U') IS NOT NULL
    DROP TABLE silver.excel_sf_accounts;
GO

CREATE TABLE silver.excel_sf_accounts (
    account_id           NVARCHAR(20)    NOT NULL PRIMARY KEY,
    account_name            NVARCHAR(255)   NOT NULL,
    industry                   NVARCHAR(100)   NULL,
    billing_city                  NVARCHAR(100)   NULL,
    billing_country                  NVARCHAR(100)   NULL,
    phone                                NVARCHAR(50)    NULL,
    annual_revenue                        DECIMAL(18,2)   NULL,
    account_owner                           NVARCHAR(100)   NULL,
    created_date                              DATE            NULL,
    rating                                       NVARCHAR(20)    NULL,
    load_date                                      DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                                    NVARCHAR(20)    NOT NULL DEFAULT 'excel'
);
GO

-- account_id2 / column1 / phon / created_date all confirmed redundant
-- duplicates of account_id / account_name / phone / date respectively
-- (verified via match-rate checks, not assumed from the lost/typo'd
-- headers alone). Every bronze column here is NVARCHAR, including dates,
-- so TRY_CAST/TRY_CONVERT throughout rather than assuming clean input.
INSERT INTO silver.excel_sf_accounts (
    account_id, account_name, industry, billing_city, billing_country,
    phone, annual_revenue, account_owner, created_date, rating
)
SELECT
    account_id,
    LTRIM(RTRIM(account_name))                                              AS account_name,
    NULLIF(LTRIM(RTRIM(industry)), '')                                      AS industry,
    NULLIF(LTRIM(RTRIM(billing_city)), '')                                  AS billing_city,
    NULLIF(LTRIM(RTRIM(billing_country)), '')                               AS billing_country,
    NULLIF(LTRIM(RTRIM(phone)), '')                                         AS phone,
    TRY_CAST(REPLACE(REPLACE(annual_revenue, ',', ''), ' ', '') AS DECIMAL(18,2)) AS annual_revenue,
    NULLIF(LTRIM(RTRIM(account_owner)), '')                                 AS account_owner,
    TRY_CAST(date AS DATE)                                                  AS created_date,
    NULLIF(LTRIM(RTRIM(rating)), '')                                        AS rating
FROM bronze.excel_sf_accounts;
GO

SELECT * FROM silver.excel_sf_accounts ORDER BY account_id;