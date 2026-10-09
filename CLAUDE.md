# CLAUDE.md — NRW Industrials Financial Lakehouse (Databricks-first build)

Context file for Claude Code continuity across sessions on this project.

## Project

A financial intelligence lakehouse on real market data for actual NRW target companies (BASF, Bayer, Siemens Energy, E.ON, RWE) plus the DAX index as benchmark. Third portfolio project, distinct from the other two:

- `smart-grid-stream` — Kafka / streaming-heavy
- `insureflow-analytics` — Databricks + MLflow / MLOps-heavy
- `nrw-industrials-financial-lakehouse` (this project) — Lakeflow Declarative Pipelines + Unity Catalog governance + modern batch modeling, no streaming or ML

**Build order: Databricks-only first, ADF second.** Originally scoped with ADF doing the ingestion trigger, but to move fast, Phase 1 gets the whole Databricks side working end-to-end with a plain Python script landing files in a Unity Catalog Volume. ADF gets bolted on in Phase 2 to replace that manual landing step with a real orchestrated trigger. This means there's a fully working, demo-able pipeline after Phase 1, instead of everything blocked on ADF setup first.

## Architecture (Phase 1 — Databricks only)

```
Python script (local or notebook)
   pulls yfinance / Alpha Vantage / ECB SDW
        |
Unity Catalog Volume  -- raw files land here (CSV/Parquet/JSON)
        |
[ Unity Catalog governed lakehouse ]
   Bronze   -- Lakeflow Declarative Pipeline, read_files() / Auto Loader, expectations
   Silver   -- Data Vault 2.0 (hubs, links, satellites), MERGE-based SCD2 for fundamentals
   Gold     -- star schema (facts, dimensions)
        |
Genie / Databricks SQL  -- natural-language BI layer
```

## Architecture (Phase 2 — add ADF)

Replace the manual Python landing step with:
- ADF trigger -> Databricks job/notebook task for the yfinance pull
- ADF REST activities for Alpha Vantage and ECB SDW (both are plain REST APIs, no wrapper library needed)
- Everything downstream (Bronze/Silver/Gold/Genie) stays the same — ADF only changes how data arrives in the Volume

## Data sources

- **yfinance** — daily OHLCV price history for target tickers + `^GDAXI` (DAX). No API key, no meaningful rate limit. Unofficial Yahoo wrapper — can break if Yahoo changes something; note this trade-off in the README rather than treating a break as a bug.
- **Alpha Vantage** — company fundamentals via `INCOME_STATEMENT`, `BALANCE_SHEET`. (`OVERVIEW` turned out to be a **premium** endpoint on the free tier, so it was dropped; static company attributes come from a `ref_company` seed instead.) Free tier: **25 requests/day, 5/minute**: 2 endpoints × 5 companies = 10 calls per pull. Pull weekly, not daily. Requires a free API key, stored in the Databricks secret scope `nrw` (`alphavantage_api_key`) and never hardcoded.
- **ECB Statistical Data Warehouse (SDW) API** — EUR/USD rate, ECB deposit rate. Free, no key.

## Data model

**Silver — Data Vault 2.0**
- `hub_company`, `hub_security`
- `link_company_security`
- `sat_company_fundamentals` — slowly changing (revenue, margins). Loaded with a MERGE pattern so a new quarterly pull only inserts a new satellite row when values actually changed (same idea as the CDC `operation` breakdown pattern from the dbdemos bike tutorial, just applied to a non-CDC source).
- `sat_price_daily`

**Gold — star schema**
- `fact_daily_price`
- `fact_quarterly_financials`
- `dim_company`
- `dim_date`
- `dim_macro_indicator`

## Data quality (expectations)

Every Bronze table gets explicit expectations, not ad-hoc checks. Starting set, based on the null-check pattern already prototyped with `read_files()`:
- `close_price IS NOT NULL`
- `trade_date IS NOT NULL`
- `ticker IS NOT NULL`
- fundamentals: `fiscal_period IS NOT NULL`, `company_id IS NOT NULL`

