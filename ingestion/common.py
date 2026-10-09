"""Landing helpers: every file goes to the Volume under a unique, timestamped name, so landing is append-only."""

import os
from datetime import datetime, timezone

import pandas as pd

from config import VOLUME_BASE


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def landing_path(entity: str, ext: str, ts: datetime | None = None) -> str:
    """Build `<base>/<entity>/<name>_<YYYYMMDD>T<HHMMSS>Z.<ext>` and create the folder if needed.

    `entity` can be nested, e.g. "fundamentals/income_statement"; the file name uses its last part.
    """
    ts = ts or utc_now()
    folder = f"{VOLUME_BASE}/{entity}"
    os.makedirs(folder, exist_ok=True)
    name = entity.rsplit("/", 1)[-1]
    return f"{folder}/{name}_{ts:%Y%m%dT%H%M%S}Z.{ext}"


def write_parquet(df: pd.DataFrame, entity: str, source: str) -> str:
    """Add lineage columns and land `df` as one Parquet file. Refuses to land an empty frame."""
    if df.empty:
        raise ValueError(f"Refusing to land an empty file for '{entity}'")
    ts = utc_now()
    out = df.assign(source=source, ingested_at=pd.Timestamp(ts))
    path = landing_path(entity, "parquet", ts)
    # Spark can't read nanosecond Parquet timestamps (the pandas default), so store microseconds
    out.to_parquet(path, index=False, coerce_timestamps="us", allow_truncated_timestamps=True)
    print(f"landed {len(out):,} rows -> {path}")
    return path


def write_text(text: str, entity: str, ext: str) -> str:
    """Land a raw text payload (e.g. an API's CSV response) exactly as received."""
    if not text.strip():
        raise ValueError(f"Refusing to land an empty file for '{entity}'")
    path = landing_path(entity, ext)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"landed {len(text):,} chars -> {path}")
    return path
