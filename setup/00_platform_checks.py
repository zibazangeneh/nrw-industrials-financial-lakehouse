# Databricks notebook source
# MAGIC %md
# MAGIC # NRW-002 · Platform checks (Free Edition)
# MAGIC Can serverless compute reach our three data sources? The answer decides where ingestion runs:
# MAGIC - **reachable** → pull scripts can run inside Databricks and write straight to the Volume
# MAGIC - **blocked** → pull scripts run locally and upload files to the Volume

# COMMAND ----------

# Who am I, and what am I running on?
print("user :", spark.sql("SELECT current_user()").first()[0])
print("spark:", spark.version)

# COMMAND ----------

import requests

urls = {
    "yahoo": "https://query1.finance.yahoo.com/v8/finance/chart/RWE.DE?range=5d&interval=1d",
    "ecb": "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?lastNObservations=1&format=csvdata",
    "alphavantage": "https://www.alphavantage.co/query?function=OVERVIEW&symbol=IBM&apikey=demo",
}

# Any HTTP status (even 4xx) means the host is reachable; an exception means the network blocked it.
for name, url in urls.items():
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        print(f"{name:13} reachable  (HTTP {r.status_code})")
    except Exception as e:
        print(f"{name:13} BLOCKED    {type(e).__name__}: {e}")
