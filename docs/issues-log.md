# CreditFlow Project — Issues Faced & Solutions

## Odoo
- Docker Desktop "Virtualization support not detected" -> Enabled Hyper-V, Virtual Machine Platform, and WSL in Windows Features, ran `wsl --update`, full restart.
- Odoo "Database creation error: Access Denied" -> `odoo.conf` already had a custom `admin_passwd` set (not the literal word "admin"); used that existing value in the Master Password field.
- `ModuleNotFoundError: No module named 'psycopg2'` -> `pip install psycopg2-binary`.
- Postgres connection refused from the host -> The `db` service in `docker-compose.yml` had no `ports` mapping; added `ports: ["5432:5432"]`, then `docker compose down && docker compose up -d`.
- Wrong Postgres database name assumed -> Confirmed the real name (`odoo_creditflow`) via `docker exec -it odoo-db-1 psql -U odoo -l`, updated the connection string.
- JSONB/dict columns crashing pyodbc inserts (stuck at 313/363 tables) -> Added a `make_json_safe()` helper converting dict/list-valued columns to JSON strings before insert; got to 363/363.
- `sale_order`/`sale_order_line` UndefinedTable, `product_template`/`product_product`/`account_payment` loading 0 rows -> Two causes: the Sales app was never installed (tables don't exist), and the other tables existed but were never seeded. Trimmed the final table list down to what was actually seeded: `res_partner`, `account_move`, `account_move_line`, `account_account`.

## Excel / dlt
- `ModuleNotFoundError: No module named 'openpyxl'` -> `pip install openpyxl`; root cause was VS Code's terminal using a different Python interpreter than the one packages were installed into.
- dlt `ConfigFieldMissingException`, secrets.toml "not found" -> dlt resolves `.dlt/secrets.toml` relative to the terminal's working directory, not the script's location; always `cd` into the script's folder first, then run by bare filename.
- `pyodbc.OperationalError`, connection actively refused -> SQLEXPRESS ships with TCP/IP disabled by default; enabled it, then set a static TCP port (1433) since named instances otherwise listen on a random dynamic port, restarted the service.
- `MissingDependencyException` (pyarrow) -> `pip install "dlt[parquet]"`.
- `ArrowTypeError`/`ArrowInvalid` on mixed-type columns (`Created_Date`, `Amount_Due`) -> Forced every column to load as string with `dtype=str` in `pd.read_excel(...)`, no data loss.

## Salesforce
- SOAP login disabled on the org (`INVALID_OPERATION`) -> Org has legacy SOAP-based login disabled entirely; switched auth method.
- OAuth username-password flow blocked (`invalid_grant`) -> This Salesforce release has that flow permanently disabled at the platform level; moved to Client Credentials Flow instead.
- Final auth fix -> Wrote `client_credentials_login()`: a raw `requests.post` to the OAuth token endpoint, passing the returned session/instance URL straight into the `Salesforce()` constructor. Required enabling Client Credentials Flow, a "Run As" user, and relaxed IP restrictions on the Connected App.
- `getaddrinfo failed` on the token endpoint (hit twice) -> `domain` in `secrets.toml` must be just the org's My Domain prefix (`orgfarm-...-dev-ed.develop`), not `"login"`, and without `.salesforce.com` appended (the code already appends it).
- 42/1126 objects failing every retry (`MALFORMED_QUERY`, mandatory per-record filter) -> Confirmed these are metadata/access-computation objects Salesforce computes on demand, not bulk-queryable by design. Added a `SKIP_OBJECTS` set, logged as skipped rather than failed. (Superseded: the pipeline was later scoped down to just Account/Contact/Opportunity, so this no longer applies to the current build.)

## SSIS Orchestration & Scheduling
- Execute Process Task pointed at the WindowsApps `python.exe` alias, not a real interpreter -> Repointed Executable to the actual classic-installer Python path.
- SQLEXPRESS doesn't support the SSISDB catalog or SQL Server Agent -> Installed a separate default-instance SQL Server 2025 Developer Edition just to host the catalog/Agent; the actual data stays on SQLEXPRESS.
- SSMS 22 missing the "Integration Services Catalogs" node -> Added the SSIS component via Visual Studio Installer's Modify option.
- Agent needed to run as a dedicated account, not the user's Microsoft account (couldn't reset its password locally) -> Created a local service account `svc_ssis`, set SQL Server Agent to log on as it.
- `svc_ssis` had no permission to run Python or write into the project folder -> Granted Read & execute, then Modify, on both folders. The Security-tab GUI silently failed to persist the change more than once; confirmed and fixed instead via `icacls /grant` on the command line.
- `python.exe` intermittently zeroed to 0 bytes, causing "This app can't run on your PC" / random "Access is denied" -> Re-ran the classic Python installer's Repair option, which restored the file without losing installed packages.
- Packages installed as the regular user weren't available to `svc_ssis` -> Reinstalled each one (`dlt`, `pandas`, `sqlalchemy`, `psycopg2-binary`, `pyodbc`, `simple-salesforce`, `openpyxl`, `dlt[parquet]`) as `svc_ssis` once Modify permission actually took effect; had to uninstall a misplaced per-user copy of `openpyxl` first.
- `svc_ssis` had no SQL Server login on SQLEXPRESS -> Added it as a Windows-auth login mapped to `creditflow-data-warehouse` with `db_datareader`, `db_datawriter`, `db_ddladmin`.
- SalesForce Load task failing with an opaque exit code 1 in the SSIS execution report -> Temporarily wrapped the task in `cmd.exe` with output redirected to a log file to surface the real Python traceback.
- That traceback showed `getaddrinfo failed` resolving Salesforce's hostname -> Confirmed via `nslookup` that DNS actually resolves fine under `svc_ssis`; was a one-time first-connection blip that cleared on retry, not a real fix needed.

## Seed Data
No issue logged yet.

---
*Add details for the seed data issue if one comes up.*
