"""Post-pipeline validation for AEMO Negative Prices.

Checks summary.csv and regional Excel workbooks for data integrity
before committing to the repository. Exits non-zero on any failure.

Usage: python tests/validate_outputs.py [--outputs-dir DIR]

Every check is exact: a region-month must have exactly days x 96 daylight
intervals, every percentage must equal round(count / total * 100, 2) (the
pipeline's formula), and the months must form one gap-free run from May 2019
to the latest complete month, identical for all five regions.

Freshness: every month that ended more than MAX_PUBLICATION_LAG_DAYS ago must
be present, so a summary AEMO has moved past fails instead of passing quietly.
"""

import argparse
import calendar
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
REGIONS = ["NSW1", "QLD1", "VIC1", "SA1", "TAS1"]
THRESHOLDS = ["0", "neg10", "neg20", "neg30", "neg40", "neg50", "neg60", "neg70", "neg80"]
REGION_NAMES = {"NSW1": "NSW", "QLD1": "QLD", "VIC1": "VIC", "SA1": "SA", "TAS1": "TAS"}
START_MONTH = "2019-05"
INTERVALS_PER_DAY = 96  # 08:00-16:00 interval starts, 12 five-minute intervals an hour

# Freshness tolerance, in days after a month's last day, by which that month must
# be in summary.csv. AEMO's monthly MMSDM archive landed 12-16 days after month
# end in 2026, 28 days at worst (Aug 2026, landed 28 Sep); 35 leaves a week over
# that worst case. index.html uses the same number for its overdue notice
# (tests/test_page.py keeps the two equal). Change it here and there together.
MAX_PUBLICATION_LAG_DAYS = 35


def latest_required_month(today: date) -> pd.Period:
    """The newest month that must be in the summary on ``today``.

    A month is required once more than MAX_PUBLICATION_LAG_DAYS days have passed
    since its last day: with 35, August (ends the 31st) is required from 6 Oct.
    """
    return pd.Period(today - timedelta(days=MAX_PUBLICATION_LAG_DAYS), freq="M") - 1


def _sample(frame: pd.DataFrame, limit: int = 5) -> str:
    keys = [f"{r.REGIONID} {r.YEAR_MONTH}" for r in frame.head(limit).itertuples()]
    more = f" (+{len(frame) - limit} more)" if len(frame) > limit else ""
    return ", ".join(keys) + more


