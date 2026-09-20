/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.odoo_res_partner
   Target: silver.odoo_res_partner
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.odoo_res_partner', 'U') IS NOT NULL
    DROP TABLE silver.odoo_res_partner;
GO

CREATE TABLE silver.odoo_res_partner (
    partner_id              INT             NOT NULL PRIMARY KEY,
    partner_name             NVARCHAR(255)   NOT NULL,
    complete_name            NVARCHAR(255)   NULL,
    is_company               BIT             NULL,
    parent_id                INT             NULL,
    commercial_partner_id    INT             NULL,
    customer_rank            INT             NOT NULL,
    supplier_rank            INT             NOT NULL,
    country_id               INT             NULL,
    city                     NVARCHAR(100)   NULL,
    street                   NVARCHAR(255)   NULL,
    phone                    NVARCHAR(50)    NULL,
    mobile                   NVARCHAR(50)    NULL,
    email                    NVARCHAR(255)   NULL,
    vat                      NVARCHAR(50)    NULL,
    is_active                BIT             NOT NULL,
    source_create_date       DATETIME2       NULL,
    source_write_date        DATETIME2       NULL,
    load_date                DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system            NVARCHAR(20)    NOT NULL DEFAULT 'odoo'
);
GO

-- Filter to real business rows (rank > 0), clean text fields,
-- dedup near-identical names (keep earliest create_date), load.
;WITH filtered AS (
    SELECT
        id,
        name,
        complete_name,
        is_company,
        parent_id,
        commercial_partner_id,
        customer_rank,
        supplier_rank,
        country_id,
        NULLIF(LTRIM(RTRIM(city)), '')            AS city,
        NULLIF(LTRIM(RTRIM(street)), '')          AS street,
        NULLIF(LTRIM(RTRIM(phone)), '')           AS phone,
        NULLIF(LTRIM(RTRIM(mobile)), '')          AS mobile,
        NULLIF(LOWER(LTRIM(RTRIM(email))), '')    AS email,
        NULLIF(LTRIM(RTRIM(vat)), '')             AS vat,
        active,
        create_date,
        write_date,
        LOWER(
            CASE WHEN RIGHT(LTRIM(RTRIM(name)), 1) = '.'
                 THEN LEFT(LTRIM(RTRIM(name)), LEN(LTRIM(RTRIM(name))) - 1)
                 ELSE LTRIM(RTRIM(name))
            END
        ) AS name_key
    FROM bronze.odoo_res_partner
    WHERE customer_rank > 0 OR supplier_rank > 0
),
deduped AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY name_key ORDER BY create_date ASC, id ASC) AS rn
    FROM filtered
)
INSERT INTO silver.odoo_res_partner (
    partner_id, partner_name, complete_name, is_company, parent_id,
    commercial_partner_id, customer_rank, supplier_rank, country_id,
    city, street, phone, mobile, email, vat, is_active,
    source_create_date, source_write_date
)
SELECT
    id,
    LTRIM(RTRIM(name))    AS partner_name,
    complete_name,
    is_company,
    parent_id,
    commercial_partner_id,
    customer_rank,
    supplier_rank,
    country_id,
    city, street, phone, mobile, email, vat,
    active,
    create_date,
    write_date
FROM deduped
WHERE rn = 1;
GO
