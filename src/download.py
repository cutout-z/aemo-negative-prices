"""Data acquisition from AEMO via NEMOSIS."""

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from nemosis import dynamic_data_compiler

from . import config

logger = logging.getLogger(__name__)


# AEMO answers a missing month directory with a 404, or by redirecting to its
# /404 page, which Cloudflare may itself serve as a 403 (or as a 200 "soft 404").
_NOT_FOUND_PAGE = re.compile(r"/404(\.[a-z]+)?/?$", re.IGNORECASE)


def _not_published(resp) -> bool:
    """True only when nemweb says the month does not exist: a 404, or a redirect to /404.

    A redirect counts whatever the /404 page itself answers (403, 200, ...). Every
    hop is checked, so a /404 page that redirects again is still recognised.
    """
    if resp.status_code == 404:
        return True
    return bool(resp.history) and any(
        _NOT_FOUND_PAGE.search(urlparse(hop.url).path) for hop in [*resp.history, resp]
    )


def get_latest_available_month() -> tuple[int, int] | None:
    """Probe AEMO directory listing to find the newest published month.

    Only a "not found" answer (404, or a redirect to AEMO's /404 page) means a
    month is not published, and the probe then steps back one month. Any other
    answer (a 403 or 5xx on the month itself, a timeout) is retried and, if it
    persists, fails the probe: returns None, so the run exits non-zero rather
    than quietly settling on an older month.

    Returns (year, month) or None if probing fails.
    """
    now = datetime.now()

    # Try the current month first, then step back one CALENDAR month at a time,
    # up to 3 months. (Stepping 30 days skipped February from 1, 2 and 31 March.)
    for months_back in range(0, 4):
        year, month = divmod(now.year * 12 + now.month - 1 - months_back, 12)
        month += 1

        # AEMO directory structure: YYYY/MMSDM_YYYY_MM/
        url = f"{config.NEMWEB_BASE_URL}{year:04d}/MMSDM_{year:04d}_{month:02d}/"

        for attempt in range(config.MAX_RETRIES):
            last = attempt == config.MAX_RETRIES - 1
            try:
                resp = requests.head(url, timeout=15, allow_redirects=True)
            except requests.RequestException as e:
                if last:
                    logger.error(f"Failed to probe {url}: {e}; not stepping back to an older month")
                    return None
                time.sleep(config.RETRY_BACKOFF * (attempt + 1))
                continue
            if _not_published(resp):
                break  # This month doesn't exist, try earlier
            if resp.status_code == 200:
                logger.info(f"Latest available month: {year}-{month:02d}")
                return (year, month)
            if last:
                logger.error(
                    f"Unexpected status {resp.status_code} for {url} (final URL {resp.url}); "
                    "not stepping back to an older month"
                )
                return None
            logger.warning(f"Unexpected status {resp.status_code} for {url}, retrying")
            time.sleep(config.RETRY_BACKOFF * (attempt + 1))

    logger.error("Could not determine latest available month from AEMO")
    return None


def download_month(year: int, month: int, cache_dir: str, *, force: bool = False) -> pd.DataFrame:
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

    action = "Re-downloading" if force else "Downloading"
    logger.info(f"{action} {year}-{month:02d} via NEMOSIS...")

    for attempt in range(config.MAX_RETRIES):
        try:
            df = dynamic_data_compiler(
                start_time=start_str,
                end_time=end_str,
                table_name=config.NEMOSIS_TABLE,
                raw_data_location=cache_dir,
                fformat="feather",
                keep_csv=False,
                rebuild=force,
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