def validate_summary(df: pd.DataFrame, today: date | None = None) -> list[str]:
    """Return a list of integrity errors in a summary.csv DataFrame (empty = valid)."""
    today = today or date.today()
    errors: list[str] = []

    def check(condition, msg):
        if not condition:
            errors.append(msg)
            print(f"  FAIL: {msg}")
        return condition

    # --- Structure ---
    if not check(len(df) > 0, "summary.csv is empty"):
        return errors
    count_cols = [f"count_below_{t}" for t in THRESHOLDS]
    pct_cols = [f"pct_below_{t}" for t in THRESHOLDS]
    required = ["REGIONID", "YEAR_MONTH", "total_daylight_intervals", *count_cols, *pct_cols]
    missing = [c for c in required if c not in df.columns]
    if not check(not missing, f"Missing columns: {missing}"):
        return errors
    nulls = df[required].isna().any(axis=1)
    if not check(not nulls.any(), f"{nulls.sum()} rows have empty cells: {_sample(df[nulls])}"):
        return errors

    # --- Exactly the 5 regions ---
    regions_present = set(df["REGIONID"].unique())
    for r in REGIONS:
        check(r in regions_present, f"Region {r} missing from summary.csv")
    extra = sorted(regions_present - set(REGIONS))
    check(not extra, f"Unexpected regions in summary.csv: {extra}")

    # --- Month labels ---
    periods = pd.to_datetime(df["YEAR_MONTH"], format="%Y-%m", errors="coerce")
    bad_labels = periods.isna()
    if not check(not bad_labels.any(), f"Malformed YEAR_MONTH in {_sample(df[bad_labels])}"):
        return errors
    months = periods.dt.to_period("M")

    # --- No duplicate region/month combinations ---
    dupes = df.duplicated(subset=["REGIONID", "YEAR_MONTH"], keep=False)
    check(dupes.sum() == 0, f"{dupes.sum()} duplicate region/month rows: {_sample(df[dupes])}")

    # --- Interval totals: exactly days_in_month x 96 ---
    expected_total = months.map(lambda p: calendar.monthrange(p.year, p.month)[1] * INTERVALS_PER_DAY)
    wrong_total = df["total_daylight_intervals"] != expected_total
    check(
        not wrong_total.any(),
        f"{wrong_total.sum()} rows have total_daylight_intervals != days_in_month x "
        f"{INTERVALS_PER_DAY}: {_sample(df[wrong_total])}",
    )

    total = df["total_daylight_intervals"]
    for c_col, p_col in zip(count_cols, pct_cols):
        # --- 0 <= count <= total ---
        bad = (df[c_col] < 0) | (df[c_col] > total)
        check(not bad.any(), f"{c_col} outside [0, total] in {bad.sum()} rows: {_sample(df[bad])}")

        # --- pct == round(count / total * 100, 2), compared exactly ---
        expected_pct = [
            round(c / t * 100, 2) if t > 0 else 0.0 for c, t in zip(df[c_col], total)
        ]
        bad = df[p_col] != pd.Series(expected_pct, index=df.index)
        check(
            not bad.any(),
            f"{p_col} != round({c_col} / total * 100, 2) in {bad.sum()} rows: {_sample(df[bad])}",
        )

    # --- Thresholds cumulative: count/pct non-increasing as the threshold deepens ---
    for cols in (count_cols, pct_cols):
        for shallow, deep in zip(cols, cols[1:]):
            bad = df[shallow] < df[deep]
            check(
                not bad.any(),
                f"Threshold ordering violated: {shallow} < {deep} in {bad.sum()} rows: {_sample(df[bad])}",
            )

    # --- Months: contiguous from START_MONTH per region, same set for every region ---
    by_region = {r: set(months[df["REGIONID"] == r]) for r in REGIONS if r in regions_present}
    start = pd.Period(START_MONTH, freq="M")
    for region, region_months in by_region.items():
        first, last = min(region_months), max(region_months)
        check(first == start, f"{region} starts at {first}, expected {start}")
        gaps = sorted(set(pd.period_range(first, last, freq="M")) - region_months)
        check(not gaps, f"{region} has {len(gaps)} missing months: {[str(p) for p in gaps[:12]]}")
    if by_region:
        union = set().union(*by_region.values())
        for region, region_months in by_region.items():
            absent = sorted(union - region_months)
            check(not absent, f"{region} lacks months other regions have: {[str(p) for p in absent[:12]]}")

    # --- Latest month is complete: strictly before the current month ---
    latest = months.max()
    current = pd.Period(today, freq="M")
    check(latest < current, f"Latest month {latest} is not a complete past month (today {today})")

    # --- Fresh: every month that ended more than MAX_PUBLICATION_LAG_DAYS ago is present ---
    required = latest_required_month(today)
    overdue_by = (today - required.end_time.date()).days
    check(
        latest >= required,
        f"Latest month {latest} is stale: {required} ended {overdue_by} days ago "
        f"(more than MAX_PUBLICATION_LAG_DAYS = {MAX_PUBLICATION_LAG_DAYS}) and is not in "
        f"summary.csv (today {today})",
    )

    return errors


def validate(outputs_dir: Path = OUTPUTS_DIR, today: date | None = None) -> list[str]:
    """Validate summary.csv and the six workbooks in outputs_dir. Returns errors."""
    outputs_dir = Path(outputs_dir)
    errors: list[str] = []

    def check(condition, msg):
        if not condition:
            errors.append(msg)
            print(f"  FAIL: {msg}")
        return condition

    summary_path = outputs_dir / "summary.csv"
    if not check(summary_path.exists(), "summary.csv does not exist"):
        return errors

    # round_trip: parse each pct exactly as written, so the equality check is exact
    df = pd.read_csv(summary_path, float_precision="round_trip")
    print(f"summary.csv: {len(df)} rows")
    errors.extend(validate_summary(df, today=today))

    # --- Regional Excel workbooks exist ---
    for name in REGION_NAMES.values():
        xlsx_path = outputs_dir / f"{name}_negative_prices.xlsx"
        check(xlsx_path.exists(), f"{xlsx_path.name} does not exist")

    # --- All-states workbook exists ---
    all_states_path = outputs_dir / "All_States_negative_prices.xlsx"
    check(all_states_path.exists(), "All_States_negative_prices.xlsx does not exist")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outputs-dir", type=Path, default=OUTPUTS_DIR)
    args = parser.parse_args(argv)

    print("Validating AEMO Negative Prices outputs...")
    errors = validate(args.outputs_dir)
    if errors:
        print(f"\n{len(errors)} validation error(s) found — aborting.")
        return 1
    print("\nAll validations passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
