/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.excel_sf_opportunities
   Target: silver.excel_sf_opportunities
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.excel_sf_opportunities', 'U') IS NOT NULL
    DROP TABLE silver.excel_sf_opportunities;
GO

CREATE TABLE silver.excel_sf_opportunities (
    opportunity_id        NVARCHAR(20)    NOT NULL PRIMARY KEY,
    account_name             NVARCHAR(255)   NULL,
    opportunity_name            NVARCHAR(255)   NULL,
    stage                          NVARCHAR(50)    NULL,
    amount                            DECIMAL(18,2)   NULL,
    currency                            NVARCHAR(10)    NULL,
    close_date                            DATE            NULL,
    owner                                    NVARCHAR(100)   NULL,
    loan_type                                  NVARCHAR(100)   NULL,
    load_date                                    DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                                  NVARCHAR(20)    NOT NULL DEFAULT 'excel'
);
GO

-- account_nam / opportunity_nam / stage_1 / close_date(text) all confirmed
-- redundant duplicates (75/75 match each) of account_name / opportunity_name
-- / stage / date. Dropped, keeping the cleaner-typed or consistently-cased
-- side of each pair, same as every other Excel table so far.
INSERT INTO silver.excel_sf_opportunities (
    opportunity_id, account_name, opportunity_name, stage,
    amount, currency, close_date, owner, loan_type
)
SELECT
    opportunity_id,
    LTRIM(RTRIM(account_name))                AS account_name,
    LTRIM(RTRIM(opportunity_name))             AS opportunity_name,
    LTRIM(RTRIM(stage))                        AS stage,
    CAST(amount AS DECIMAL(18,2))              AS amount,
    NULLIF(LTRIM(RTRIM(currency)), '')         AS currency,
    CAST(date AS DATE)                         AS close_date,
    NULLIF(LTRIM(RTRIM(owner)), '')            AS owner,
    NULLIF(LTRIM(RTRIM(loan_type)), '')        AS loan_type
FROM bronze.excel_sf_opportunities;
GO

SELECT * FROM silver.excel_sf_opportunities ORDER BY opportunity_id;