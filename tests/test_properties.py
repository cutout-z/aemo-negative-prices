"""Property tests for calculate_monthly_stats (synthetic cent prices).

Dev-only (Hypothesis); skipped visibly where it is not installed.
"""

import sys
from collections import defaultdict
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
# 5-minute end stamps across two adjacent months (the month is of the interval START)
STAMPS = pd.date_range("2025-01-30 08:05", periods=288 * 5, freq="5min")

rows_st = st.lists(
    st.tuples(
        st.integers(0, len(STAMPS) - 1),
        st.sampled_from(REGIONS),
        st.integers(-20_000, 5_000),  # whole cents: -$200.00 .. $50.00
    ),
    min_size=1,
    max_size=300,
)


@given(rows=rows_st)
def test_threshold_counts_and_percentages(rows):
    df = pd.DataFrame({
        "SETTLEMENTDATE": [STAMPS[i] for i, _, _ in rows],
        "REGIONID": [r for _, r, _ in rows],
        "RRP": [c / 100 for _, _, c in rows],
    })
    out = calculate_monthly_stats(df)

    # independent expectation, in integer cents, keyed by (region, month of interval start)
    cents_by_key = defaultdict(list)
    for i, region, c in rows:
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
