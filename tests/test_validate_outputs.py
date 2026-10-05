"""Each validator check must be able to fail (synthetic summaries, no network)."""

import calendar
from datetime import date

import pandas as pd
import pytest

import validate_outputs as v

TODAY = date(2020, 4, 15)  # latest complete month in the fixture: 2020-03
MONTHS = [str(p) for p in pd.period_range("2019-05", "2020-03", freq="M")]  # incl. Feb 2020 (29 days)


def _row(region: str, ym: str, total: int | None = None, counts: list[int] | None = None) -> dict:
    y, m = map(int, ym.split("-"))
    total = calendar.monthrange(y, m)[1] * 96 if total is None else total
    if counts is None:
        base = (len(region) * 37 + m * 53) % (total // 2)
        counts = [max(base - i * (base // 9 + 1), 0) for i in range(len(v.THRESHOLDS))]
    row = {"REGIONID": region, "YEAR_MONTH": ym, "total_daylight_intervals": total}
    for suffix, count in zip(v.THRESHOLDS, counts):
        row[f"count_below_{suffix}"] = count
        row[f"pct_below_{suffix}"] = round(count / total * 100, 2)
    return row


def _summary(months=MONTHS) -> pd.DataFrame:
    return pd.DataFrame([_row(r, ym) for r in v.REGIONS for ym in months])


def _replace(df: pd.DataFrame, region: str, ym: str, **kwargs) -> pd.DataFrame:
    df = df.copy()
    idx = df.index[(df.REGIONID == region) & (df.YEAR_MONTH == ym)][0]
    for col, val in _row(region, ym, **kwargs).items():
        df.at[idx, col] = val
    return df


def _errors(df: pd.DataFrame) -> list[str]:
    return v.validate_summary(df, today=TODAY)


def _fails_with(df: pd.DataFrame, fragment: str):
    errors = _errors(df)
    assert any(fragment in e for e in errors), errors


def test_clean_fixture_passes():
    assert _errors(_summary()) == []


# --- The five cases the logic-pass audit proved the old validator accepted ---

def test_four_days_missing_in_two_months():
    df = _replace(_summary(), "QLD1", "2019-07", total=27 * 96)  # 2,592
    df = _replace(df, "QLD1", "2019-08", total=27 * 96)
    _fails_with(df, "total_daylight_intervals != days_in_month")


def test_total_inflated_to_3125():
    _fails_with(_replace(_summary(), "SA1", "2019-10", total=3125), "total_daylight_intervals != days_in_month")


def test_whole_month_removed_for_all_regions():
    df = _summary()
    _fails_with(df[df.YEAR_MONTH != "2019-12"], "missing months")


def test_one_region_missing_latest_month():
    df = _summary()
    df = df[~((df.REGIONID == "TAS1") & (df.YEAR_MONTH == "2020-03"))]
    _fails_with(df, "TAS1 lacks months other regions have")


def test_pct_inconsistent_with_count():
    df = _replace(_summary(), "NSW1", "2019-05", counts=[0] * 9)
    df.loc[(df.REGIONID == "NSW1") & (df.YEAR_MONTH == "2019-05"), "pct_below_0"] = 55.0
    _fails_with(df, "pct_below_0 != round(count_below_0")


# --- The remaining checks ---

def test_pct_off_by_one_hundredth():
    df = _summary()
    df.loc[3, "pct_below_neg20"] = round(df.loc[3, "pct_below_neg20"] + 0.01, 2)
    _fails_with(df, "pct_below_neg20 != round(")


def test_count_above_total():
    df = _replace(_summary(), "VIC1", "2019-09", counts=[2881] * 9)
    _fails_with(df, "count_below_0 outside [0, total]")


def test_negative_count():
    df = _replace(_summary(), "VIC1", "2019-09", counts=[5, 4, 3, 2, 1, 0, 0, 0, -1])
    _fails_with(df, "count_below_neg80 outside [0, total]")


def test_thresholds_must_be_non_increasing():
    df = _replace(_summary(), "SA1", "2019-06", counts=[10, 12, 8, 6, 4, 2, 1, 0, 0])
    _fails_with(df, "Threshold ordering violated: count_below_0 < count_below_neg10")


def test_region_must_start_in_may_2019():
    df = _summary()
    _fails_with(df[~((df.REGIONID == "NSW1") & (df.YEAR_MONTH == "2019-05"))], "NSW1 starts at 2019-06")


def test_gap_in_one_region():
    df = _summary()
    _fails_with(df[~((df.REGIONID == "VIC1") & (df.YEAR_MONTH == "2019-11"))], "VIC1 has 1 missing months")


def test_latest_month_in_the_future():
    df = _summary(MONTHS + ["2020-04"])
    _fails_with(df, "Latest month 2020-04 is not a complete past month")


def test_missing_region():
    df = _summary()
    _fails_with(df[df.REGIONID != "TAS1"], "Region TAS1 missing")


def test_unexpected_region():
    df = pd.concat([_summary(), pd.DataFrame([_row("SNOWY1", m) for m in MONTHS])], ignore_index=True)
    _fails_with(df, "Unexpected regions")


def test_duplicate_rows():
    df = _summary()
    _fails_with(pd.concat([df, df.iloc[[0]]], ignore_index=True), "duplicate region/month rows")


def test_malformed_month_label():
    df = _summary()
    df.loc[0, "YEAR_MONTH"] = "2019/05"
    _fails_with(df, "Malformed YEAR_MONTH")


def test_empty_cell():
    df = _summary()
    df.loc[0, "count_below_neg30"] = None
    _fails_with(df, "empty cells")


def test_missing_column():
    _fails_with(_summary().drop(columns=["pct_below_neg80"]), "Missing columns")


def test_empty_summary():
    _fails_with(_summary().iloc[0:0], "summary.csv is empty")


# --- File-level checks ---

def _write_outputs(tmp_path, df, workbooks=True):
    df.to_csv(tmp_path / "summary.csv", index=False)
    if workbooks:
        for name in [*v.REGION_NAMES.values(), "All_States"]:
            (tmp_path / f"{name}_negative_prices.xlsx").write_bytes(b"")


def test_validate_reads_csv_round_trip(tmp_path):
    _write_outputs(tmp_path, _summary())
    assert v.validate(tmp_path, today=TODAY) == []


def test_validate_requires_workbooks(tmp_path):
    _write_outputs(tmp_path, _summary(), workbooks=False)
    errors = v.validate(tmp_path, today=TODAY)
    assert "All_States_negative_prices.xlsx does not exist" in errors
    assert "NSW_negative_prices.xlsx does not exist" in errors


def test_validate_requires_summary(tmp_path):
    assert v.validate(tmp_path, today=TODAY) == ["summary.csv does not exist"]


def test_main_exit_code(tmp_path):
    _write_outputs(tmp_path, _summary().iloc[0:0])
    assert v.main(["--outputs-dir", str(tmp_path)]) == 1
