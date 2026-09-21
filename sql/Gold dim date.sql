/* ============================================================
   CreditFlow — Gold Layer Dimension
   Target: gold.dim_date
   Generated calendar dimension, 2018-01-01 through 2027-12-31.
   Not sourced from bronze/silver -- built directly.
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'gold')
    EXEC('CREATE SCHEMA gold');
GO

IF OBJECT_ID('gold.dim_date', 'U') IS NOT NULL
    DROP TABLE gold.dim_date;
GO

CREATE TABLE gold.dim_date (
    date_key           INT             NOT NULL PRIMARY KEY,  -- yyyymmdd
    full_date            DATE            NOT NULL,
    day_of_week              TINYINT         NOT NULL,
    day_name                    NVARCHAR(10)    NOT NULL,
    day_of_month                    TINYINT         NOT NULL,
    day_of_year                          SMALLINT        NOT NULL,
    week_of_year                              TINYINT         NOT NULL,
    month_number                                  TINYINT         NOT NULL,
    month_name                                        NVARCHAR(10)    NOT NULL,
    quarter                                              TINYINT         NOT NULL,
    year                                                     SMALLINT        NOT NULL,
    is_weekend                                                 BIT             NOT NULL
);
GO

-- Fix weekday numbering so this doesn't silently depend on the server's
-- locale/session settings (@@DATEFIRST default varies by install).
SET DATEFIRST 7;   -- 1 = Sunday ... 7 = Saturday

;WITH date_seq AS (
    SELECT CAST('2018-01-01' AS DATE) AS full_date
    UNION ALL
    SELECT DATEADD(DAY, 1, full_date)
    FROM date_seq
    WHERE full_date < '2027-12-31'
)
INSERT INTO gold.dim_date (
    date_key, full_date, day_of_week, day_name, day_of_month, day_of_year,
    week_of_year, month_number, month_name, quarter, year, is_weekend
)
SELECT
    CAST(FORMAT(full_date, 'yyyyMMdd') AS INT)                    AS date_key,
    full_date,
    DATEPART(WEEKDAY, full_date)                                  AS day_of_week,
    DATENAME(WEEKDAY, full_date)                                  AS day_name,
    DATEPART(DAY, full_date)                                      AS day_of_month,
    DATEPART(DAYOFYEAR, full_date)                                AS day_of_year,
    DATEPART(WEEK, full_date)                                     AS week_of_year,
    DATEPART(MONTH, full_date)                                    AS month_number,
    DATENAME(MONTH, full_date)                                    AS month_name,
    DATEPART(QUARTER, full_date)                                  AS quarter,
    DATEPART(YEAR, full_date)                                     AS year,
    CASE WHEN DATEPART(WEEKDAY, full_date) IN (1, 7) THEN 1 ELSE 0 END AS is_weekend  -- Sat/Sun
FROM date_seq
OPTION (MAXRECURSION 0);
GO

SELECT * FROM gold.dim_date ORDER BY date_key;
-- Expect 3653 rows (10 years, 2 of them leap years' worth of extra days accounted for).