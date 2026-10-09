# TICKETS — NRW Industrials Financial Lakehouse

Backlog derived from `CLAUDE.md`. Tickets are ordered so each one can be picked up once its dependencies are done.
Size: **S** ≈ < 1h, **M** ≈ 1–3h, **L** ≈ half a day+.

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

## Overview

| ID | Title | Epic | Size | Depends on |
|---|---|---|---|---|
| NRW-001 | Scaffold repo and local environment | 0 Setup | S | — |
| NRW-002 | Databricks CLI auth + Free Edition capability check | 0 Setup | S | 001 |
| NRW-003 | Create Unity Catalog catalog / schemas / Volume | 0 Setup | S | 002 |
| NRW-004 | Alpha Vantage API key as env var | 0 Setup | S | 001 |
| NRW-005 | Spike: verify data-source coverage | 1 Ingestion | M | 001, 004 |
| NRW-006 | Shared ingestion helpers (Volume upload, naming, logging) | 1 Ingestion | M | 003 |
| NRW-007 | yfinance daily price pull | 1 Ingestion | M | 005, 006 |
| NRW-008 | Alpha Vantage fundamentals pull | 1 Ingestion | M | 005, 006 |
| NRW-009 | ECB Data Portal macro pull | 1 Ingestion | S | 005, 006 |
| NRW-010 | Ingestion runner CLI + first backfill | 1 Ingestion | S | 007, 008, 009 |
| NRW-011 | Source inspection with `read_files()` | 2 Bronze | S | 010 |
| NRW-012 | Bronze Lakeflow Declarative Pipeline + expectations | 2 Bronze | L | 011 |
| NRW-013 | Data-quality monitoring from the pipeline event log | 2 Bronze | M | 012 |
| NRW-014 | Design: Data Vault keys + `sat_company_fundamentals` change logic | 3 Silver | M | 012 |
| NRW-015 | Company reference seed + hubs + link | 3 Silver | M | 014 |
| NRW-016 | `sat_price_daily` | 3 Silver | M | 015 |
| NRW-017 | `sat_company_fundamentals` (SCD2, change-only inserts) | 3 Silver | L | 015 |
| NRW-018 | Macro indicators in Silver | 3 Silver | S | 014 |
| NRW-019 | Gold dimensions | 4 Gold | M | 016, 017, 018 |
| NRW-020 | Gold facts | 4 Gold | M | 019 |
| NRW-021 | Gold validation queries | 4 Gold | S | 020 |
| NRW-022 | Genie space / SQL dashboard on Gold | 5 BI | M | 021 |
| NRW-023 | Package as Databricks Asset Bundle | 6 Packaging | M | 012–020 |
| NRW-024 | End-to-end runbook + smoke test | 6 Packaging | M | 023 |
| NRW-025 | README + `docs/architecture.md` + ADRs | 6 Packaging | M | 024 |
| NRW-026 | Spike: ADF ↔ Databricks Free Edition connectivity | 7 ADF (Phase 2) | M | 025 |
| NRW-027 | Move yfinance pull into a Databricks job | 7 ADF (Phase 2) | M | 026 |
| NRW-028 | ADF pipeline + schedule trigger for the Databricks job | 7 ADF (Phase 2) | M | 027 |
| NRW-029 | ADF REST activities for Alpha Vantage + ECB | 7 ADF (Phase 2) | L | 026 |
| NRW-030 | Commit ADF definitions + document the pattern | 7 ADF (Phase 2) | S | 028, 029 |

---

## Epic 0 — Setup

### NRW-001 · Scaffold repo and local environment `[x]` · S
**Goal:** An empty project skeleton matching the repo structure in `CLAUDE.md`, under git.
- [ ] Create `nrw-industrials-financial-lakehouse/` with `ingestion/`, `pipelines/{bronze,silver_data_vault,gold_star_schema}/`, `adf/`, `docs/`, `docs/decisions/`, `setup/`
- [ ] `git init`, `.gitignore` (`venv/`, `.env`, `__pycache__/`, `.databricks/`, local data files)
- [ ] `python -m venv venv`, then `.\venv\Scripts\Activate.ps1`
- [ ] `requirements.txt`: `yfinance`, `requests`, `pandas`, `pyarrow`, `databricks-sdk`, `python-dotenv`
- [ ] `.env.example` listing `ALPHAVANTAGE_API_KEY=`, `DATABRICKS_PROFILE=`, `NRW_CATALOG=`, `NRW_VOLUME_PATH=` (no real values)

