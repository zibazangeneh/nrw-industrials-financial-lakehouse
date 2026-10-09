# ADR-001 · Data sources

**Status:** Accepted · **Date:** 2026-10-09 · **Ticket:** NRW-005
**Evidence:** `explorations/00_alphavantage_access.py`, `explorations/01_source_coverage.py` (run on serverless, 2026-10-09)

## Context

The original plan used three sources: yfinance (prices), Alpha Vantage (fundamentals) and the ECB (macro). Before building pipelines, each one was tested against the actual companies in scope: BASF, Bayer, Siemens Energy, E.ON, RWE and the DAX.

## Findings

### Prices: yfinance 1.7.0 ✅

| Company | Ticker | History available | Rows | Null closes |
|---|---|---|---|---|
| BASF | `BAS.DE` | 1996-12-16 → today | 7,637 | 0 |
| Bayer | `BAYN.DE` | 1996-12-16 → today | 7,637 | 0 |
| Siemens Energy | `ENR.DE` | **2020-09-29** → today (spun off from Siemens) | 1,537 | 0 |
| E.ON | `EOAN.DE` | 2000-01-03 → today | 6,842 | 0 |
| RWE | `RWE.DE` | 1996-12-16 → today | 7,637 | 0 |
| DAX (benchmark) | `^GDAXI` | 1987-12-30 → today | 9,807 | 0 |

All prices are in EUR.

### Fundamentals: Alpha Vantage ❌ → yfinance ✅

| Test | Result |
|---|---|
| Alpha Vantage `OVERVIEW` | **Premium**: not available on the free tier, even for IBM |
| Alpha Vantage `INCOME_STATEMENT` / `BALANCE_SHEET` for IBM | Free, works |
| Alpha Vantage `INCOME_STATEMENT` for all 5 companies, XETRA symbols (`BAS.DEX`, …) **and** US ADRs (`BASFY`, `BAYRY`, `SMNEY`, `EONGY`, `RWEOY`) | **Empty response for all 10.** Alpha Vantage fundamentals only cover US-reporting companies; these companies report under IFRS in Germany |
| yfinance `quarterly_income_stmt` / `quarterly_balance_sheet` | ✅ all 5 companies, **5–6 quarters**, latest 2026-06-30. `Total Revenue`, `Operating Income` and `Net Income` all present |

### Macro: ECB Data Portal ✅

The old SDW API (`sdw-wsrest.ecb.europa.eu`) has moved to the **ECB Data Portal** (`data-api.ecb.europa.eu`).

| Series | Key | Frequency | Since 2015 |
|---|---|---|---|
| EUR/USD reference rate | `EXR/D.USD.EUR.SP00.A` | ECB business days (no weekends/holidays) | 3,013 rows |
| Deposit facility rate | `FM/D.U2.EUR.4F.KR.DFR.LEV` | **Calendar days** (incl. weekends) | 4,300 rows |

## Decisions

1. **Alpha Vantage is dropped.** It has no fundamentals for any company in scope. The secret-scope setup from NRW-004 stays in place as the pattern for any future API key.
2. **yfinance supplies both prices and fundamentals.**
   - Prices: the 6 tickers above, **backfill from 2018-01-01**. That gives a pre-2022 baseline for the energy-crisis comparisons while keeping volumes small. Siemens Energy simply starts on 2020-09-29.
   - Fundamentals: quarterly **and** annual income statement + balance sheet, pulled **weekly**.
3. **Fundamentals history is built up over time, not backfilled.** Yahoo only serves the last 5–6 quarters (about 4 years for annual statements). Each weekly pull lands a full snapshot, and `sat_company_fundamentals` (SCD2) keeps every version. That keeps quarters after Yahoo drops them and records restatements. Without it, the history would be gone, which makes the satellite essential rather than decorative.
4. **Fundamentals land in long format.** One row per `(company_id, statement, frequency, period_end, metric)`. Yahoo adds and removes line items between companies and over time; long format keeps the landing and Bronze schema stable, and Silver picks the metrics it needs.
5. **Macro: ECB Data Portal**, the two series above, backfilled from 2018-01-01. Because the two series have different calendars, Gold joins them to trading days with an **as-of join** (last known value), not an equi-join.

## Consequences and risks

- **yfinance is now a single point of failure** for prices and fundamentals. It is an unofficial wrapper around Yahoo endpoints and can break without notice. Mitigations:
  - the version is pinned (`yfinance==1.7.0`)
  - raw files are kept in the Volume, so a broken pull never damages existing data
  - each pull fails loudly per ticker instead of landing empty files
  - the README documents this trade-off
- **Fiscal calendars differ:** Siemens Energy's fiscal year ends **30 September**; the others follow the calendar year. The fundamentals business key uses the **period end date**, not a "fiscal quarter" label, and `dim_date` carries both calendar and per-company fiscal attributes.
- **Phase 2 (ADF) changes:** the ADF REST activity now only covers the ECB. yfinance runs as a Databricks job triggered by ADF.
