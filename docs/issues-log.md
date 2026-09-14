# CreditFlow Project — Issues Faced & Solutions

## Odoo

### 1. Docker Desktop — "Virtualization support not detected"
**Issue:** Docker Desktop failed to start, showing a virtualization support error.
**Solution:** Enabled Hyper-V, Virtual Machine Platform, and WSL in Windows Features, ran `wsl --update`, then did a full system restart.

### 2. Odoo — "Database creation error: Access Denied"
**Issue:** Could not create a new database in Odoo; got an Access Denied error on the DB creation form.
**Solution:** Found that `odoo.conf` already had a custom `admin_passwd` set (not the literal word "admin"). Used that existing value in the Master Password field of the DB creation form.

### 3. `ModuleNotFoundError: No module named 'psycopg2'`
**Issue:** `odoo_direct_load.py` failed immediately on import — no Postgres driver installed.
**Solution:** `pip install psycopg2-binary`.

### 4. Postgres connection refused from the host
**Issue:** The direct-load script couldn't reach Odoo's Postgres database at all — connection refused on port 5432.
**Solution:** The `db` service in `docker-compose.yml` had no `ports` mapping, so Postgres was only reachable from other containers, not from the host. Added `ports: ["5432:5432"]` to the `db` service, then `docker compose down && docker compose up -d` to apply.

### 5. Wrong Postgres database name assumed
**Issue:** Script connected to Postgres fine but failed to find any Odoo tables — was pointed at a guessed database name (`CreditFlow_2026_dev`) that didn't exist.
**Solution:** Confirmed the real database name by running `docker exec -it odoo-db-1 psql -U odoo -l` inside the container. Actual name was `odoo_creditflow`. Updated the connection string accordingly.

### 6. JSONB/dict columns crashing pyodbc inserts
**Issue:** Bulk load was silently dropping tables — ended at 313/363 tables loaded, with translated-field tables (Odoo stores multi-language fields like `name={'en_US': 'Dollars'}`) failing. pyodbc can't bind a raw Python dict or list as a parameter.
**Solution:** Added a `make_json_safe()` helper that converts any dict/list-valued column to a JSON string before the SQL Server insert. This was the fix that took the run from 313/363 to a full **363/363 tables loaded**.

### 7. Scoping the direct-load table list — nonexistent and empty tables
**Issue:** After narrowing `odoo_direct_load.py` down from all 363 tables to just the ones actually needed, `sale_order` and `sale_order_line` failed with `psycopg2.errors.UndefinedTable` (relation does not exist), while `product_template`, `product_product`, and `account_payment` ran fine but loaded 0 rows.
**Solution:** Two different causes. `UndefinedTable` meant the Sales app was never installed in Odoo, those tables only get created when that module is installed, not something fixable client-side. The 0-row tables existed but were never seeded, the seed script created vendor bills directly via `account.move`/`account.move.line` without linking products or recording payments. Final table list trimmed to what was actually seeded: `res_partner`, `account_move`, `account_move_line`, plus `account_account` (not seeded, but pulled in raw anyway since bill lines reference it via `account_id`, resolved as a join during the warehouse build rather than filtered out at ingestion).

## Excel / dlt Pipeline

### 1. `ModuleNotFoundError: No module named 'openpyxl'`
**Issue:** Running `excel_pipeline.py` in VS Code failed immediately — pandas couldn't read the Excel file because `openpyxl` wasn't installed.
**Solution:** Ran `pip install openpyxl` (and re-ran `pip install -r requirements.txt` to be safe). Root cause was VS Code's terminal using a different Python interpreter than the one the packages were originally installed into — worth checking `python -c "import sys; print(sys.executable)"` matches the interpreter VS Code has selected.

### 2. dlt `ConfigFieldMissingException` — secrets.toml "not found"
**Issue:** Pipeline failed to resolve any SQL Server credentials, even though `.dlt/secrets.toml` existed right next to the script. Error showed dlt searching in completely unrelated folders (e.g. the VS Code install directory).
**Solution:** dlt looks for `.dlt/secrets.toml` relative to the terminal's current working directory, not the script's file location. The terminal hadn't been `cd`'d into the `etl` folder before running `python excel_pipeline.py` (or was pointing at the file by full path from elsewhere). Fix: always `cd` into the folder containing the script and `.dlt` folder first, then run the script with a bare filename. This recurred multiple times across all three pipelines, not just Excel.

