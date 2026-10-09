# ADR-000 · Platform constraints (Databricks Free Edition)

**Status:** Accepted · **Date:** 2026-10-09 · **Ticket:** NRW-002

## Context

The project runs on Databricks Free Edition (serverless-only). Two things had to be checked before designing ingestion:

1. Can serverless compute reach the external data sources (outbound internet)?
2. Can we create our own Unity Catalog catalog?

## Findings

| Check | Result | How verified |
|---|---|---|
| Outbound HTTP to Yahoo Finance (`query1.finance.yahoo.com`) | ✅ reachable (HTTP 200) | `setup/00_platform_checks.py` on serverless |
| Outbound HTTP to ECB Data Portal (`data-api.ecb.europa.eu`) | ✅ reachable (HTTP 200) | same |
| Outbound HTTP to Alpha Vantage (`www.alphavantage.co`) | ✅ reachable (HTTP 200) | same |
| `CREATE CATALOG` allowed | _pending — NRW-003_ | `setup/00_create_uc_objects.sql` |

## Decision

**Ingestion runs inside Databricks** (serverless notebooks/jobs) and writes directly to the Unity Catalog Volume via its `/Volumes/...` path.

- Phase 1 doesn't need a local "download, then upload with the CLI/SDK" step. The original NRW-006 upload helper is reduced to path/naming helpers.
- The Databricks CLI is only needed later, for Asset Bundles (NRW-023).
- The Phase 2 story stays the same: ADF triggers the Databricks ingestion job instead of a person running the notebook.

## Consequences

- The Alpha Vantage API key has to be available inside Databricks. Preferred: a Databricks secret scope (`dbutils.secrets.get("nrw", "alphavantage_api_key")`). Creating a secret scope needs the CLI/API, so that one step is done from the CLI when NRW-008 starts.
- Free Edition's outbound access could be restricted in the future. If that happens, fall back to running `ingestion/` locally and uploading to the Volume.
