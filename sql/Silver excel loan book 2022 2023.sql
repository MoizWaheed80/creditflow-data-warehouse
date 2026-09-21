/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.excel_loan_book_2022_2023
   Target: silver.excel_loan_book_2022_2023
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.excel_loan_book_2022_2023', 'U') IS NOT NULL
    DROP TABLE silver.excel_loan_book_2022_2023;
GO

CREATE TABLE silver.excel_loan_book_2022_2023 (
    loan_record_id       INT             IDENTITY(1,1) PRIMARY KEY,
    company                NVARCHAR(255)   NOT NULL,
    loan_type                NVARCHAR(50)    NULL,
    loan_amount                DECIMAL(18,2)   NULL,
    currency                     NVARCHAR(10)    NULL,
    loan_date                      DATE            NULL,
    status                           NVARCHAR(50)    NULL,
    notes                              NVARCHAR(MAX)   NULL,
    source_period                       NVARCHAR(20)    NULL,
    load_date                             DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                           NVARCHAR(20)    NOT NULL DEFAULT 'excel'
);
GO

-- Different status vocabulary this year (Past due 30 days, Client requested
-- top-up) but nothing placeholder-like, so no normalization needed. Same
-- cleaning + amount cast as the other two loan book years.
INSERT INTO silver.excel_loan_book_2022_2023 (
    company, loan_type, loan_amount, currency, loan_date, status, notes, source_period
)
SELECT
    LTRIM(RTRIM(company))                  AS company,
    NULLIF(LTRIM(RTRIM(loan_type)), '')    AS loan_type,
    CAST(amount_pkrx AS DECIMAL(18,2))     AS loan_amount,
    NULLIF(LTRIM(RTRIM(currency)), '')     AS currency,
    CAST(date AS DATE)                     AS loan_date,
    LTRIM(RTRIM(status))                   AS status,
    NULLIF(LTRIM(RTRIM(notes)), '')        AS notes,
    NULLIF(LTRIM(RTRIM(source_block)), '') AS source_period
FROM bronze.excel_loan_book_2022_2023;
GO

SELECT * FROM silver.excel_loan_book_2022_2023 ORDER BY loan_record_id;