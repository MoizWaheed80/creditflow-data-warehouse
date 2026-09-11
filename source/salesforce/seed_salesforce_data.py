
import json
import random
import statistics
import sys
from datetime import date, timedelta
 
import requests
from faker import Faker
 
CONFIG_PATH = "source/salesforce/config/salesforce_config.json"
API_VERSION = "v60.0"
 
fake = Faker()
 
# ---- Pipeline configuration -------------------------------------------------
 
STAGES = [
    "Application Received",
    "Under Review",
    "Credit Check",
    "Approved",
    "Funded",
    "Rejected",
]
 
# Realistic funnel shape: most applications sit early, fewer make it all the
# way to Funded, some drop off as Rejected.
STAGE_WEIGHTS = {
    "Application Received": 0.28,
    "Under Review": 0.22,
    "Credit Check": 0.16,
    "Approved": 0.10,
    "Funded": 0.16,
    "Rejected": 0.08,
}
 
N_CLEAN_BORROWERS = 85
N_DIRTY_BORROWERS = 10
N_CLEAN_OPPS = 115
N_DIRTY_OPPS = 15
 
DATE_WINDOW_DAYS = 150
TODAY = date(2026, 9, 12)
 
known_issues = []  # collects (record_type, identifier, issue) for the log
 
 
# ---- Config / auth -----------------------------------------------------------
 
def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Config file not found at {CONFIG_PATH}")
        sys.exit(1)
 
 
def get_access_token(config):
    token_url = f"{config['domain']}/services/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": config["consumer_key"],
        "client_secret": config["consumer_secret"],
    }
    response = requests.post(token_url, data=payload)
    if response.status_code != 200:
        print("Authentication failed.")
        print(response.text)
        sys.exit(1)
    data = response.json()
    return data["access_token"], data["instance_url"]
 
 
def sf_post(instance_url, access_token, sobject, record):
    url = f"{instance_url}/services/data/{API_VERSION}/sobjects/{sobject}/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        # Some of our seed data is intentionally duplicate (for the cleaning
        # exercise later). This tells Salesforce's built-in duplicate rules
        # to save anyway instead of blocking the request.
        "Sforce-Duplicate-Rule-Header": "allowSave=true",
    }
    response = requests.post(url, headers=headers, json=record)
    if response.status_code != 201:
        print(f"Failed to create {sobject}: {response.text}")
        sys.exit(1)
    return response.json()["id"]
 
 
# ---- Date helper (weekday-weighted, matches Odoo's seeding pattern) --------
 
def random_business_date():
    while True:
        offset = random.randint(0, DATE_WINDOW_DAYS)
        d = TODAY - timedelta(days=offset)
        # ~85% chance to keep weekdays, occasional weekend entries allowed
        if d.weekday() < 5 or random.random() < 0.15:
            return d
 
 
# ---- Borrower (Account + Contact) generation --------------------------------
 
def make_clean_borrower():
    is_business = random.random() < 0.35
    if is_business:
        name = fake.company()
        first, last = fake.first_name(), fake.last_name()
    else:
        first, last = fake.first_name(), fake.last_name()
        name = f"{first} {last}"
    return {
        "account_name": name,
        "first_name": first,
        "last_name": last,
        "email": fake.email(),
        "phone": fake.phone_number(),
        "dirty": False,
    }
 
 
def make_dirty_borrowers(clean_borrowers, count):
    dirty = []
    # 3 exact duplicates of existing clean borrowers
    for b in random.sample(clean_borrowers, 3):
        dup = dict(b)
        dirty.append(dup)
        known_issues.append(("Account", dup["account_name"],
                              "Exact duplicate of an existing borrower record"))
 
    # 2 near-duplicate names (typo/spacing variants)
    for b in random.sample(clean_borrowers, 2):
        variant = dict(b)
        variant["account_name"] = b["account_name"].replace(" ", "  ", 1) + " "
        dirty.append(variant)
        known_issues.append(("Account", variant["account_name"],
                              f"Near-duplicate of '{b['account_name']}' (spacing variant)"))
 
    # 3 missing email
    for _ in range(3):
        b = make_clean_borrower()
        b["email"] = None
        dirty.append(b)
        known_issues.append(("Contact", b["account_name"], "Missing email address"))
 
    # 2 placeholder/junk email (syntactically valid so Salesforce accepts it,
    # but semantically meaningless, exactly the kind of junk real data has)
    for placeholder in ["na@example.com", "test@test.com"]:
        b = make_clean_borrower()
        b["email"] = placeholder
        dirty.append(b)
        known_issues.append(("Contact", b["account_name"],
                              f"Placeholder/junk email: '{placeholder}'"))
 
    return dirty[:count]
 
 
