"""
Test the Salesforce API connection using OAuth 2.0 Client Credentials Flow.

This confirms the Consumer Key/Secret work and that basic data can be read
before we build the full seeding script (same purpose as test_connection.py
was for Odoo).
"""

import json
import sys
import requests

CONFIG_PATH = "source/salesforce/config/salesforce_config.json"


def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Config file not found at {CONFIG_PATH}")
        print("Copy salesforce_config.example.json to salesforce_config.json "
              "and fill in your real values first.")
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
        print(f"Status code: {response.status_code}")
        print(response.text)
        sys.exit(1)
    return response.json()


def test_query(access_token, instance_url):
    query = "SELECT Id, Name, StageName, Amount FROM Opportunity LIMIT 5"
    url = f"{instance_url}/services/data/v60.0/query"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"q": query}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print("Query failed.")
        print(f"Status code: {response.status_code}")
        print(response.text)
        sys.exit(1)
    return response.json()


def main():
    config = load_config()

    print("Requesting access token...")
    token_data = get_access_token(config)
    access_token = token_data["access_token"]
    instance_url = token_data["instance_url"]
    print("Authenticated successfully.")
    print(f"Instance URL: {instance_url}")

    print("\nRunning test query on Opportunity object...")
    result = test_query(access_token, instance_url)
    total = result.get("totalSize", 0)
    print(f"Query succeeded. Opportunities found: {total}")
    for record in result.get("records", []):
        name = record.get("Name")
        stage = record.get("StageName")
        amount = record.get("Amount")
        print(f"  - {name} | Stage: {stage} | Amount: {amount}")


if __name__ == "__main__":
    main()
