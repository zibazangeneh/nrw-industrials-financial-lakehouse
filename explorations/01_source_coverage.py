# Databricks notebook source
# MAGIC %md
# MAGIC # NRW-005 · Spike: do the sources cover our companies?
# MAGIC Run cell by cell. Results go into `docs/decisions/ADR-001-data-sources.md`.
# MAGIC
# MAGIC | Part | Source | Question |
# MAGIC |---|---|---|
# MAGIC | A | yfinance | Daily prices for all 5 companies + DAX? Since when? |
# MAGIC | B | Alpha Vantage | Fundamentals for German companies (XETRA or US ADR symbol)? Uses **10 of 25** daily calls |
# MAGIC | C | yfinance | Fallback fundamentals if Alpha Vantage has gaps |
# MAGIC | D | ECB Data Portal | Do both series keys return data? |

# COMMAND ----------

# MAGIC %pip install yfinance==1.7.0 -q

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## A · yfinance daily prices

# COMMAND ----------

import yfinance as yf

TICKERS = {"BASF": "BAS.DE", "Bayer": "BAYN.DE", "Siemens Energy": "ENR.DE", "E.ON": "EOAN.DE", "RWE": "RWE.DE", "DAX": "^GDAXI"}

for name, ticker in TICKERS.items():
    df = yf.Ticker(ticker).history(period="max", interval="1d", auto_adjust=False)
    if df.empty:
        print(f"❌ {name:15} {ticker:8} no data")
        continue
    print(f"✅ {name:15} {ticker:8} {df.index.min():%Y-%m-%d} → {df.index.max():%Y-%m-%d}  "
          f"rows={len(df):>6}  null_close={df['Close'].isna().sum()}  currency={yf.Ticker(ticker).fast_info.get('currency')}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## B · Alpha Vantage fundamentals for our companies
# MAGIC Tests `INCOME_STATEMENT` only (balance sheet coverage follows the same symbols). 10 calls, ~2 minutes.

# COMMAND ----------

import time
import requests

api_key = dbutils.secrets.get(scope="nrw", key="alphavantage_api_key")

AV_SYMBOLS = {
    "BASF":           ["BAS.DEX", "BASFY"],
    "Bayer":          ["BAYN.DEX", "BAYRY"],
    "Siemens Energy": ["ENR.DEX", "SMNEY"],
    "E.ON":           ["EOAN.DEX", "EONGY"],
    "RWE":            ["RWE.DEX", "RWEOY"],
}

first = True
for company, symbols in AV_SYMBOLS.items():
    for symbol in symbols:
        if not first:
            time.sleep(13)  # free tier: 5 calls/minute
        first = False
        data = requests.get("https://www.alphavantage.co/query",
                            params={"function": "INCOME_STATEMENT", "symbol": symbol, "apikey": api_key},
                            timeout=15).json()
        q = data.get("quarterlyReports") or []
        if q:
            print(f"✅ {company:15} {symbol:9} quarters={len(q):>3}  latest={q[0].get('fiscalDateEnding')}  "
                  f"currency={q[0].get('reportedCurrency')}")
        else:
            msg = next((v for k, v in data.items() if k in ("Information", "Note", "Error Message")), "empty response")
            print(f"❌ {company:15} {symbol:9} {str(msg)[:80]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## C · yfinance fundamentals (fallback)

# COMMAND ----------

for name, ticker in list(TICKERS.items())[:5]:  # skip the DAX index
    t = yf.Ticker(ticker)
    inc, bal = t.quarterly_income_stmt, t.quarterly_balance_sheet
    has = [k for k in ("Total Revenue", "Operating Income", "Net Income") if k in inc.index]
    print(f"{name:15} income quarters={inc.shape[1]:>2}  balance quarters={bal.shape[1]:>2}  "
          f"latest={inc.columns.max():%Y-%m-%d}  rows found={has}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## D · ECB Data Portal series

# COMMAND ----------

import io
import pandas as pd

ECB_SERIES = {
    "EUR/USD reference rate": "EXR/D.USD.EUR.SP00.A",
    "Deposit facility rate":  "FM/D.U2.EUR.4F.KR.DFR.LEV",
}

for name, key in ECB_SERIES.items():
    r = requests.get(f"https://data-api.ecb.europa.eu/service/data/{key}",
                     params={"format": "csvdata", "startPeriod": "2015-01-01"}, timeout=30)
    if r.status_code != 200:
        print(f"❌ {name:24} {key:28} HTTP {r.status_code}")
        continue
    df = pd.read_csv(io.StringIO(r.text))
    print(f"✅ {name:24} {key:28} {df['TIME_PERIOD'].min()} → {df['TIME_PERIOD'].max()}  "
          f"rows={len(df)}  latest={df['OBS_VALUE'].iloc[-1]}")