def create_borrower(instance_url, access_token, borrower):
    account_id = sf_post(instance_url, access_token, "Account",
                          {"Name": borrower["account_name"]})
    contact = {
        "FirstName": borrower["first_name"],
        "LastName": borrower["last_name"],
        "AccountId": account_id,
        "Phone": borrower["phone"],
    }
    if borrower["email"]:
        contact["Email"] = borrower["email"]
    sf_post(instance_url, access_token, "Contact", contact)
    return account_id
 
 
# ---- Opportunity generation --------------------------------------------------
 
def weighted_stage():
    stages, weights = zip(*STAGE_WEIGHTS.items())
    return random.choices(stages, weights=weights, k=1)[0]
 
 
def make_clean_opportunity(account_id, account_name):
    stage = weighted_stage()
    amount = round(random.triangular(5000, 150000, 30000), 2)
    close_date = random_business_date()
    return {
        "Name": f"{account_name} - Loan Application",
        "AccountId": account_id,
        "StageName": stage,
        "Amount": amount,
        "CloseDate": close_date.isoformat(),
    }
 
 
def make_dirty_opportunities(account_pool, count):
    dirty = []
 
    # 4 missing amount
    for _ in range(4):
        acc_id, acc_name = random.choice(account_pool)
        opp = make_clean_opportunity(acc_id, acc_name)
        del opp["Amount"]
        dirty.append(opp)
        known_issues.append(("Opportunity", opp["Name"], "Missing loan amount"))
 
    # 3 outlier amount (2 unrealistically low, 1 unrealistically high)
    for outlier_amount in [250.0, 480.0, 980000.0]:
        acc_id, acc_name = random.choice(account_pool)
        opp = make_clean_opportunity(acc_id, acc_name)
        opp["Amount"] = outlier_amount
        dirty.append(opp)
        known_issues.append(("Opportunity", opp["Name"],
                              f"Outlier loan amount: {outlier_amount}"))
 
    # 3 stalled in Under Review with a stale close date (400+ days in the past)
    for _ in range(3):
        acc_id, acc_name = random.choice(account_pool)
        opp = make_clean_opportunity(acc_id, acc_name)
        opp["StageName"] = "Under Review"
        opp["CloseDate"] = (TODAY - timedelta(days=random.randint(400, 500))).isoformat()
        dirty.append(opp)
        known_issues.append(("Opportunity", opp["Name"],
                              "Stalled in Under Review with a stale close date"))
 
    # 2 vague/placeholder names
    for placeholder in ["TBD", "Test Loan"]:
        acc_id, acc_name = random.choice(account_pool)
        opp = make_clean_opportunity(acc_id, acc_name)
        opp["Name"] = placeholder
        dirty.append(opp)
        known_issues.append(("Opportunity", opp["Name"], "Vague/placeholder name"))
 
    # 2 Funded but with a future close date (logically inconsistent)
    for _ in range(2):
        acc_id, acc_name = random.choice(account_pool)
        opp = make_clean_opportunity(acc_id, acc_name)
        opp["StageName"] = "Funded"
        opp["CloseDate"] = (TODAY + timedelta(days=random.randint(30, 120))).isoformat()
        dirty.append(opp)
        known_issues.append(("Opportunity", opp["Name"],
                              "Marked Funded but CloseDate is in the future"))
 
    # 1 duplicate opportunity (same account, same amount, near-identical name)
    acc_id, acc_name = random.choice(account_pool)
    original = make_clean_opportunity(acc_id, acc_name)
    dup = dict(original)
    dup["Name"] = original["Name"] + " "
    dirty.append(original)
    dirty.append(dup)
    known_issues.append(("Opportunity", original["Name"],
                          "Duplicate opportunity entered twice for the same account"))
 
    return dirty[:count]
 
 
