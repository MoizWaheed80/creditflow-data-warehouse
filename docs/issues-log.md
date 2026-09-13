# CreditFlow Project — Issues Faced & Solutions

## Odoo

### 1. Docker Desktop — "Virtualization support not detected"
**Issue:** Docker Desktop failed to start, showing a virtualization support error.
**Solution:** Enabled Hyper-V, Virtual Machine Platform, and WSL in Windows Features, ran `wsl --update`, then did a full system restart.

### 2. Odoo — "Database creation error: Access Denied"
**Issue:** Could not create a new database in Odoo; got an Access Denied error on the DB creation form.
**Solution:** Found that `odoo.conf` already had a custom `admin_passwd` set (not the literal word "admin"). Used that existing value in the Master Password field of the DB creation form.

## Salesforce
No issues logged yet.

## Seed Data
No issue logged yet.

---
*Add details for the seed data issue and any Salesforce issues and I'll update this file.*
