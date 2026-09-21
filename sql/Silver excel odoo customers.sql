/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.excel_odoo_customers
   Target: silver.excel_odoo_customers
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.excel_odoo_customers', 'U') IS NOT NULL
    DROP TABLE silver.excel_odoo_customers;
GO

CREATE TABLE silver.excel_odoo_customers (
    customer_ref         NVARCHAR(20)    NOT NULL PRIMARY KEY,
    company_name           NVARCHAR(255)   NOT NULL,
    tax_id                    NVARCHAR(50)    NULL,
    city                        NVARCHAR(100)   NULL,
    country                       NVARCHAR(100)   NULL,
    phone                            NVARCHAR(50)    NULL,
    email                              NVARCHAR(255)   NULL,
    customer_since                       DATE            NULL,
    load_date                              DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                            NVARCHAR(20)    NOT NULL DEFAULT 'excel'
);
GO

-- Source sheet had duplicate headers (company_name/_1, tax_id/_1, phone/_1,
-- email/_1, customer_since/_1). Verified via match-rate check which side of
-- each pair to keep:
--   company_name  : proper title case, company_name_1 has inconsistent casing
--   tax_id        : identical to tax_id_1, drop the duplicate
--   phone_1       : phone is FLOAT and lost leading zeros, phone_1 (text) is correct
--   customer_since: reliable typed column, customer_since_1 is messier free text of the same date
--   email         : genuinely complementary (one populated where the other isn't) -> COALESCE
INSERT INTO silver.excel_odoo_customers (
    customer_ref, company_name, tax_id, city, country, phone, email, customer_since
)
SELECT
    customer_ref,
    LTRIM(RTRIM(company_name))                                      AS company_name,
    NULLIF(LTRIM(RTRIM(tax_id)), '')                                AS tax_id,
    NULLIF(LTRIM(RTRIM(city)), '')                                  AS city,
    NULLIF(LTRIM(RTRIM(country)), '')                               AS country,
    NULLIF(LTRIM(RTRIM(phone_1)), '')                               AS phone,
    NULLIF(LOWER(LTRIM(RTRIM(COALESCE(email, email_1)))), '')       AS email,
    CAST(customer_since AS DATE)                                    AS customer_since
FROM bronze.excel_odoo_customers;
GO

SELECT * FROM silver.excel_odoo_customers ORDER BY customer_ref;