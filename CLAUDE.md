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
   pulls yfinance (prices + fundamentals) / ECB Data Portal
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
- ADF REST activity for the ECB Data Portal (plain REST API, no wrapper library needed). Alpha Vantage was dropped (ADR-001)
- Everything downstream (Bronze/Silver/Gold/Genie) stays the same — ADF only changes how data arrives in the Volume

## Data sources

> Decided in `docs/decisions/ADR-001-data-sources.md` after testing every source against the real companies (2026-10-09).

- **yfinance** (pinned `1.7.0`) — daily OHLCV price history for `BAS.DE`, `BAYN.DE`, `ENR.DE`, `EOAN.DE`, `RWE.DE` + `^GDAXI` (DAX), backfilled from **2018-01-01** (Siemens Energy only exists since 2020-09-29). **Also the fundamentals source**: quarterly + annual income statement and balance sheet, pulled **weekly** as a full snapshot. Yahoo only serves 5–6 quarters, so history builds up in the SCD2 satellite rather than being backfilled. Fundamentals land in **long format** (`company_id, statement, frequency, period_end, metric, value`). No API key. Unofficial Yahoo wrapper — can break if Yahoo changes something, and it's now a single point of failure for prices and fundamentals; note this trade-off in the README rather than treating a break as a bug.
- **Alpha Vantage — dropped.** `OVERVIEW` is premium, and `INCOME_STATEMENT`/`BALANCE_SHEET` return empty for all 5 companies (XETRA and US ADR symbols); its fundamentals only cover US reporters. The key stays in secret scope `nrw` (`alphavantage_api_key`) as the pattern for future keys.
- **ECB Data Portal API** (successor of the SDW API, `data-api.ecb.europa.eu`) — EUR/USD `EXR/D.USD.EUR.SP00.A` (business days), deposit facility rate `FM/D.U2.EUR.4F.KR.DFR.LEV` (calendar days). Free, no key. Different calendars → as-of join to trading days in Gold.
- **Fiscal calendars differ:** Siemens Energy's fiscal year ends 30 September; the others are calendar-year. Key fundamentals on `period_end`, not on a fiscal-quarter label.

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
├── ingestion/               # yfinance / ECB pull notebooks (Phase 1: run in Databricks, write straight to the Volume)
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
2. Write `ingestion/` notebooks: yfinance price pull, yfinance fundamentals pull, ECB pull — land output as files in the Volume
3. Bronze: Lakeflow Declarative Pipeline using `read_files()`/Auto Loader off the Volume, with expectations from the section above
4. Silver: Data Vault hubs/links/satellites, MERGE-based satellite loading for fundamentals
5. Gold: fact/dim star schema
6. Genie space or Databricks SQL dashboard on Gold (example queries: compare RWE vs E.ON price volatility since 2022; which company improved operating margin most YoY)
7. Package as a Databricks Asset Bundle
8. Write README + architecture.md

**Phase 2 — Add ADF orchestration**
- ADF pipeline to trigger the Databricks ingestion job on a schedule
- ADF REST activity for the ECB Data Portal
- Document the ADF-triggers-Databricks pattern explicitly (common real enterprise setup)

## Environment and conventions

- Windows PowerShell; venv activation is `.\venv\Scripts\Activate.ps1`
- Databricks Free Edition (serverless-only)
- **Important platform note**: earlier projects worked around Free Edition blocking `spark.conf.set()` on raw/classic clusters (see Smart Grid Stream Week 2 workaround). Lakeflow Declarative Pipelines sidestep this entirely — serverless-native, always Unity-Catalog-governed. This project should not need that workaround; if a cluster config error shows up, check whether the pipeline is accidentally running on classic compute.
- No hardcoded secrets anywhere — credentials live in the Databricks secret scope `nrw` and are read via `dbutils.secrets.get()` (or `os.environ.get()` for local runs)
- CLI-first development; UI/dashboard layers added afterward
- Document workarounds and platform constraints as architectural decisions, not TODOs to hide

## Learning notes carried in from dbdemos tutorials

- `read_files(path, format => "...", multiline => true)` — query files directly without creating a table first; useful for ad-hoc source inspection before deciding on Bronze expectations
- Window function pattern for category breakdowns: `round(count(*) * 100.0 / sum(count(*)) over(), 1)` — reusable for "what % of daily price rows come from each ticker" type checks
- CDC `operation` column pattern (INSERT/UPDATE/DELETE) doesn't apply directly here (no CDC source), but the underlying idea — track what changed, not just current state — is exactly why `sat_company_fundamentals` uses MERGE-based SCD2 instead of overwrite

## Open questions / next steps for Claude Code

- [x] Confirm current yfinance install/behavior before relying on it (ADR-001)
- [x] Get free Alpha Vantage API key → stored in secret scope; Alpha Vantage then dropped (ADR-001)
- [x] Create Unity Catalog catalog/schema/volume for this project (`nrw_fin`, NRW-003)
- [ ] Scaffold `ingestion/` pull scripts
- [ ] Scaffold Lakeflow Declarative Pipeline for Bronze with `read_files()`/Auto Loader + expectations
- [ ] Design the exact MERGE logic for `sat_company_fundamentals`

## Session workflow

- Work tracked in `TICKETS.md`; decisions in `docs/decisions/ADR-*.md`
- Ingestion runs inside Databricks (serverless has outbound internet, ADR-000); the CLI is only used for secrets and, later, Asset Bundles
