# Databricks notebook source
# MAGIC %md
# MAGIC # NRW-004/005 · Which Alpha Vantage endpoints does our free key unlock?
# MAGIC `OVERVIEW` returned "This is a premium endpoint". This tests each endpoint we planned to use, plus two
# MAGIC endpoints the docs mark as free, to tell "key problem" apart from "endpoint is premium".
# MAGIC
# MAGIC Uses **5 of the 25 free requests/day**, spaced 13 s apart (limit: 5/minute).

# COMMAND ----------

import time
import requests

api_key = dbutils.secrets.get(scope="nrw", key="alphavantage_api_key")

tests = [
    ("GLOBAL_QUOTE (free per docs)",      {"function": "GLOBAL_QUOTE", "symbol": "IBM"}),
    ("TIME_SERIES_DAILY (free per docs)", {"function": "TIME_SERIES_DAILY", "symbol": "IBM"}),
    ("OVERVIEW",                          {"function": "OVERVIEW", "symbol": "IBM"}),
    ("INCOME_STATEMENT",                  {"function": "INCOME_STATEMENT", "symbol": "IBM"}),
    ("BALANCE_SHEET",                     {"function": "BALANCE_SHEET", "symbol": "IBM"}),
]

# Alpha Vantage answers HTTP 200 even on errors; the message keys tell us what really happened
ERROR_KEYS = ("Information", "Note", "Error Message")

for i, (name, params) in enumerate(tests):
    if i:
        time.sleep(13)
    data = requests.get("https://www.alphavantage.co/query", params={**params, "apikey": api_key}, timeout=15).json()
    errors = {k: v for k, v in data.items() if k in ERROR_KEYS}
    if errors:
        msg = next(iter(errors.values()))
        verdict = "PREMIUM" if "premium" in msg.lower() else "RATE LIMIT" if "rate limit" in msg.lower() else "ERROR"
        print(f"❌ {name:34} {verdict}: {msg[:90]}")
    else:
        print(f"✅ {name:34} OK (keys: {', '.join(list(data)[:3])})")