Use `EXPECT ... ON VIOLATION DROP ROW` for the fields above (bad rows shouldn't silently become bad facts downstream); log counts so a sudden spike in dropped rows is visible.

## Repo structure

```
nrw-industrials-financial-lakehouse/
├── ingestion/               # yfinance / Alpha Vantage / ECB pull scripts (Phase 1: run manually/locally)
├── pipelines/               # Lakeflow Declarative Pipelines (Python/SQL)
│   ├── bronze/
│   ├── silver_data_vault/
│   └── gold_star_schema/
├── adf/                     # Phase 2: ARM/JSON pipeline definitions, linked services
├── databricks.yml           # Databricks Asset Bundle config
├── docs/
│   └── architecture.md
└── README.md
```

## Roadmap

**Phase 1 — Databricks only (target: fast, a few focused sessions)**
1. Set up Databricks Free Edition workspace: catalog, schema, and a Unity Catalog Volume for raw landing
2. Write `ingestion/` scripts: yfinance historical pull, Alpha Vantage fundamentals pull, ECB SDW pull — land output as files in the Volume
3. Bronze: Lakeflow Declarative Pipeline using `read_files()`/Auto Loader off the Volume, with expectations from the section above
4. Silver: Data Vault hubs/links/satellites, MERGE-based satellite loading for fundamentals
5. Gold: fact/dim star schema
6. Genie space or Databricks SQL dashboard on Gold (example queries: compare RWE vs E.ON price volatility since 2022; which company improved operating margin most YoY)
7. Package as a Databricks Asset Bundle
8. Write README + architecture.md

**Phase 2 — Add ADF orchestration**
- ADF pipeline to trigger the Databricks ingestion job on a schedule
- ADF REST activities for Alpha Vantage / ECB SDW
- Document the ADF-triggers-Databricks pattern explicitly (common real enterprise setup)

## Environment and conventions

- Windows PowerShell; venv activation is `.\venv\Scripts\Activate.ps1`
- Databricks Free Edition (serverless-only)
- **Important platform note**: earlier projects worked around Free Edition blocking `spark.conf.set()` on raw/classic clusters (see Smart Grid Stream Week 2 workaround). Lakeflow Declarative Pipelines sidestep this entirely — serverless-native, always Unity-Catalog-governed. This project should not need that workaround; if a cluster config error shows up, check whether the pipeline is accidentally running on classic compute.
- No hardcoded secrets anywhere — all credentials (Alpha Vantage key) via `os.environ.get()`
- CLI-first development; UI/dashboard layers added afterward
- Document workarounds and platform constraints as architectural decisions, not TODOs to hide

## Learning notes carried in from dbdemos tutorials

- `read_files(path, format => "...", multiline => true)` — query files directly without creating a table first; useful for ad-hoc source inspection before deciding on Bronze expectations
- Window function pattern for category breakdowns: `round(count(*) * 100.0 / sum(count(*)) over(), 1)` — reusable for "what % of daily price rows come from each ticker" type checks
- CDC `operation` column pattern (INSERT/UPDATE/DELETE) doesn't apply directly here (no CDC source), but the underlying idea — track what changed, not just current state — is exactly why `sat_company_fundamentals` uses MERGE-based SCD2 instead of overwrite

## Open questions / next steps for Claude Code

- [ ] Confirm current yfinance install/behavior before relying on it
- [ ] Get free Alpha Vantage API key, store as env var
- [ ] Create Unity Catalog catalog/schema/volume for this project
- [ ] Scaffold `ingestion/` pull scripts
- [ ] Scaffold Lakeflow Declarative Pipeline for Bronze with `read_files()`/Auto Loader + expectations
- [ ] Design the exact MERGE logic for `sat_company_fundamentals`
