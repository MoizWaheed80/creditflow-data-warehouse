import xmlrpc.client

url = "http://localhost:8069"
db = "odoo_creditflow"
username = "theclassictech@gmail.com"
password = "admin"

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
print("Odoo version info:", common.version())

uid = common.authenticate(db, username, password, {})
if not uid:
    print("Authentication failed. Check db name, username, and password.")
else:
    print("Authenticated. User ID:", uid)

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    partner_ids = models.execute_kw(
        db, uid, password,
        "res.partner", "search",
        [[]], {"limit": 5}
    )
    print("Sample partner (vendor/contact) IDs:", partner_ids)
