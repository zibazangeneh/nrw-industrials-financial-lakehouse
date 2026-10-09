# Databricks notebook source
# MAGIC %md
# MAGIC # NRW-004 · Check the Alpha Vantage secret
# MAGIC The key is stored in the Databricks secret scope `nrw`. It must never be printed, hardcoded or committed.

# COMMAND ----------

# Databricks redacts secret values in notebook output: this should print [REDACTED]
api_key = dbutils.secrets.get(scope="nrw", key="alphavantage_api_key")
print(api_key)

# COMMAND ----------

import requests

# One real call with our key (uses 1 of the 25 free requests/day)
r = requests.get(
    "https://www.alphavantage.co/query",
    params={"function": "INCOME_STATEMENT", "symbol": "IBM", "apikey": api_key},  # OVERVIEW is premium
    timeout=15,
)
data = r.json()

# Alpha Vantage returns HTTP 200 even for errors, so check the body instead of the status code
if "quarterlyReports" in data:
    print("✅ key works:", data["symbol"], "-", len(data["quarterlyReports"]), "quarterly reports")
else:
    print("❌ no data returned:", {k: v for k, v in data.items() if k in ("Note", "Information", "Error Message")})
