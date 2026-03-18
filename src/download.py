"""Data acquisition from AEMO via NEMOSIS."""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from nemosis import dynamic_data_compiler

from . import config

logger = logging.getLogger(__name__)


def get_latest_available_month() -> tuple[int, int] | None:
    """Probe AEMO directory listing to find the newest published month.

    Returns (year, month) or None if probing fails.
    """
    now = datetime.now()

    # Try current month first, then work backwards up to 3 months
    for months_back in range(0, 4):
        probe_date = now - timedelta(days=30 * months_back)
        year = probe_date.year
        month = probe_date.month

        # AEMO directory structure: YYYY/MMYYYY/
        url = f"{config.NEMWEB_BASE_URL}{year:04d}/MMSDM_{year:04d}_{month:02d}/"

        for attempt in range(config.MAX_RETRIES):
            try:
                resp = requests.head(url, timeout=15, allow_redirects=True)
                if resp.status_code == 200:
                    logger.info(f"Latest available month: {year}-{month:02d}")
                    return (year, month)
                elif resp.status_code == 404:
                    break  # This month doesn't exist, try earlier
                else:
                    logger.warning(f"Unexpected status {resp.status_code} for {url}")
                    break
            except requests.RequestException as e:
                if attempt < config.MAX_RETRIES - 1:
                    time.sleep(config.RETRY_BACKOFF * (attempt + 1))
                else:
                    logger.error(f"Failed to probe {url}: {e}")

    logger.error("Could not determine latest available month from AEMO")
    return None


def download_month(year: int, month: int, cache_dir: str) -> pd.DataFrame:
    """Download DISPATCHPRICE data for a single month via NEMOSIS.

    Returns filtered DataFrame with columns [SETTLEMENTDATE, REGIONID, RRP].
    """
    # NEMOSIS needs start/end as strings: "YYYY/MM/DD HH:MM:SS"
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    start_str = start.strftime("%Y/%m/%d %H:%M:%S")
    end_str = end.strftime("%Y/%m/%d %H:%M:%S")

    logger.info(f"Downloading {year}-{month:02d} via NEMOSIS...")

    for attempt in range(config.MAX_RETRIES):
        try:
            df = dynamic_data_compiler(
                start_time=start_str,
                end_time=end_str,
                table_name=config.NEMOSIS_TABLE,
                raw_data_location=cache_dir,
                fformat="feather",
                keep_csv=False,
            )
            break
        except Exception as e:
            if attempt < config.MAX_RETRIES - 1:
                wait = config.RETRY_BACKOFF * (attempt + 1)
                logger.warning(f"Download failed (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"Failed to download {year}-{month:02d} after {config.MAX_RETRIES} attempts: {e}")

    if df.empty:
        logger.warning(f"No data returned for {year}-{month:02d}")
        return pd.DataFrame(columns=["SETTLEMENTDATE", "REGIONID", "RRP"])

    # Filter out intervention repricing (INTERVENTION == 0 means normal pricing)
    df["INTERVENTION"] = pd.to_numeric(df["INTERVENTION"], errors="coerce")
    df = df[df["INTERVENTION"] == 0].copy()

    # Ensure SETTLEMENTDATE is datetime
    df["SETTLEMENTDATE"] = pd.to_datetime(df["SETTLEMENTDATE"])

    # Ensure RRP is numeric
    df["RRP"] = pd.to_numeric(df["RRP"], errors="coerce")

    # Keep only needed columns
    df = df[["SETTLEMENTDATE", "REGIONID", "RRP"]].copy()

    logger.info(f"Downloaded {len(df):,} rows for {year}-{month:02d}")
    return df


def download_range(start_year: int, start_month: int,
                   end_year: int, end_month: int,
                   cache_dir: str) -> pd.DataFrame:
    """Download data for a range of months. Returns concatenated DataFrame."""
    frames = []
    current = datetime(start_year, start_month, 1)
    end = datetime(end_year, end_month, 1)

    while current <= end:
        df = download_month(current.year, current.month, cache_dir)
        if not df.empty:
            frames.append(df)
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame(columns=["SETTLEMENTDATE", "REGIONID", "RRP"])