# ---- Main --------------------------------------------------------------------
 
def main():
    config = load_config()
    print("Requesting access token...")
    access_token, instance_url = get_access_token(config)
    print("Authenticated successfully.\n")
 
    print("Generating borrowers...")
    clean_borrowers = [make_clean_borrower() for _ in range(N_CLEAN_BORROWERS)]
    dirty_borrowers = make_dirty_borrowers(clean_borrowers, N_DIRTY_BORROWERS)
    all_borrowers = clean_borrowers + dirty_borrowers
 
    print(f"Creating {len(all_borrowers)} Accounts/Contacts in Salesforce...")
    account_pool = []  # (account_id, account_name), used for opportunities
    for i, b in enumerate(all_borrowers, 1):
        account_id = create_borrower(instance_url, access_token, b)
        account_pool.append((account_id, b["account_name"]))
        if i % 20 == 0:
            print(f"  ...{i}/{len(all_borrowers)} created")
 
    print(f"\nCreated {len(all_borrowers)} borrower records "
          f"({N_CLEAN_BORROWERS} clean, {N_DIRTY_BORROWERS} intentionally dirty).")
 
    print("\nGenerating opportunities...")
    clean_opps = []
    for _ in range(N_CLEAN_OPPS):
        acc_id, acc_name = random.choice(account_pool)
        clean_opps.append(make_clean_opportunity(acc_id, acc_name))
    dirty_opps = make_dirty_opportunities(account_pool, N_DIRTY_OPPS)
    all_opps = clean_opps + dirty_opps
    random.shuffle(all_opps)
 
    print(f"Creating {len(all_opps)} Opportunities in Salesforce...")
    for i, opp in enumerate(all_opps, 1):
        sf_post(instance_url, access_token, "Opportunity", opp)
        if i % 20 == 0:
            print(f"  ...{i}/{len(all_opps)} created")
 
    print(f"\nCreated {len(all_opps)} opportunity records "
          f"({N_CLEAN_OPPS} clean, {N_DIRTY_OPPS} intentionally dirty).")
 
    # ---- Data quality check on the clean opportunities only ----
    amounts = [o["Amount"] for o in clean_opps]
    dates_used = {o["CloseDate"] for o in clean_opps}
    weekday_count = sum(
        1 for o in clean_opps
        if date.fromisoformat(o["CloseDate"]).weekday() < 5
    )
    stage_counts = {}
    for o in clean_opps:
        stage_counts[o["StageName"]] = stage_counts.get(o["StageName"], 0) + 1
 
    print("\n=== Data Quality Check (clean records only) ===")
    print(f"Unique dates used: {len(dates_used)} across {DATE_WINDOW_DAYS}-day window")
    print(f"Weekday vs weekend split: {weekday_count} / {len(clean_opps) - weekday_count}")
    print(f"Amount range: {min(amounts):.2f} to {max(amounts):.2f}")
    print(f"Amount mean: {statistics.mean(amounts):.2f}, "
          f"std dev: {statistics.stdev(amounts):.2f}")
    print("Stage distribution:")
    for stage in STAGES:
        print(f"  {stage}: {stage_counts.get(stage, 0)}")
 
    # ---- Write known issues log ----
    with open("salesforce_seed_known_issues.md", "w") as f:
        f.write("# Salesforce Seed Data - Known Issues Log\n\n")
        f.write("Answer key for intentionally dirty records, for validating "
                "the Bronze -> Silver cleaning logic later.\n\n")
        for record_type, identifier, issue in known_issues:
            f.write(f"- **{record_type}** `{identifier}`: {issue}\n")
 
    print("\nWrote salesforce_seed_known_issues.md, move this into docs/ "
          "alongside seed_data_known_issues.md.")
 
 
if __name__ == "__main__":
    main()