### 3. `pyodbc.OperationalError` — "target machine actively refused" connection
**Issue:** Once secrets were found, connecting to `localhost\SQLEXPRESS` still failed with a TCP connection refused error. This blocked all three pipelines, not just Excel, since they all write to the same SQL Server instance.
**Solution:** Two stacked causes, both specific to a named SQL Server Express instance:
- TCP/IP protocol was disabled for SQLEXPRESS in SQL Server Configuration Manager (SQL Express installs with only Shared Memory enabled locally by default). Enabled it under SQL Server Network Configuration -> Protocols for SQLEXPRESS.
- Named instances listen on a random dynamic port, not 1433, unless one is explicitly set. Set a fixed port by clearing "TCP Dynamic Ports" and setting "TCP Port" to `1433` under the TCP/IP protocol's IP Addresses -> IPAll section, then restarted the SQL Server (SQLEXPRESS) service for the change to take effect.

### 4. `MissingDependencyException` — pyarrow not installed
**Issue:** Pipeline failed at `step=extract` for every sheet with `dlt.common.exceptions.MissingDependencyException`, requiring pyarrow to load pandas DataFrames.
**Solution:** `pip install "dlt[parquet]"`.

### 5. `ArrowTypeError` / `ArrowInvalid` — mixed data types within a column
**Issue:** Two sheets failed to load even after pyarrow was installed. `SF_Accounts` failed on `Created_Date` (mix of real dates and text in the same column), `Odoo_Invoices` failed on `Amount_Due` (mix of numbers and comma-formatted strings like `'2,188,447'`). pyarrow can't infer one consistent type per column when the values are inconsistent.
**Solution:** Forced every column to load as string on ingest with `dtype=str` in the `pd.read_excel(...)` call. Keeps it a raw pass-through (no data loss/transformation), just stops pyarrow from guessing a type and choking on the mix. All 9 sheets loaded successfully after this.

## Salesforce

### 1. SOAP login disabled on the org
**Issue:** Original design used simple-salesforce's default login (SOAP, username + password + security token). Failed with `INVALID_OPERATION`.
**Solution:** Investigated and found the org has legacy SOAP-based login disabled entirely — not fixable client-side. Had to switch authentication approach.

### 2. OAuth username-password flow blocked
**Issue:** Switched to the OAuth 2.0 username-password (resource owner) flow — omitting `security_token` and concatenating it into the password instead. Failed with `invalid_grant`.
**Solution:** This org (Summer '23+ Salesforce release) has the username-password OAuth flow permanently disabled/greyed out under Setup → OAuth and OpenID Connect Settings — a platform-level default, not something fixable via Connected App config. Had to move to a third auth method.

### 3. Final fix — OAuth 2.0 Client Credentials Flow
**Solution:** Wrote a `client_credentials_login()` function that does a raw `requests.post` to `https://{domain}.salesforce.com/services/oauth2/token` with `grant_type=client_credentials`, then passes the returned `session_id`/`instance_url` straight into the `Salesforce()` constructor — bypassing simple-salesforce's built-in login entirely. Required Salesforce-side setup before it would work:
- Enabled "Enable Client Credentials Flow" on the Connected App (Setup → App Manager → Edit)
- Set a "Run As" user under Edit Policies → OAuth Policies
- Set IP Relaxation to "Relax IP restrictions"

### 4. `secrets.toml` domain field gotcha
**Issue:** `getaddrinfo failed` — DNS resolution failure on the token endpoint, hit twice.
**Solution:** The `domain` field must be the org's My Domain only (e.g. `orgfarm-568b3bcb1a-dev-ed.develop.my`) — not the literal string `"login"`, and not with `.salesforce.com` appended, since the code already appends that suffix. Appending it twice broke DNS resolution both times it was tried.

### 5. 42 objects can't be bulk-queried, by design
**Issue:** First full run finished at 1084/1126 objects loaded, with 42 objects failing on every attempt regardless of retry logic — errors like `MALFORMED_QUERY: a filter on a reified column is required` and `Implementation restriction: ... requires a filter by a single Id`.
**Solution:** Confirmed via Salesforce's own docs and a real open-source Salesforce connector's exclusion list that these are metadata/access-computation objects (`UserFieldAccess`, `EntityParticle`, `Vote`, `SearchLayout`, etc.) that Salesforce computes per-record on demand rather than stores as bulk-exportable data — no SOQL shape can query them without knowing a specific ID/user/field in advance, so no generic dynamic pipeline can pull them. This isn't a bug; it's a hard platform ceiling. Added a `SKIP_OBJECTS` set so these are skipped up front (saving the wasted `describe()` API call too) and logged as "skipped (known unsupported)" rather than counted as failures. Final run: **1084 loaded, 42 skipped (known unsupported), 0 failed**, exit code 0.

## Seed Data
No issue logged yet.

---
*Add details for the seed data issue if one comes up.*
