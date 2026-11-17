"""Property tests for calculate_monthly_stats (synthetic cent prices).

Dev-only (Hypothesis); skipped visibly where it is not installed.
"""

import sys
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("hypothesis", reason="hypothesis is a dev-only dependency (requirements-dev.txt)")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import hypothesis_gate  # noqa: E402,F401  (loads the fixed profile)
from hypothesis import given, strategies as st  # noqa: E402

from src import config  # noqa: E402
from src.analyse import _threshold_suffix, calculate_monthly_stats  # noqa: E402

REGIONS = ["NSW1", "QLD1", "SA1"]
# 5-minute end stamps across a month boundary (the month is of the interval START)
STAMPS = pd.date_range("2025-01-30 08:05", periods=288 * 5, freq="5min")
# the interval stamped 00:00 on 1 Feb ran 23:55-00:00 on 31 Jan: it belongs to January
BOUNDARY = STAMPS.get_loc(pd.Timestamp("2025-02-01 00:00"))

stamp_idx = st.one_of(st.sampled_from([BOUNDARY - 1, BOUNDARY, BOUNDARY + 1]), st.integers(0, len(STAMPS) - 1))
# RRP is published to 5 decimals: draw integer units of 1e-5 $/MWh, hitting the cent-rounding edges
# (+-499/500/501 units either side of a whole cent) at and next to every threshold.
near_threshold = st.sampled_from([
    (t * 100 + dc) * 1000 + du
    for t in config.THRESHOLDS for dc in (-1, 0, 1) for du in (-501, -500, -499, -1, 0, 1, 499, 500, 501)
])
price_units = st.one_of(near_threshold, st.integers(-2_000_000, 500_000))

rows_st = st.lists(st.tuples(stamp_idx, st.sampled_from(REGIONS), price_units), min_size=50, max_size=300)


def _cents(units: int) -> int:
    """Whole cents, half away from zero, in exact decimal arithmetic."""
    return int((Decimal(units) / 1000).to_integral_value(rounding=ROUND_HALF_UP))


@given(rows=rows_st)
def test_threshold_counts_and_percentages(rows):
    df = pd.DataFrame({
        "SETTLEMENTDATE": [STAMPS[i] for i, _, _ in rows],
        "REGIONID": [r for _, r, _ in rows],
        "RRP": [u / 100_000 for _, _, u in rows],
    })
    out = calculate_monthly_stats(df)

    # independent expectation, in integer cents, keyed by (region, month of interval start)
    cents_by_key = defaultdict(list)
    for i, region, u in rows:
        c = _cents(u)
        start = STAMPS[i] - pd.Timedelta(minutes=config.INTERVAL_MINUTES)
        cents_by_key[(region, f"{start.year}-{start.month:02d}")].append(c)
    assert len(out) == len(cents_by_key)

    ordered = sorted(config.THRESHOLDS, reverse=True)  # shallowest (0) to deepest (-80)
    for _, r in out.iterrows():
        cents = cents_by_key[(r["REGIONID"], r["YEAR_MONTH"])]
        total = r["total_daylight_intervals"]
        assert total == len(cents)
        previous = None
        for t in ordered:
            suffix = _threshold_suffix(t)
            count = r[f"count_below_{suffix}"]
            assert count == sum(1 for c in cents if c < t * 100)
            assert r[f"pct_below_{suffix}"] == round(count / total * 100, 2)
            if previous is not None:
                assert count <= previous  # deeper threshold never counts more
            previous = count
