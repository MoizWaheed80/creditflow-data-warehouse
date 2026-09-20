/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.salesforce_account
   Target: silver.salesforce_account
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.salesforce_account', 'U') IS NOT NULL
    DROP TABLE silver.salesforce_account;
GO

CREATE TABLE silver.salesforce_account (
    account_id            NVARCHAR(20)    NOT NULL PRIMARY KEY,
    account_name            NVARCHAR(255)   NOT NULL,
    account_type             NVARCHAR(50)    NULL,
    billing_street             NVARCHAR(255)   NULL,
    billing_city                 NVARCHAR(100)   NULL,
    billing_state                  NVARCHAR(100)   NULL,
    billing_country                  NVARCHAR(100)   NULL,
    phone                              NVARCHAR(50)    NULL,
    industry                             NVARCHAR(100)   NULL,
    annual_revenue                        DECIMAL(18,2)   NULL,
    number_of_employees                     BIGINT          NULL,
    ownership                                 NVARCHAR(50)    NULL,
    rating                                     NVARCHAR(20)    NULL,
    is_active                                   NVARCHAR(10)    NULL,
    customer_priority                             NVARCHAR(20)    NULL,
    sla                                             NVARCHAR(20)    NULL,
    source_created_date                               DATETIMEOFFSET  NULL,
    source_modified_date                                DATETIMEOFFSET  NULL,
    load_date                                             DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                                           NVARCHAR(20)    NOT NULL DEFAULT 'salesforce'
);
GO

-- Real accounts always have at least one business attribute filled in
-- (industry, revenue, employee count, or type); the synthetic filler rows
-- (a name with everything else NULL) have none. is_deleted excludes
-- Salesforce's soft-deleted records.
INSERT INTO silver.salesforce_account (
    account_id, account_name, account_type,
    billing_street, billing_city, billing_state, billing_country,
    phone, industry, annual_revenue, number_of_employees, ownership, rating,
    is_active, customer_priority, sla,
    source_created_date, source_modified_date
)
SELECT
    id,
    LTRIM(RTRIM(name))                          AS account_name,
    type                                          AS account_type,
    NULLIF(LTRIM(RTRIM(billing_street)), '')     AS billing_street,
    NULLIF(LTRIM(RTRIM(billing_city)), '')       AS billing_city,
    NULLIF(LTRIM(RTRIM(billing_state)), '')      AS billing_state,
    NULLIF(LTRIM(RTRIM(billing_country)), '')    AS billing_country,
    NULLIF(LTRIM(RTRIM(phone)), '')               AS phone,
    industry,
    CAST(annual_revenue AS DECIMAL(18,2))         AS annual_revenue,
    number_of_employees,
    ownership,
    rating,
    active__c                                       AS is_active,
    customer_priority__c                              AS customer_priority,
    sla__c                                              AS sla,
    created_date,
    last_modified_date
FROM bronze.salesforce_account
WHERE is_deleted = 0
  AND (industry IS NOT NULL 
       OR annual_revenue IS NOT NULL 
       OR type IS NOT NULL 
       OR number_of_employees IS NOT NULL);
GO

SELECT * FROM silver.salesforce_account ORDER BY account_name;