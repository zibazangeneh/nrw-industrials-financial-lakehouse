"""Static ingestion configuration. Sources and choices are explained in docs/decisions/ADR-001-data-sources.md."""

VOLUME_BASE = "/Volumes/nrw_fin/landing/raw"

BACKFILL_START = "2018-01-01"
INCREMENTAL_DAYS = 10  # overlap with the previous pull is fine, Silver dedupes

# Pinned to the same yfinance version as requirements.txt
YFINANCE_VERSION = "1.7.0"

COMPANIES = [
    {"company_id": "BASF",           "name": "BASF SE",           "ticker": "BAS.DE",  "fiscal_year_end": "12-31"},
    {"company_id": "BAYER",          "name": "Bayer AG",          "ticker": "BAYN.DE", "fiscal_year_end": "12-31"},
    {"company_id": "SIEMENS_ENERGY", "name": "Siemens Energy AG", "ticker": "ENR.DE",  "fiscal_year_end": "09-30"},
    {"company_id": "EON",            "name": "E.ON SE",           "ticker": "EOAN.DE", "fiscal_year_end": "12-31"},
    {"company_id": "RWE",            "name": "RWE AG",            "ticker": "RWE.DE",  "fiscal_year_end": "12-31"},
]

BENCHMARKS = [
    {"index_id": "DAX", "name": "DAX 40", "ticker": "^GDAXI"},
]

PRICE_TICKERS = [c["ticker"] for c in COMPANIES] + [b["ticker"] for b in BENCHMARKS]

ECB_BASE_URL = "https://data-api.ecb.europa.eu/service/data"
ECB_SERIES = {
    "eurusd": "EXR/D.USD.EUR.SP00.A",            # ECB business days
    "deposit_rate": "FM/D.U2.EUR.4F.KR.DFR.LEV",  # calendar days
}
