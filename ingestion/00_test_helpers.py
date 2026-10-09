# Databricks notebook source
# MAGIC %md
# MAGIC # NRW-006 · Test the landing helpers
# MAGIC Lands a tiny test DataFrame through `common.write_parquet`, reads it back with Spark (the way Bronze will), then deletes it.
# MAGIC Needs `config.py` and `common.py` in the **same workspace folder** as this notebook.

# COMMAND ----------

# MAGIC %load_ext autoreload
# MAGIC %autoreload 2
# MAGIC # Re-imports config.py / common.py automatically after you edit them (otherwise Python keeps the old copy)

# COMMAND ----------

import pandas as pd

from common import write_parquet
from config import COMPANIES, PRICE_TICKERS, VOLUME_BASE

print("Volume :", VOLUME_BASE)
print("Tickers:", PRICE_TICKERS)
print("Companies:", [c["company_id"] for c in COMPANIES])

# COMMAND ----------

test_df = pd.DataFrame({
    "trade_date": pd.to_datetime(["2026-10-08", "2026-10-09"]).date,
    "ticker": ["RWE.DE", "RWE.DE"],
    "close_price": [41.10, 41.55],
})

# No leading "_" in the name: Spark treats files starting with "_" or "." as hidden and skips them
path = write_parquet(test_df, "smoke_test", source="test")

# COMMAND ----------

# Read back with Spark, as the Bronze pipeline will. This catches type problems (e.g. nanosecond timestamps) early.
back = spark.read.parquet(path)
back.printSchema()
display(back)

# COMMAND ----------

# Clean up: test folders must not stay in the landing zone
for folder in ("smoke_test", "_smoke_test"):
    dbutils.fs.rm(f"{VOLUME_BASE}/{folder}", recurse=True)
    print("cleaned up:", f"{VOLUME_BASE}/{folder}")
