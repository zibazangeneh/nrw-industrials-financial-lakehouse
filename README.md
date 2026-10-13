# NRW Industrials Financial Lakehouse

A financial lakehouse on Databricks built on real market data for five NRW industrial companies (**BASF, Bayer, Siemens Energy, E.ON, RWE**), with the **DAX** as benchmark.

> 🚧 **Work in progress.** Built ticket by ticket; see [`TICKETS.md`](TICKETS.md) for progress and [`docs/decisions/`](docs/decisions/) for the architecture decisions made along the way.

## Architecture

```
yfinance (prices + fundamentals) · ECB Data Portal (EUR/USD, deposit rate)
        │  Databricks notebooks (serverless)
        ▼
Unity Catalog Volume  nrw_fin.landing.raw      append-only raw files
        │  Lakeflow Declarative Pipeline (Auto Loader + expectations)
        ▼
Bronze  →  Silver (Data Vault 2.0, SCD2 satellites)  →  Gold (star schema)
        │
        ▼
Genie / Databricks SQL
```

**Phase 2:** Azure Data Factory takes over orchestration (triggers the Databricks ingestion job and pulls the ECB REST API).

## Stack

Databricks Free Edition (serverless) · Unity Catalog · Lakeflow Declarative Pipelines · Data Vault 2.0 · Databricks Asset Bundles · Azure Data Factory (Phase 2)

## Key decisions so far

- [ADR-000](docs/decisions/ADR-000-platform-constraints.md): ingestion runs inside Databricks, because serverless compute can reach the data sources.
- [ADR-001](docs/decisions/ADR-001-data-sources.md): Alpha Vantage was tested and **dropped** (no fundamentals for German IFRS reporters). yfinance supplies prices and fundamentals, and fundamentals history is built up over time in an SCD2 satellite.
