"""Unit tests for src.analyse (synthetic data, no network)."""

import pandas as pd
import pytest

from src import config
from src.analyse import analyse_month, calculate_monthly_stats, filter_daylight_hours


def _frame(stamps, rrp=-1.0, region="QLD1"):
    """DISPATCHPRICE-shaped frame: SETTLEMENTDATE is the interval END."""
    stamps = list(stamps)
    prices = rrp if isinstance(rrp, list) else [rrp] * len(stamps)
    return pd.DataFrame({
        "SETTLEMENTDATE": pd.to_datetime(stamps),
        "REGIONID": region,
        "RRP": prices,
    })


def _day_of_stamps(day: str) -> list[pd.Timestamp]:
    """All 288 interval-end stamps of one day: 00:05 .. 24:00 (next day 00:00)."""
    start = pd.Timestamp(day)
    return list(pd.date_range(start + pd.Timedelta(minutes=5), periods=288, freq="5min"))


# --- H1: daylight window classified by interval start -------------------------

@pytest.mark.parametrize(
    "end_stamp, kept",
    [
        ("2024-03-10 07:55", False),  # 07:50-07:55
        ("2024-03-10 08:00", False),  # 07:55-08:00 -- before the window
        ("2024-03-10 08:05", True),   # 08:00-08:05 -- first daylight interval
        ("2024-03-10 12:00", True),
        ("2024-03-10 15:55", True),
        ("2024-03-10 16:00", True),   # 15:55-16:00 -- last daylight interval
        ("2024-03-10 16:05", False),  # 16:00-16:05 -- after the window
        ("2024-03-01 00:00", False),  # 23:55-00:00 on the last day of Feb
    ],
)
def test_daylight_window_uses_interval_start(end_stamp, kept):
    out = filter_daylight_hours(_frame([end_stamp]))
    assert (len(out) == 1) is kept


def test_full_day_has_96_daylight_intervals_ending_0805_to_1600():
    out = filter_daylight_hours(_frame(_day_of_stamps("2024-03-10")))
    assert len(out) == config.INTERVALS_PER_DAY == 96
    assert out["SETTLEMENTDATE"].min() == pd.Timestamp("2024-03-10 08:05")
    assert out["SETTLEMENTDATE"].max() == pd.Timestamp("2024-03-10 16:00")


def test_month_assigned_by_interval_start():
    # 00:00 on the 1st is the 23:55-00:00 interval of the previous month's last day.
    stats = calculate_monthly_stats(_frame(["2024-03-01 00:00", "2024-03-01 00:05"]))
    assert dict(zip(stats["YEAR_MONTH"], stats["total_daylight_intervals"])) == {
        "2024-02": 1,
        "2024-03": 1,
    }


def test_analyse_month_counts_window_edges():
    # Negative only at 08:00 (outside) and 16:00 (inside) end stamps.
    stamps = _day_of_stamps("2024-03-10")
    prices = [
        -5.0 if s in (pd.Timestamp("2024-03-10 08:00"), pd.Timestamp("2024-03-10 16:00")) else 50.0
        for s in stamps
    ]
    stats = analyse_month(_frame(stamps, prices))
    row = stats.iloc[0]
    assert row["YEAR_MONTH"] == "2024-03"
    assert row["total_daylight_intervals"] == 96
    assert row["count_below_0"] == 1
