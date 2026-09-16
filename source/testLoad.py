import json, xmlrpc.client, requests

# Turn on docker
#DELETE FROM bronze.odoo_res_partner WHERE name LIKE 'TEST_%';
#DELETE FROM bronze.salesforce_contact WHERE last_name LIKE 'TEST_%';


# ==== EDIT THESE TWO LINES BEFORE RUNNING ====
ODOO_TEST_ID = "AcmeCorp"        # <-- test record name to create in Odoo
SALESFORCE_TEST_ID = "AcmeCorp"  # <-- test record name to create in Salesforce
# ==============================================

# ---- Odoo ----
url = "http://localhost:8069"
db = "odoo_creditflow"
user = "theclassictech@gmail.com"
password = "admin"  

uid = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common").authenticate(db, user, password, {})
print("uid:", uid)  # if this prints False, your password/db/user is wrong
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
partner_id = models.execute_kw(db, uid, password, "res.partner", "create", [{"name": f"TEST_{ODOO_TEST_ID}"}])
print("Odoo id:", partner_id)

# ---- Salesforce (reads your existing config file, no extra credentials needed here) ----
config = json.load(open(r"C:\Users\thecl\OneDrive\Desktop\creditflow-data-warehouse\source\salesforce\config\salesforce_config.json"))
token = requests.post(f"{config['domain']}/services/oauth2/token", data={
    "grant_type": "client_credentials",
    "client_id": config["consumer_key"],
    "client_secret": config["consumer_secret"],
}).json()
contact = requests.post(
    f"{token['instance_url']}/services/data/v60.0/sobjects/Contact/",
    headers={"Authorization": f"Bearer {token['access_token']}"},
    json={"LastName": f"TEST_{SALESFORCE_TEST_ID}"},
).json()
print("Salesforce id:", contact["id"])