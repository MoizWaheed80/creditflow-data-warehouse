/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.odoo_account_account
   Target: silver.odoo_account_account
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.odoo_account_account', 'U') IS NOT NULL
    DROP TABLE silver.odoo_account_account;
GO

CREATE TABLE silver.odoo_account_account (
    account_id           INT             NOT NULL PRIMARY KEY,
    account_code          NVARCHAR(50)    NULL,
    account_name          NVARCHAR(255)   NOT NULL,
    account_type          NVARCHAR(50)    NULL,
    currency_id           INT             NULL,
    note                  NVARCHAR(MAX)   NULL,
    deprecated            BIT             NOT NULL,
    reconcile             BIT             NOT NULL,
    non_trade             BIT             NOT NULL,
    source_create_date    DATETIME2       NULL,
    source_write_date     DATETIME2       NULL,
    load_date             DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system         NVARCHAR(20)    NOT NULL DEFAULT 'odoo'
);
GO

-- name and code_store are Odoo's JSON translation/multi-company wrappers
-- ({"en_US": "..."} / {"<company_id>": "..."}) — pull the plain value out
-- of each rather than storing the raw JSON string.
INSERT INTO silver.odoo_account_account (
    account_id, account_code, account_name, account_type,
    currency_id, note, deprecated, reconcile, non_trade,
    source_create_date, source_write_date
)
SELECT
    a.id,
    code.account_code,
    JSON_VALUE(a.name, '$.en_US')          AS account_name,
    a.account_type,
    a.currency_id,
    NULLIF(LTRIM(RTRIM(a.note)), '')       AS note,
    a.deprecated,
    a.reconcile,
    a.non_trade,
    a.create_date,
    a.write_date
FROM bronze.odoo_account_account a
CROSS APPLY (
    SELECT TOP 1 [value] AS account_code
    FROM OPENJSON(a.code_store)
) code;
GO

SELECT * FROM silver.odoo_account_account ORDER BY account_id;