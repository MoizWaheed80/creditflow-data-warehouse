/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.odoo_account_move
   Target: silver.odoo_account_move
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.odoo_account_move', 'U') IS NOT NULL
    DROP TABLE silver.odoo_account_move;
GO

CREATE TABLE silver.odoo_account_move (
    move_id                  BIGINT          NOT NULL PRIMARY KEY,
    move_name                 NVARCHAR(50)    NULL,
    ref                       NVARCHAR(255)   NULL,
    state                     NVARCHAR(20)    NULL,
    move_type                 NVARCHAR(20)    NULL,
    partner_id                BIGINT          NULL,
    commercial_partner_id      BIGINT          NULL,
    journal_id                 BIGINT          NULL,
    company_id                 BIGINT          NULL,
    currency_id                BIGINT          NULL,
    invoice_date               DATE            NULL,
    invoice_date_due           DATE            NULL,
    move_date                  DATE            NULL,
    amount_untaxed              DECIMAL(18,2)   NULL,
    amount_tax                  DECIMAL(18,2)   NULL,
    amount_total                DECIMAL(18,2)   NULL,
    amount_residual              DECIMAL(18,2)   NULL,
    payment_state                NVARCHAR(20)    NULL,
    narration                    NVARCHAR(MAX)   NULL,
    source_create_date            DATETIME2       NULL,
    source_write_date             DATETIME2       NULL,
    load_date                     DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                 NVARCHAR(20)    NOT NULL DEFAULT 'odoo'
);
GO

-- Money fields come in as FLOAT in bronze (Odoo's native type) — cast to
-- DECIMAL here so no rounding drift carries into gold-layer aggregates.
INSERT INTO silver.odoo_account_move (
    move_id, move_name, ref, state, move_type,
    partner_id, commercial_partner_id, journal_id, company_id, currency_id,
    invoice_date, invoice_date_due, move_date,
    amount_untaxed, amount_tax, amount_total, amount_residual,
    payment_state, narration,
    source_create_date, source_write_date
)
SELECT
    id,
    LTRIM(RTRIM(name))                     AS move_name,
    NULLIF(LTRIM(RTRIM(ref)), '')          AS ref,
    state,
    move_type,
    partner_id,
    commercial_partner_id,
    journal_id,
    company_id,
    currency_id,
    invoice_date,
    invoice_date_due,
    date                                    AS move_date,
    CAST(amount_untaxed AS DECIMAL(18,2))  AS amount_untaxed,
    CAST(amount_tax AS DECIMAL(18,2))      AS amount_tax,
    CAST(amount_total AS DECIMAL(18,2))    AS amount_total,
    CAST(amount_residual AS DECIMAL(18,2)) AS amount_residual,
    payment_state,
    NULLIF(LTRIM(RTRIM(narration)), '')    AS narration,
    create_date,
    write_date
FROM bronze.odoo_account_move;
GO

SELECT * FROM silver.odoo_account_move ORDER BY move_id;