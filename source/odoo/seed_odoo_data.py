import xmlrpc.client
import random
from collections import Counter
from datetime import datetime, timedelta
from statistics import mean, pstdev

# Update these to match your setup
url = "http://localhost:8069"
db = "odoo_creditflow"
username = "theclassictech@gmail.com"
password = "admin"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})
if not uid:
    raise SystemExit("Authentication failed, check db/username/password.")

models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")


def call(model, method, args=None, kwargs=None):
    return models.execute_kw(db, uid, password, model, method, args or [], kwargs or {})


today = datetime.today()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATE_RANGE_DAYS = 150          # ~5 months, denser and more natural than a full year
CLEAN_BILLS = 180
DUPLICATE_BILLS = 6
OUTLIER_BILLS = 5
DRAFT_ONLY_BILLS = 4
VAGUE_DESCRIPTION_BILLS = 3
FUTURE_DATED_BILLS = 1
NEAR_DUPLICATE_VENDOR_BILLS = 3

OUTLIER_AMOUNTS = [75000.00, 68000.00, 1.00, 3.50, 62000.00]
VAGUE_DESCRIPTIONS = ["misc", "TBD", "n/a", "asdf test"]
LINE_DESCRIPTIONS = [
    "Inventory restocking", "Equipment maintenance", "Branch utilities",
    "Logistics and freight", "Office supplies", "Marketing services",
    "Facility repairs", "IT and software services",
]

# ---------------------------------------------------------------------------
# 1. Clean vendors
# ---------------------------------------------------------------------------
vendor_names = [
    "Northgate Supplies Co", "Palmview Logistics", "BrightPath Vendors",
    "Solstice Trading LLC", "Ironclad Distributors", "Meridian Wholesale",
    "Crestline Materials", "Harborview Freight", "Aspen Ridge Suppliers",
    "Wavecrest Equipment",
]

vendor_ids = []
for name in vendor_names:
    existing = call("res.partner", "search", [[["name", "=", name]]])
    vendor_ids.append(existing[0] if existing else call("res.partner", "create", [{"name": name, "supplier_rank": 1}]))

print(f"Clean vendors ready: {vendor_ids}")

# 2. Deliberately near-duplicate vendors (simulates messy vendor master data)
dirty_vendor_names = ["meridian wholesale ", "Northgate Supplies Co."]  # subtle case/space/punctuation diffs
dirty_vendor_ids = []
for name in dirty_vendor_names:
    existing = call("res.partner", "search", [[["name", "=", name]]])
    dirty_vendor_ids.append(existing[0] if existing else call("res.partner", "create", [{"name": name, "supplier_rank": 1}]))

print(f"Near-duplicate vendors (intentional): {dirty_vendor_ids} -> {dirty_vendor_names}")

# ---------------------------------------------------------------------------
# 3. Expense account
# ---------------------------------------------------------------------------
expense_accounts = call("account.account", "search_read",
                         [[["account_type", "=", "expense"]]], {"fields": ["id", "name"], "limit": 1})
if not expense_accounts:
    expense_accounts = call("account.account", "search_read",
                             [[["name", "ilike", "expense"]]], {"fields": ["id", "name"], "limit": 1})
if not expense_accounts:
    raise SystemExit("No expense account found, check the installed chart of accounts.")

expense_account_id = expense_accounts[0]["id"]
print(f"Using expense account: {expense_accounts[0]['name']} (id {expense_account_id})")


def create_bill(vendor_id, date_str, amount, description):
    return call("account.move", "create", [{
        "move_type": "in_invoice",
        "partner_id": vendor_id,
        "invoice_date": date_str,
        "invoice_line_ids": [(0, 0, {
            "name": description, "quantity": 1,
            "price_unit": amount, "account_id": expense_account_id,
        })],
    }])


def pick_business_date(range_days):
    """Weighted toward weekdays, occasional weekend, like real accounting entries."""
    for _ in range(20):
        d = today - timedelta(days=random.randint(1, range_days))
        if d.weekday() < 5 or random.random() < 0.12:
            return d
    return d


# ---------------------------------------------------------------------------
# 4. Clean bills, multiple-per-day allowed naturally, no artificial forcing
# ---------------------------------------------------------------------------
clean_bills = []  # (id, date, amount, vendor_id, description)
to_post = []

for _ in range(CLEAN_BILLS):
    vendor_id = random.choice(vendor_ids)
    d = pick_business_date(DATE_RANGE_DAYS)
    date_str = d.strftime("%Y-%m-%d")
    amount = round(random.uniform(150, 5000), 2)
    description = random.choice(LINE_DESCRIPTIONS)
    bill_id = create_bill(vendor_id, date_str, amount, description)
    clean_bills.append((bill_id, date_str, amount, vendor_id, description))
    to_post.append(bill_id)

print(f"\nCreated {len(clean_bills)} clean vendor bills.")

# ---------------------------------------------------------------------------
# 5. Intentionally dirty data, logged as it's created
# ---------------------------------------------------------------------------
issues = {"duplicates": [], "outliers": [], "draft_only": [], "vague_description": [],
          "future_dated": [], "near_duplicate_vendor": [], "failed": []}

