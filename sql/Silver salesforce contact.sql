/* ============================================================
   CreditFlow — Silver Layer Transformation
   Source: bronze.salesforce_contact
   Target: silver.salesforce_contact
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'silver')
    EXEC('CREATE SCHEMA silver');
GO

IF OBJECT_ID('silver.salesforce_contact', 'U') IS NOT NULL
    DROP TABLE silver.salesforce_contact;
GO

CREATE TABLE silver.salesforce_contact (
    contact_id           NVARCHAR(20)    NOT NULL PRIMARY KEY,
    account_id             NVARCHAR(20)    NULL,
    first_name               NVARCHAR(100)   NULL,
    last_name                  NVARCHAR(100)   NOT NULL,
    salutation                   NVARCHAR(20)    NULL,
    full_name                      NVARCHAR(255)   NULL,
    title                             NVARCHAR(150)   NULL,
    department                          NVARCHAR(100)   NULL,
    email                                 NVARCHAR(255)   NULL,
    phone                                   NVARCHAR(50)    NULL,
    mobile_phone                             NVARCHAR(50)    NULL,
    mailing_city                               NVARCHAR(100)   NULL,
    mailing_state                                NVARCHAR(100)   NULL,
    mailing_country                                NVARCHAR(100)   NULL,
    source_created_date                              DATETIMEOFFSET  NULL,
    source_modified_date                               DATETIMEOFFSET  NULL,
    load_date                                            DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_system                                          NVARCHAR(20)    NOT NULL DEFAULT 'salesforce'
);
GO

-- Real contacts are identified by having an actual job title/department
-- (org-chart data), not by name/email/phone being populated -- Faker fills
-- those on every synthetic row regardless. is_deleted excludes Salesforce's
-- soft-deleted records.
INSERT INTO silver.salesforce_contact (
    contact_id, account_id, first_name, last_name, salutation, full_name,
    title, department, email, phone, mobile_phone,
    mailing_city, mailing_state, mailing_country,
    source_created_date, source_modified_date
)
SELECT
    id,
    account_id,
    NULLIF(LTRIM(RTRIM(first_name)), '')       AS first_name,
    LTRIM(RTRIM(last_name))                    AS last_name,
    salutation,
    LTRIM(RTRIM(name))                         AS full_name,
    NULLIF(LTRIM(RTRIM(title)), '')            AS title,
    NULLIF(LTRIM(RTRIM(department)), '')       AS department,
    NULLIF(LOWER(LTRIM(RTRIM(email))), '')     AS email,
    NULLIF(LTRIM(RTRIM(phone)), '')            AS phone,
    NULLIF(LTRIM(RTRIM(mobile_phone)), '')     AS mobile_phone,
    NULLIF(LTRIM(RTRIM(mailing_city)), '')     AS mailing_city,
    NULLIF(LTRIM(RTRIM(mailing_state)), '')    AS mailing_state,
    NULLIF(LTRIM(RTRIM(mailing_country)), '')  AS mailing_country,
    created_date,
    last_modified_date
FROM bronze.salesforce_contact
WHERE is_deleted = 0
  AND (title IS NOT NULL OR department IS NOT NULL);
GO

SELECT * FROM silver.salesforce_contact ORDER BY last_name;