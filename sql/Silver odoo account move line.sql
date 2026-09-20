/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.odoo_account_move_line
   Target: silver.odoo_account_move_line
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.odoo_account_move_line', 'U') IS NOT NULL
    DROP TABLE silver.odoo_account_move_line;
GO

CREATE TABLE silver.odoo_account_move_line (
    line_id                BIGINT          NOT NULL PRIMARY KEY,
    move_id                 BIGINT          NULL,
    move_name                NVARCHAR(50)    NULL,
    journal_id                BIGINT          NULL,
    account_id                 BIGINT          NULL,
    partner_id                  BIGINT          NULL,
    parent_state                 NVARCHAR(20)    NULL,
    display_type                  NVARCHAR(20)    NULL,
    ref                             NVARCHAR(255)   NULL,
    line_description                 NVARCHAR(255)   NULL,
    line_date                          DATE            NULL,
    invoice_date                        DATE            NULL,
    date_maturity                        DATE            NULL,
    debit                                  DECIMAL(18,2)   NULL,
    credit                                  DECIMAL(18,2)   NULL,
    balance                                 DECIMAL(18,2)   NULL,
    amount_currency                          DECIMAL(18,2)   NULL,
    amount_residual                           DECIMAL(18,2)   NULL,
    quantity                                    DECIMAL(18,4)   NULL,
    price_unit                                   DECIMAL(18,2)   NULL,
    price_subtotal                                DECIMAL(18,2)   NULL,
    price_total                                    DECIMAL(18,2)   NULL,
    discount                                        DECIMAL(9,2)    NULL,
    reconciled                                       BIT             NOT NULL,
    source_create_date                                DATETIME2       NULL,
    source_write_date                                  DATETIME2       NULL,
    load_date                                           DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                                        NVARCHAR(20)    NOT NULL DEFAULT 'odoo'
);
GO

-- Only posted lines belong in a fact table used for reporting; draft/cancelled
-- lines aren't real transactions yet. Money fields cast FLOAT -> DECIMAL,
-- same reasoning as odoo_account_move.
INSERT INTO silver.odoo_account_move_line (
    line_id, move_id, move_name, journal_id, account_id, partner_id,
    parent_state, display_type, ref, line_description,
    line_date, invoice_date, date_maturity,
    debit, credit, balance, amount_currency, amount_residual,
    quantity, price_unit, price_subtotal, price_total, discount,
    reconciled, source_create_date, source_write_date
)
SELECT
    id,
    move_id,
    LTRIM(RTRIM(move_name))                     AS move_name,
    journal_id,
    account_id,
    partner_id,
    parent_state,
    display_type,
    NULLIF(LTRIM(RTRIM(ref)), '')                AS ref,
    NULLIF(LTRIM(RTRIM(name)), '')               AS line_description,
    date                                          AS line_date,
    invoice_date,
    date_maturity,
    CAST(debit AS DECIMAL(18,2))                 AS debit,
    CAST(credit AS DECIMAL(18,2))                AS credit,
    CAST(balance AS DECIMAL(18,2))               AS balance,
    CAST(amount_currency AS DECIMAL(18,2))       AS amount_currency,
    CAST(amount_residual AS DECIMAL(18,2))       AS amount_residual,
    CAST(quantity AS DECIMAL(18,4))              AS quantity,
    CAST(price_unit AS DECIMAL(18,2))            AS price_unit,
    CAST(price_subtotal AS DECIMAL(18,2))        AS price_subtotal,
    CAST(price_total AS DECIMAL(18,2))           AS price_total,
    CAST(discount AS DECIMAL(9,2))               AS discount,
    reconciled,
    create_date,
    write_date
FROM bronze.odoo_account_move_line
WHERE parent_state = 'posted';
GO

SELECT * FROM silver.odoo_account_move_line ORDER BY line_id;