**Done when:** `pip install -r requirements.txt` succeeds and the first commit is made.

### NRW-002 · Free Edition capability check `[x]` · S
**Goal:** Find out early which platform limits will affect later tickets.
- [x] Workspace project folder created in the UI (mirrors this repo)
- [x] Check: does serverless notebook compute have **outbound internet**? → **Yes**: Yahoo, ECB and Alpha Vantage all reachable (`setup/00_platform_checks.py`)
- [x] Check: can you create a **new catalog** on Free Edition? → **Yes** (NRW-003)
- [x] Findings recorded in `docs/decisions/ADR-000-platform-constraints.md`
- [ ] ~~CLI login~~ → deferred to NRW-023 (Asset Bundles). Because the sources are reachable, Phase 1 ingestion runs inside Databricks and doesn't need the CLI

**Done when:** The checks are recorded in the ADR.

### NRW-003 · Create Unity Catalog catalog / schemas / Volume `[x]` · S
**Goal:** Governed landing zone + layer schemas.
- [x] `setup/00_create_uc_objects.sql` (idempotent `CREATE ... IF NOT EXISTS`):
  - catalog `nrw_fin` (or the workspace catalog if NRW-002 says you can't create one)
  - schemas `landing`, `bronze`, `silver`, `gold`
  - managed Volume `landing.raw`
- [x] Folder convention in the Volume:
  `/prices/`, `/fundamentals/income_statement/`, `/fundamentals/balance_sheet/`, `/macro/eurusd/`, `/macro/deposit_rate/`
- [x] Add `COMMENT`s on the catalog, schemas and Volume (governance story)

**Done when:** The Volume `landing.raw` is visible in Catalog Explorer. Subfolders are created by the ingestion notebooks on first write.

### NRW-004 · Alpha Vantage API key as a Databricks secret `[x]` · S
> Changed after ADR-000: ingestion runs inside Databricks, so the key lives in a Databricks secret scope rather than a local `.env`.
- [x] Get the free key from alphavantage.co
- [x] One-time CLI step (Databricks has no UI for secrets): `databricks auth login`, then create scope `nrw` and put secret `alphavantage_api_key`. The CLI prompts for the value, so it never lands in a file, notebook or shell history
- [x] Code reads it only via `dbutils.secrets.get("nrw", "alphavantage_api_key")` and never prints it
- [ ] Optional, for local runs: `.env` with `ALPHAVANTAGE_API_KEY` (gitignored)

**Done when:** `setup/01_check_secret.py` on serverless shows the secret as `[REDACTED]` and makes one successful Alpha Vantage call.

**Outcome:** key works. `OVERVIEW` is **premium** on the free tier; `INCOME_STATEMENT`, `BALANCE_SHEET`, `GLOBAL_QUOTE` and `TIME_SERIES_DAILY` are free (`explorations/00_alphavantage_access.py`). → `OVERVIEW` dropped; static company attributes come from the `ref_company` seed (NRW-015).


---

## Epic 1 — Ingestion (Phase 1: run locally, land in the Volume)

### NRW-005 · Spike: verify data-source coverage `[ ]` · M
**Goal:** Resolve the "confirm yfinance behaviour" open question and catch source gaps **before** writing pipelines.
- [ ] **yfinance**: pin the installed version; confirm daily history for `BAS.DE`, `BAYN.DE`, `ENR.DE`, `EOAN.DE`, `RWE.DE`, `^GDAXI`. Note: Siemens Energy (`ENR.DE`) only has history from Sept 2020, so pick a backfill start date that accounts for that
- [ ] **Alpha Vantage**: test `INCOME_STATEMENT` / `BALANCE_SHEET` (`OVERVIEW` is premium, see NRW-004) for the XETRA symbols **and** the US ADR symbols (`BASFY`, `BAYRY`, `SMNEY`, `EONGY`, `RWEOY`). ⚠️ Risk: AV fundamentals coverage for non-US issuers is patchy and may come back empty
- [ ] If AV coverage has gaps: evaluate the fallback `yfinance.Ticker(...).quarterly_income_stmt` / `quarterly_balance_sheet`
- [ ] **ECB**: the old SDW API has moved to the ECB Data Portal (`https://data-api.ecb.europa.eu/service/data/...`). Confirm the series keys:
  - EUR/USD reference rate: `EXR/D.USD.EUR.SP00.A`
  - Deposit facility rate: `FM/D.U2.EUR.4F.KR.DFR.LEV` (check it)
- [ ] Record the decisions in `docs/decisions/ADR-001-data-sources.md`, including the yfinance "unofficial wrapper" trade-off

**Done when:** The ADR lists the exact ticker/symbol/series key for each source, with a fallback decision for fundamentals.

### NRW-006 · Shared ingestion helpers `[ ]` · M
**Goal:** One place for landing files, so swapping in ADF later only changes this layer.
- [ ] `ingestion/common.py`:
  - `upload_to_volume(local_path, volume_subpath)` using `databricks-sdk` `WorkspaceClient().files.upload(...)`
  - File naming: `<source>_<entity>_<YYYYMMDD>T<HHMMSS>Z.<ext>`, so files are append-only and never overwritten (Auto Loader friendly)
  - Logging setup, config loaded from env (`NRW_VOLUME_PATH`, profile)
- [ ] `ingestion/config.py`: company ↔ ticker ↔ AV symbol mapping from NRW-005

**Done when:** A dummy file uploads and shows up in the Volume.

### NRW-007 · yfinance daily price pull `[ ]` · M
- [ ] `ingestion/pull_prices.py` with `--mode backfill|incremental` and `--start` (default from the ADR)
- [ ] Normalise columns: `trade_date, ticker, open, high, low, close_price, adj_close, volume`, plus `source='yfinance'` and `ingested_at`
- [ ] Write Parquet per run → `/prices/`
- [ ] Incremental mode: pull the last N days (overlap is fine; Silver dedupes)
- [ ] Handle a failure on one ticker without killing the whole run; log per-ticker row counts

**Done when:** The backfill lands one or more Parquet files with all 6 tickers.

### NRW-008 · Alpha Vantage fundamentals pull `[ ]` · M
- [ ] `ingestion/pull_fundamentals.py`: 3 endpoints × 5 companies = 15 calls (fits the 25/day limit)
- [ ] Rate limiting: ≥ 12 s between calls (5/min), and a hard stop at a configurable daily budget
- [ ] ⚠️ AV returns **HTTP 200 with a `Note` / `Information` key** when throttled or when the key is invalid. Detect this and fail loudly instead of landing junk
- [ ] Land the raw JSON as-is (one file per symbol per endpoint) → `/fundamentals/<endpoint>/`; Bronze does the parsing
- [ ] If NRW-005 chose the yfinance fallback for some companies, implement that path here too and tag it with `source`

**Done when:** All 5 companies have fundamentals files landed, and a throttled response is rejected.

### NRW-009 · ECB Data Portal macro pull `[ ]` · S
- [ ] `ingestion/pull_ecb.py`: `?format=csvdata&startPeriod=...` for both series
- [ ] Land the CSV → `/macro/eurusd/`, `/macro/deposit_rate/`

**Done when:** Both series land with history covering the price backfill range.

### NRW-010 · Ingestion runner CLI + first backfill `[ ]` · S
- [ ] `python -m ingestion.run --source prices|fundamentals|ecb|all --mode backfill|incremental`
- [ ] Run the full backfill once and record row/file counts in the PR/commit message

**Done when:** The Volume holds a full historical landing for every source.

---

## Epic 2 — Bronze

### NRW-011 · Source inspection with `read_files()` `[ ]` · S
**Goal:** Base the Bronze expectations on what the data actually looks like.
- [ ] `explorations/01_inspect_landing.sql`: `read_files()` on each Volume folder (`format => 'parquet' | 'json' | 'csv'`, `multiline => true` for AV JSON)
- [ ] Null counts per key column; % of rows per ticker using `round(count(*) * 100.0 / sum(count(*)) over(), 1)`
- [ ] Check the AV JSON shape: `annualReports` / `quarterlyReports` arrays, string-typed numbers, `"None"` literals

**Done when:** Expectation list confirmed or adjusted; any surprises noted in ADR-001.

### NRW-012 · Bronze Lakeflow Declarative Pipeline + expectations `[ ]` · L
- [ ] `pipelines/bronze/bronze.sql` (or `.py`); **serverless**, target catalog/schema `bronze`
- [ ] Streaming tables via `STREAM read_files(...)` (Auto Loader):
  - `bronze_prices`: `CONSTRAINT ... EXPECT (close_price IS NOT NULL) ON VIOLATION DROP ROW`, same for `trade_date` and `ticker`
  - `bronze_fundamentals_income`, `bronze_fundamentals_balance`: explode `quarterlyReports` (+ `annualReports`) into one row per period; `fiscal_period IS NOT NULL`, `company_id IS NOT NULL` → DROP ROW
  - `bronze_macro_ecb`: `obs_date`, `series_key`, `obs_value` NOT NULL
- [ ] Every table: `_metadata.file_path AS source_file`, `_metadata.file_modification_time`, `current_timestamp() AS bronze_loaded_at`, keep `_rescued_data`
- [ ] Create the pipeline (UI or CLI for now; formalised in NRW-023) and run it

**Done when:** The pipeline run succeeds on serverless, all Bronze tables are populated, and the expectations show up in the pipeline UI. If a cluster/`spark.conf` error appears, check for classic compute (see `CLAUDE.md` platform note).

### NRW-013 · Data-quality monitoring from the event log `[ ]` · M
**Goal:** "Log counts so a spike in dropped rows is visible."
- [ ] `pipelines/bronze/dq_monitoring.sql`: view over `event_log(<pipeline>)` → `flow_progress` events → `details:flow_progress.data_quality.expectations` → passed/failed records per expectation per update
- [ ] Simple threshold query: flag any update where dropped % > X

**Done when:** One query shows dropped-row counts per table, per expectation, per run.

---

## Epic 3 — Silver (Data Vault 2.0)

### NRW-014 · Design: Data Vault keys + `sat_company_fundamentals` change logic `[ ]` · M
**Goal:** Resolve the open question "design the exact MERGE logic".
- [ ] Hash key convention: `md5(upper(trim(business_key)))`; standard columns `load_ts`, `record_source`
- [ ] `hashdiff` = md5 over the tracked fundamentals columns (fixed column order, null-safe `coalesce`)
- [ ] Decide on the implementation and record it in `docs/decisions/ADR-002-satellite-loading.md`:
  - **Option A (recommended):** inside the pipeline, `AUTO CDC INTO ... KEYS (company_hk, fiscal_period) SEQUENCE BY load_ts STORED AS SCD TYPE 2 TRACK HISTORY ON <columns>`. Declarative, and only opens a new version when tracked values change
  - **Option B:** an explicit `MERGE` with a hashdiff comparison in a separate job task after the pipeline. Closer to the "MERGE-based" wording in `CLAUDE.md` and makes the Data Vault mechanics more visible, but sits outside the pipeline lineage
- [ ] Name the business keys: company = internal `company_id` (e.g. `BASF`), security = yfinance ticker

**Done when:** The ADR is merged, with a worked example (unchanged pull → 0 new rows; restated revenue → 1 new row, old row end-dated).

### NRW-015 · Company reference seed + hubs + link `[ ]` · M
- [ ] `pipelines/silver_data_vault/ref_company.csv` (or a SQL `VALUES` table): `company_id, company_name, isin, yf_ticker, av_symbol, sector, hq_city`
- [ ] `hub_company`, `hub_security` (incl. `^GDAXI` as an index security with no company), `link_company_security`
- [ ] Hubs are insert-only (no duplicates on re-run)

**Done when:** 5 companies, 6 securities and 5 links exist; re-running adds no rows.

### NRW-016 · `sat_price_daily` `[ ]` · M
- [ ] Keyed on `security_hk, trade_date`; dedupes the overlapping incremental pulls (latest `bronze_loaded_at` wins)
- [ ] Carries OHLCV + `adj_close` + `record_source`

**Done when:** No duplicate `(security_hk, trade_date)` rows, and row counts match Bronze minus duplicates.

### NRW-017 · `sat_company_fundamentals` (SCD2, change-only inserts) `[ ]` · L
- [ ] Implement per ADR-002: revenue, gross profit, operating income, net income, total assets, total liabilities, equity, derived operating margin
- [ ] Cast AV string numbers → `DECIMAL`, map `"None"` → NULL
- [ ] **Test:** re-land identical files and rerun → 0 new versions. Hand-edit one value in a test file and rerun → exactly 1 new version, previous version end-dated
- [ ] Record the test outcome in ADR-002

**Done when:** Both test cases pass and are documented.

### NRW-018 · Macro indicators in Silver `[ ]` · S
> Gap in `CLAUDE.md`: Gold has `dim_macro_indicator`, but Silver has no macro entity.
- [ ] `hub_macro_indicator` (business key = ECB series key) + `sat_macro_observation` (`obs_date`, `obs_value`)
- [ ] Update the data model section in `CLAUDE.md`

**Done when:** Both ECB series are in Silver and `CLAUDE.md` reflects them.

---

## Epic 4 — Gold (star schema)

### NRW-019 · Gold dimensions `[ ]` · M
- [ ] `dim_date`: generated calendar covering the full range, with `is_trading_day` (XETRA) derived from price data, plus quarter/fiscal attributes
- [ ] `dim_company`: current attributes from the ref seed + hubs (SCD1 is fine here)
- [ ] `dim_macro_indicator`: one row per series (name, unit, frequency, source)
- [ ] Materialized views in `pipelines/gold_star_schema/`

**Done when:** All three dims exist with surrogate/natural keys and comments.

### NRW-020 · Gold facts `[ ]` · M
- [ ] `fact_daily_price`: grain = security × trade_date; OHLCV, `daily_return`, and EUR/USD of that day (from macro, as-of join for non-ECB days)
- [ ] `fact_quarterly_financials`: grain = company × fiscal_quarter, using the **current** satellite version; revenue, operating income, `operating_margin`, YoY deltas
- [ ] Add a macro fact (`fact_macro_daily`), or join macro into `fact_daily_price`. Decide which and note it in architecture.md
- [ ] Add column comments everywhere (Genie uses them)

**Done when:** The facts join cleanly to all dims with no orphan keys (checked by query).

### NRW-021 · Gold validation queries `[ ]` · S
- [ ] `explorations/02_gold_questions.sql`:
  - RWE vs E.ON annualised volatility of daily returns since 2022-01-01
  - Which company improved operating margin most YoY (latest quarter)
- [ ] Sanity checks: the DAX price is in a plausible range, and there are no gaps > 5 trading days per ticker

**Done when:** Both questions return plausible answers.

---

## Epic 5 — BI

### NRW-022 · Genie space / SQL dashboard on Gold `[ ]` · M
- [ ] Genie space on the `gold` tables only; add instructions (definitions of volatility, operating margin, fiscal quarter) and the NRW-021 SQL as example queries
- [ ] Test 5+ natural-language questions and note where Genie fails
- [ ] Optional: AI/BI dashboard with price index chart, margin comparison and DQ panel (NRW-013)
- [ ] Screenshots → `docs/img/` for the README

**Done when:** Genie answers both example questions correctly.

---

## Epic 6 — Packaging and docs

### NRW-023 · Package as Databricks Asset Bundle `[ ]` · M
- [ ] `databricks.yml` with `dev` target (variables: `catalog`, Volume path)
- [ ] `resources/lakehouse_pipeline.yml`: `serverless: true`, catalog/schema, libraries pointing at the bronze/silver/gold sources
- [ ] `resources/refresh_job.yml`: a job that runs the pipeline (+ the MERGE task if ADR-002 chose Option B)
- [ ] `databricks bundle validate` → `deploy -t dev` → `run`
- [ ] Delete the manually created pipeline from NRW-012 so only the bundle-managed one remains

**Done when:** A clean `bundle deploy` + `bundle run` rebuilds everything.

### NRW-024 · End-to-end runbook + smoke test `[ ]` · M
- [ ] `docs/runbook.md`: from a fresh clone → env → UC setup → backfill → bundle deploy → run → Genie
- [ ] Run it start to finish yourself, ideally with a dropped-and-recreated schema, and fix anything undocumented
- [ ] Incremental day-2 run: `--mode incremental` → pipeline run → new rows only

**Done when:** The runbook works start to finish without tribal knowledge.

### NRW-025 · README + `docs/architecture.md` + ADRs `[ ]` · M
- [ ] README: purpose, architecture diagram, tech choices, how to run, screenshots, limitations (yfinance unofficial, AV free tier, Free Edition constraints)
- [ ] architecture.md: layer-by-layer design, Data Vault → star rationale, expectations strategy, Phase 2 plan
- [ ] Link ADR-000 … ADR-002
- [ ] Tick off the "Open questions" in `CLAUDE.md`

**Done when:** A reviewer can understand and run the project from the README alone. **End of Phase 1.**

---

## Epic 7 — Phase 2: ADF orchestration

### NRW-026 · Spike: ADF ↔ Databricks Free Edition connectivity `[ ]` · M
**Goal:** Check feasibility before building. Neither of these is guaranteed:
- [ ] **Triggering:** Free Edition isn't an Azure Databricks workspace, so ADF's Azure Databricks linked service may not apply. Probable route: an ADF **Web activity** → Jobs API `POST /api/2.2/jobs/run-now` with a token from Azure Key Vault, plus a polling loop on `runs/get`
- [ ] **Landing:** ADF has no native UC Volume sink. Options: Web activity → Files API `PUT /api/2.0/fs/files/Volumes/...`, or ADF only *triggers* Databricks jobs that do the pulls themselves
- [ ] Requires an Azure subscription (free tier) for ADF + Key Vault
- [ ] Record the outcome in `docs/decisions/ADR-003-adf-integration.md`

**Done when:** The ADR picks a working pattern, backed by a manual proof (one successful triggered run).

### NRW-027 · Move yfinance pull into a Databricks job `[ ]` · M
- [ ] Notebook/Python task wrapping `ingestion.pull_prices` that writes straight to `/Volumes/...` (needs serverless outbound internet, see NRW-002)
- [ ] Add it to the bundle as `ingestion_job`, with the pipeline refresh as a downstream task

**Done when:** `bundle run ingestion_job` lands prices and refreshes the lakehouse.

### NRW-028 · ADF pipeline + schedule trigger for the Databricks job `[ ]` · M
- [ ] Pipeline `pl_daily_prices`: trigger job → poll until terminal state → fail the ADF run if the job fails
- [ ] Schedule trigger: daily after XETRA close (e.g. 19:00 CET)

**Done when:** A scheduled run executes unattended and is visible in ADF monitoring.

### NRW-029 · ADF REST activities for Alpha Vantage + ECB `[ ]` · L
- [ ] Alpha Vantage: ForEach over companies × endpoints, sequential with a Wait of ≥ 12 s, API key from Key Vault, **weekly** trigger
- [ ] Throttle detection: an If Condition on the `Note` / `Information` key in the response
- [ ] ECB: REST/HTTP source → CSV, daily trigger
- [ ] Landing per the ADR-003 pattern, using the **same paths and file naming** as Phase 1 so nothing downstream changes

**Done when:** Bronze picks up ADF-landed files with no code change.

### NRW-030 · Commit ADF definitions + document the pattern `[ ]` · S
- [ ] Export ARM/JSON (pipelines, linked services, triggers, datasets) → `adf/`, with no secrets
- [ ] architecture.md: an "ADF triggers Databricks" section with a diagram, and why ADF handles orchestration while Databricks handles compute
- [ ] README: Phase 2 setup steps

**Done when:** The ADF setup is reproducible from the repo. **End of Phase 2.**
