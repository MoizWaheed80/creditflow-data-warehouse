/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.excel_sf_contacts
   Target: silver.excel_sf_contacts
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.excel_sf_contacts', 'U') IS NOT NULL
    DROP TABLE silver.excel_sf_contacts;
GO

CREATE TABLE silver.excel_sf_contacts (
    contact_id           NVARCHAR(20)    NOT NULL PRIMARY KEY,
    account_name            NVARCHAR(255)   NULL,
    first_name                 NVARCHAR(100)   NULL,
    last_name                     NVARCHAR(100)   NULL,
    title                            NVARCHAR(100)   NULL,
    email                               NVARCHAR(255)   NULL,
    phone                                  NVARCHAR(50)    NULL,
    mobile                                    NVARCHAR(50)    NULL,
    load_date                                  DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                                NVARCHAR(20)    NOT NULL DEFAULT 'excel'
);
GO

-- account_nam confirmed redundant duplicate of account_name (46/46 match),
-- dropped. phone / phone_1 are complementary, not redundant -- where phone
-- (text, properly formatted) exists use it; otherwise fall back to phone_1
-- (FLOAT, missing leading zeros -- same lossy pattern seen on every other
-- FLOAT-typed phone column in this warehouse).
INSERT INTO silver.excel_sf_contacts (
    contact_id, account_name, first_name, last_name, title, email, phone, mobile
)
SELECT
    contact_id,
    NULLIF(LTRIM(RTRIM(account_name)), '')                    AS account_name,
    NULLIF(LTRIM(RTRIM(first_name)), '')                      AS first_name,
    NULLIF(LTRIM(RTRIM(last_name)), '')                       AS last_name,
    NULLIF(LTRIM(RTRIM(title)), '')                           AS title,
    NULLIF(LOWER(LTRIM(RTRIM(email))), '')                    AS email,
    COALESCE(
        NULLIF(LTRIM(RTRIM(phone)), ''),
        CAST(TRY_CAST(phone_1 AS BIGINT) AS NVARCHAR(20))
    )                                                           AS phone,
    NULLIF(LTRIM(RTRIM(mobile)), '')                          AS mobile
FROM bronze.excel_sf_contacts;
GO

SELECT * FROM silver.excel_sf_contacts ORDER BY contact_id;