/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.excel_odoo_invoices
   Target: silver.excel_odoo_invoices
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.excel_odoo_invoices', 'U') IS NOT NULL
    DROP TABLE silver.excel_odoo_invoices;
GO

CREATE TABLE silver.excel_odoo_invoices (
    invoice_no           NVARCHAR(20)    NOT NULL PRIMARY KEY,
    customer_name           NVARCHAR(255)   NOT NULL,
    invoice_date              DATE            NULL,
    due_date                    DATE            NULL,
    amount_due                    DECIMAL(18,2)   NULL,
    amount_paid                      DECIMAL(18,2)   NULL,
    payment_status                     NVARCHAR(20)    NULL,
    review_flag                           NVARCHAR(20)    NULL,
    load_date                               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                             NVARCHAR(20)    NOT NULL DEFAULT 'excel'
);
GO

-- customer_name_1 / invoice_date_1 / due_date_1 / payment_status_1 confirmed
-- redundant (65/65 match) -- dropped, same as the sales orders table.
-- amount_due / amount_paid came in as text with thousands-separator commas
-- (e.g. "2,188,447") -- strip commas before casting to decimal.
-- "staus" is NOT a duplicate of payment_status (0/65 match, different value
-- set entirely) -- it's a separate manual review flag, kept as its own
-- column and renamed for clarity.
INSERT INTO silver.excel_odoo_invoices (
    invoice_no, customer_name, invoice_date, due_date,
    amount_due, amount_paid, payment_status, review_flag
)
SELECT
    invoice_no,
    LTRIM(RTRIM(customer_name))                                        AS customer_name,
    CAST(invoice_date AS DATE)                                         AS invoice_date,
    CAST(due_date AS DATE)                                             AS due_date,
    CAST(REPLACE(REPLACE(amount_due, ',', ''), ' ', '') AS DECIMAL(18,2))   AS amount_due,
    CAST(REPLACE(REPLACE(amount_paid, ',', ''), ' ', '') AS DECIMAL(18,2))  AS amount_paid,
    NULLIF(LTRIM(RTRIM(payment_status)), '')                           AS payment_status,
    NULLIF(LTRIM(RTRIM(staus)), '')                                    AS review_flag
FROM bronze.excel_odoo_invoices;
GO

SELECT * FROM silver.excel_odoo_invoices ORDER BY invoice_no;