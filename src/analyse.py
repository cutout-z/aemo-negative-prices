"""Threshold analysis for negative electricity prices."""

import logging

import pandas as pd

from . import config

logger = logging.getLogger(__name__)


def filter_daylight_hours(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only intervals within daylight hours (08:00–16:00 AEST market time).

    NEM runs on AEST year-round. NEMOSIS returns SETTLEMENTDATE in AEST.
    """
    df = df.copy()
    df["hour"] = df["SETTLEMENTDATE"].dt.hour
    daylight = df[
        (df["hour"] >= config.DAYLIGHT_START_HOUR)
        & (df["hour"] < config.DAYLIGHT_END_HOUR)
    ].drop(columns=["hour"])
    return daylight


def calculate_monthly_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate percentage of daylight intervals below each threshold.

    Input: DataFrame with [SETTLEMENTDATE, REGIONID, RRP] filtered to daylight hours.
    Output: DataFrame with columns:
        REGIONID, YEAR_MONTH, total_daylight_intervals,
        count_below_0, pct_below_0, count_below_neg10, pct_below_neg10, ...
    """
    df = df.copy()
    df["YEAR_MONTH"] = df["SETTLEMENTDATE"].dt.to_period("M").astype(str)

    grouped = df.groupby(["REGIONID", "YEAR_MONTH"])

    rows = []
    for (region, year_month), group in grouped:
        total = len(group)
        row = {
            "REGIONID": region,
            "YEAR_MONTH": year_month,
            "total_daylight_intervals": total,
        }

        for threshold in config.THRESHOLDS:
            count = (group["RRP"] < threshold).sum()
            pct = round(count / total * 100, 2) if total > 0 else 0.0
            suffix = _threshold_suffix(threshold)
            row[f"count_below_{suffix}"] = int(count)
            row[f"pct_below_{suffix}"] = pct

        # Log warning if interval count is unexpected
        _check_interval_count(region, year_month, total)

        rows.append(row)

    result = pd.DataFrame(rows)

    if not result.empty:
        result = result.sort_values(["REGIONID", "YEAR_MONTH"]).reset_index(drop=True)

    return result


def _threshold_suffix(threshold: int) -> str:
    """Convert threshold to column suffix: 0 -> '0', -10 -> 'neg10'."""
    if threshold == 0:
        return "0"
    return f"neg{abs(threshold)}"


def _check_interval_count(region: str, year_month: str, total: int):
    """Log warning if interval count is outside expected range."""
    # Expected: 96 intervals/day × 28-31 days = 2688-2976
    if total < 2600 or total > 3100:
        logger.warning(
            f"Unexpected interval count for {region} {year_month}: "
            f"{total} (expected ~2688-2976)"
        )


def analyse_month(df: pd.DataFrame) -> pd.DataFrame:
    """Full pipeline: filter to daylight hours, then calculate stats."""
    daylight = filter_daylight_hours(df)
    return calculate_monthly_stats(daylight)
