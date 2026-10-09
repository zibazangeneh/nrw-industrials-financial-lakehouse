-- NRW-003: Unity Catalog objects for the NRW Industrials Financial Lakehouse.
-- Idempotent: safe to re-run. Run in the Databricks SQL Editor (Serverless Starter Warehouse).

CREATE CATALOG IF NOT EXISTS nrw_fin
  COMMENT 'NRW Industrials Financial Lakehouse: market data for BASF, Bayer, Siemens Energy, E.ON, RWE + DAX benchmark';

USE CATALOG nrw_fin;

CREATE SCHEMA IF NOT EXISTS landing
  COMMENT 'Raw source files landed by ingestion scripts (Phase 1) or ADF (Phase 2). Files only, no tables.';

CREATE SCHEMA IF NOT EXISTS bronze
  COMMENT 'Raw-but-typed tables loaded by the Lakeflow Declarative Pipeline from the landing Volume, with expectations.';

CREATE SCHEMA IF NOT EXISTS silver
  COMMENT 'Data Vault 2.0: hubs, links and satellites (SCD2 for fundamentals).';

CREATE SCHEMA IF NOT EXISTS gold
  COMMENT 'Star schema: facts and dimensions for Databricks SQL and Genie.';

CREATE VOLUME IF NOT EXISTS landing.raw
  COMMENT 'Landing zone for raw files: /prices, /fundamentals/<endpoint>, /macro/<series>. Append-only, never overwritten.';

-- Verify
SHOW SCHEMAS IN nrw_fin;
SHOW VOLUMES IN nrw_fin.landing;
