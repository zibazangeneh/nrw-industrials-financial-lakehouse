# Databricks notebook source
# MAGIC %md
# MAGIC # NRW-007 · Pull daily prices (yfinance) → landing Volume
# MAGIC - **backfill**: everything since `start` (default 2018-01-01, ADR-001)
# MAGIC - **incremental**: the last 10 days (overlap is fine, Silver dedupes)
# MAGIC
# MAGIC Lands **one Parquet file per run** in `/Volumes/nrw_fin/landing/raw/prices/`.
# MAGIC If a ticker returns nothing, the others are still landed, then the notebook fails so the problem is visible.

# COMMAND ----------

# MAGIC %pip install yfinance==1.7.0 -q

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %load_ext autoreload
# MAGIC %autoreload 2

# COMMAND ----------

import json
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from common import write_parquet
from config import BACKFILL_START, INCREMENTAL_DAYS, PRICE_TICKERS

# Widgets = notebook parameters. A job (NRW-010/027) passes them; when run by hand, set them in the bar at the top.
# Default is incremental, so a scheduled run without parameters can never re-land 8 years of history.
dbutils.widgets.dropdown("mode", "incremental", ["backfill", "incremental"])
dbutils.widgets.text("start", BACKFILL_START)

mode = dbutils.widgets.get("mode")
start = dbutils.widgets.get("start") if mode == "backfill" else str(date.today() - timedelta(days=INCREMENTAL_DAYS))
print(f"mode={mode}  start={start}  tickers={PRICE_TICKERS}")

# COMMAND ----------

# yfinance column → our column. Dividends / Stock Splits are dropped.
COLUMNS = {"Open": "open", "High": "high", "Low": "low", "Close": "close_price", "Adj Close": "adj_close", "Volume": "volume"}

frames, failed = [], {}
for ticker in PRICE_TICKERS:
    try:
        hist = yf.Ticker(ticker).history(start=start, interval="1d", auto_adjust=False)
    except Exception as e:
        failed[ticker] = f"{type(e).__name__}: {e}"
        continue
    if hist.empty:  # unknown or delisted tickers come back empty instead of raising
        failed[ticker] = "no rows returned"
        continue
    df = (
        hist.reindex(columns=list(COLUMNS)).rename(columns=COLUMNS)
        .assign(trade_date=hist.index.date, ticker=ticker)  # index is exchange-local (Europe/Berlin) → local trading date
        .reset_index(drop=True)
    )
    frames.append(df[["trade_date", "ticker", *COLUMNS.values()]])
    print(f"✅ {ticker:8} {len(df):>5} rows  {df.trade_date.min()} → {df.trade_date.max()}")

for ticker, reason in failed.items():
    print(f"❌ {ticker:8} {reason}")

# COMMAND ----------

if frames:
    prices = pd.concat(frames, ignore_index=True)
    path = write_parquet(prices, "prices", source="yfinance")
    display(prices.groupby("ticker").agg(rows=("trade_date", "size"), first=("trade_date", "min"), last=("trade_date", "max")).reset_index())

# COMMAND ----------

if failed:
    raise RuntimeError(f"{len(failed)} ticker(s) failed (the others were landed): {failed}")

# Returned to the caller when run from another notebook or a job (NRW-010)
dbutils.notebook.exit(json.dumps({"mode": mode, "start": start, "rows": len(prices), "file": path}))
