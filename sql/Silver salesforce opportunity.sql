/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.salesforce_opportunity
   Target: silver.salesforce_opportunity
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.salesforce_opportunity', 'U') IS NOT NULL
    DROP TABLE silver.salesforce_opportunity;
GO

CREATE TABLE silver.salesforce_opportunity (
    opportunity_id         NVARCHAR(20)    NOT NULL PRIMARY KEY,
    account_id               NVARCHAR(20)    NULL,
    opportunity_name           NVARCHAR(255)   NOT NULL,
    stage_name                    NVARCHAR(50)    NULL,
    amount                           DECIMAL(18,2)   NULL,
    probability                       DECIMAL(5,2)    NULL,
    expected_revenue                    DECIMAL(18,2)   NULL,
    close_date                            DATE            NULL,
    opportunity_type                        NVARCHAR(50)    NULL,
    lead_source                               NVARCHAR(50)    NULL,
    is_closed                                   BIT             NOT NULL,
    is_won                                        BIT             NOT NULL,
    forecast_category                               NVARCHAR(50)    NULL,
    source_created_date                               DATETIMEOFFSET  NULL,
    source_modified_date                                DATETIMEOFFSET  NULL,
    load_date                                             DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                                           NVARCHAR(20)    NOT NULL DEFAULT 'salesforce'
);
GO

-- No junk-row filter needed here (unlike Account/Contact) -- this table
-- looks like genuine pipeline data. Just clean text, cast money/percent
-- fields, drop Salesforce soft-deletes.
INSERT INTO silver.salesforce_opportunity (
    opportunity_id, account_id, opportunity_name, stage_name,
    amount, probability, expected_revenue, close_date,
    opportunity_type, lead_source, is_closed, is_won, forecast_category,
    source_created_date, source_modified_date
)
SELECT
    id,
    account_id,
    LTRIM(RTRIM(name))                        AS opportunity_name,
    stage_name,
    CAST(amount AS DECIMAL(18,2))             AS amount,
    CAST(probability AS DECIMAL(5,2))         AS probability,
    CAST(expected_revenue AS DECIMAL(18,2))   AS expected_revenue,
    close_date,
    type                                        AS opportunity_type,
    NULLIF(LTRIM(RTRIM(lead_source)), '')       AS lead_source,
    is_closed,
    is_won,
    forecast_category,
    created_date,
    last_modified_date
FROM bronze.salesforce_opportunity
WHERE is_deleted = 0;
GO

SELECT * FROM silver.salesforce_opportunity ORDER BY account_id, close_date;