try:
    # 5a. Exact duplicate bills (accidental double entry)
    for orig_id, orig_date, orig_amount, orig_vendor, orig_desc in random.sample(clean_bills, DUPLICATE_BILLS):
        dup_id = create_bill(orig_vendor, orig_date, orig_amount, orig_desc)
        to_post.append(dup_id)
        issues["duplicates"].append({"original_id": orig_id, "duplicate_id": dup_id, "date": orig_date, "amount": orig_amount})

    # 5b. Outlier amounts (typo-style: missing/extra decimal, data entry errors)
    for amount in OUTLIER_AMOUNTS[:OUTLIER_BILLS]:
        vendor_id = random.choice(vendor_ids)
        d = pick_business_date(DATE_RANGE_DAYS)
        bill_id = create_bill(vendor_id, d.strftime("%Y-%m-%d"), amount, random.choice(LINE_DESCRIPTIONS))
        to_post.append(bill_id)
        issues["outliers"].append({"id": bill_id, "amount": amount})

    # 5c. Draft-only bills (incomplete real-world records, never finalized)
    for _ in range(DRAFT_ONLY_BILLS):
        vendor_id = random.choice(vendor_ids)
        d = pick_business_date(DATE_RANGE_DAYS)
        bill_id = create_bill(vendor_id, d.strftime("%Y-%m-%d"), round(random.uniform(150, 5000), 2), random.choice(LINE_DESCRIPTIONS))
        issues["draft_only"].append({"id": bill_id})  # deliberately NOT added to to_post

    # 5d. Vague/junk line descriptions (needs text cleaning)
    for _ in range(VAGUE_DESCRIPTION_BILLS):
        vendor_id = random.choice(vendor_ids)
        d = pick_business_date(DATE_RANGE_DAYS)
        desc = random.choice(VAGUE_DESCRIPTIONS)
        bill_id = create_bill(vendor_id, d.strftime("%Y-%m-%d"), round(random.uniform(150, 5000), 2), desc)
        to_post.append(bill_id)
        issues["vague_description"].append({"id": bill_id, "description": desc})

    # 5e. Future-dated bill (data entry error)
    for _ in range(FUTURE_DATED_BILLS):
        vendor_id = random.choice(vendor_ids)
        future_date = (today + timedelta(days=20)).strftime("%Y-%m-%d")
        bill_id = create_bill(vendor_id, future_date, round(random.uniform(150, 5000), 2), random.choice(LINE_DESCRIPTIONS))
        to_post.append(bill_id)
        issues["future_dated"].append({"id": bill_id, "date": future_date})

    # 5f. Bills against the near-duplicate vendor records (vendor master data problem)
    for _ in range(NEAR_DUPLICATE_VENDOR_BILLS):
        vendor_id = random.choice(dirty_vendor_ids)
        d = pick_business_date(DATE_RANGE_DAYS)
        bill_id = create_bill(vendor_id, d.strftime("%Y-%m-%d"), round(random.uniform(150, 5000), 2), random.choice(LINE_DESCRIPTIONS))
        to_post.append(bill_id)
        issues["near_duplicate_vendor"].append({"id": bill_id, "vendor_id": vendor_id})

except Exception as e:
    issues["failed"].append(str(e))
    print(f"NOTE: one of the dirty-data injections was rejected by Odoo: {e}")

call("account.move", "action_post", [to_post])
print(f"Posted {len(to_post)} bills ({DRAFT_ONLY_BILLS} left in draft on purpose).")

total_records = len(clean_bills) + sum(len(v) for k, v in issues.items() if k != "failed")
print(f"\nTotal vendor bill records created: {total_records}")

# ---------------------------------------------------------------------------
# 6. Quality report on the CLEAN data (dirty data is supposed to look off)
# ---------------------------------------------------------------------------
print("\n=== Data Quality Check (clean records only) ===")
dates = [b[1] for b in clean_bills]
amounts = [b[2] for b in clean_bills]
date_counts = Counter(dates)

print(f"Unique dates used: {len(date_counts)} across {DATE_RANGE_DAYS}-day window")
weekday_count = sum(1 for d in dates if datetime.strptime(d, "%Y-%m-%d").weekday() < 5)
print(f"Weekday vs weekend split: {weekday_count} weekday / {len(dates) - weekday_count} weekend")
print("Busiest days (top 5):", date_counts.most_common(5))
print(f"Amount range: {min(amounts):.2f} to {max(amounts):.2f}")
print(f"Amount mean: {mean(amounts):.2f}, std dev: {pstdev(amounts):.2f}")

# ---------------------------------------------------------------------------
# 7. Write a known-issues log, this is your answer key for the Silver-layer cleaning step
# ---------------------------------------------------------------------------
with open("seed_data_known_issues.md", "w") as f:
    f.write("# CreditFlow Seed Data: Known Issues (intentionally injected)\n\n")
    f.write("These records were deliberately seeded as dirty data to give the Bronze-to-Silver\n")
    f.write("transformation layer real problems to catch and document.\n\n")
    for category, records in issues.items():
        if category == "failed":
            continue
        f.write(f"## {category.replace('_', ' ').title()} ({len(records)})\n")
        for r in records:
            f.write(f"- {r}\n")
        f.write("\n")
    if issues["failed"]:
        f.write("## Injection failures\n")
        for msg in issues["failed"]:
            f.write(f"- {msg}\n")

print("\nWrote seed_data_known_issues.md, move this into docs/ and reference it when you build the QA/cleaning step.")
