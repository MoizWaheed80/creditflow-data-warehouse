# CreditFlow Project — Issues Faced & Solutions

## Odoo

### 1. Docker Desktop — "Virtualization support not detected"
**Issue:** Docker Desktop failed to start, showing a virtualization support error.
**Solution:** Enabled Hyper-V, Virtual Machine Platform, and WSL in Windows Features, ran `wsl --update`, then did a full system restart.

### 2. Odoo — "Database creation error: Access Denied"
**Issue:** Could not create a new database in Odoo; got an Access Denied error on the DB creation form.
**Solution:** Found that `odoo.conf` already had a custom `admin_passwd` set (not the literal word "admin"). Used that existing value in the Master Password field of the DB creation form.

## Excel / dlt Pipeline

### 1. `ModuleNotFoundError: No module named 'openpyxl'`
**Issue:** Running `excel_pipeline.py` in VS Code failed immediately — pandas couldn't read the Excel file because `openpyxl` wasn't installed.
**Solution:** Ran `pip install openpyxl` (and re-ran `pip install -r requirements.txt` to be safe). Root cause was VS Code's terminal using a different Python interpreter than the one the packages were originally installed into — worth checking `python -c "import sys; print(sys.executable)"` matches the interpreter VS Code has selected.

### 2. dlt `ConfigFieldMissingException` — secrets.toml "not found"
**Issue:** Pipeline failed to resolve any SQL Server credentials, even though `.dlt/secrets.toml` existed right next to the script. Error showed dlt searching in completely unrelated folders (e.g. the VS Code install directory).
**Solution:** dlt looks for `.dlt/secrets.toml` relative to the terminal's current working directory, not the script's file location. The terminal hadn't been `cd`'d into the `etl` folder before running `python excel_pipeline.py` (or was pointing at the file by full path from elsewhere). Fix: always `cd` into the folder containing the script and `.dlt` folder first, then run the script with a bare filename.

### 3. `pyodbc.OperationalError` — "target machine actively refused" connection
**Issue:** Once secrets were found, connecting to `localhost\SQLEXPRESS` still failed with a TCP connection refused error.
**Solution:** Two stacked causes, both specific to a named SQL Server Express instance:
- TCP/IP protocol was disabled for SQLEXPRESS in SQL Server Configuration Manager (SQL Express installs with only Shared Memory enabled locally by default). Enabled it under SQL Server Network Configuration -> Protocols for SQLEXPRESS.
- Named instances listen on a random dynamic port, not 1433, unless one is explicitly set. Set a fixed port by clearing "TCP Dynamic Ports" and setting "TCP Port" to `1433` under the TCP/IP protocol's IP Addresses -> IPAll section, then restarted the SQL Server (SQLEXPRESS) service for the change to take effect.

## Salesforce
No issues logged yet.

## Seed Data
No issue logged yet.

---
*Add details for the seed data issue and any Salesforce issues and I'll update this file.*
