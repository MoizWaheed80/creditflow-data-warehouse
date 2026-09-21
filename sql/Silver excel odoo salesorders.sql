/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.excel_odoo_salesorders
   Target: silver.excel_odoo_salesorders
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.excel_odoo_salesorders', 'U') IS NOT NULL
    DROP TABLE silver.excel_odoo_salesorders;
GO

CREATE TABLE silver.excel_odoo_salesorders (
    order_ref            NVARCHAR(20)    NOT NULL PRIMARY KEY,
    customer_name           NVARCHAR(255)   NOT NULL,
    order_date                DATE            NULL,
    loan_product                 NVARCHAR(100)   NULL,
    disbursed_amount                DECIMAL(18,2)   NULL,
    currency                          NVARCHAR(10)    NULL,
    status                               NVARCHAR(50)    NULL,
    load_date                             DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                           NVARCHAR(20)    NOT NULL DEFAULT 'excel'
);
GO

-- Same duplicate-header pattern as excel_odoo_customers. Match-rate check
-- confirmed all three pairs are genuinely redundant (89/89) -- keeping the
-- consistently-formatted side of each, dropping the messier _1 duplicate.
-- order_date_1 in particular mixes several different date formats row to row.
INSERT INTO silver.excel_odoo_salesorders (
    order_ref, customer_name, order_date, loan_product, disbursed_amount, currency, status
)
SELECT
    order_ref,
    LTRIM(RTRIM(customer_name))               AS customer_name,
    CAST(order_date AS DATE)                  AS order_date,
    NULLIF(LTRIM(RTRIM(loan_product)), '')    AS loan_product,
    CAST(disbursed_amount AS DECIMAL(18,2))   AS disbursed_amount,
    NULLIF(LTRIM(RTRIM(currency)), '')        AS currency,
    NULLIF(LTRIM(RTRIM(status)), '')          AS status
FROM bronze.excel_odoo_salesorders;
GO

SELECT * FROM silver.excel_odoo_salesorders ORDER BY order_ref;