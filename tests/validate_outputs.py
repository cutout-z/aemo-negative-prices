"""Post-pipeline validation for AEMO Negative Prices.

Checks summary.csv and regional Excel workbooks for data integrity
before committing to the repository. Exits non-zero on any failure.
"""

import sys
from pathlib import Path

import pandas as pd

OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
REGIONS = ["NSW1", "QLD1", "VIC1", "SA1", "TAS1"]
THRESHOLDS = ["0", "neg10", "neg20", "neg30", "neg40", "neg50", "neg60", "neg70", "neg80"]
REGION_NAMES = {"NSW1": "NSW", "QLD1": "QLD", "VIC1": "VIC", "SA1": "SA", "TAS1": "TAS"}

errors = []


def check(condition, msg):
    if not condition:
        errors.append(msg)
        print(f"  FAIL: {msg}")
    return condition


def validate():
    summary_path = OUTPUTS_DIR / "summary.csv"
    check(summary_path.exists(), "summary.csv does not exist")
    if not summary_path.exists():
        return

    df = pd.read_csv(summary_path)
    print(f"summary.csv: {len(df)} rows")

    # --- Structure ---
    check(len(df) > 0, "summary.csv is empty")
    check("REGIONID" in df.columns, "Missing REGIONID column")
    check("YEAR_MONTH" in df.columns, "Missing YEAR_MONTH column")

    # --- All 5 regions present ---
    regions_present = set(df["REGIONID"].unique())
    for r in REGIONS:
        check(r in regions_present, f"Region {r} missing from summary.csv")

    # --- Interval counts in expected range (daylight hours: 2600-3100) ---
    if "total_daylight_intervals" in df.columns:
        bad_intervals = df[
            (df["total_daylight_intervals"] < 2500) | (df["total_daylight_intervals"] > 3200)
        ]
        check(
            len(bad_intervals) == 0,
            f"{len(bad_intervals)} rows have interval counts outside [2500, 3200]",
        )

    # --- Percentages in [0, 100] ---
    pct_cols = [c for c in df.columns if c.startswith("pct_below_")]
    for col in pct_cols:
        vals = df[col].dropna()
        check(vals.min() >= 0, f"{col} has negative values (min={vals.min():.2f})")
        check(vals.max() <= 100, f"{col} exceeds 100% (max={vals.max():.2f})")

    # --- Threshold ordering: count_below_0 >= count_below_neg10 >= ... ---
    count_cols = [f"count_below_{t}" for t in THRESHOLDS if f"count_below_{t}" in df.columns]
    if len(count_cols) >= 2:
        for i in range(len(count_cols) - 1):
            violations = df[df[count_cols[i]] < df[count_cols[i + 1]]]
            check(
                len(violations) == 0,
                f"Threshold ordering violated: {count_cols[i]} < {count_cols[i+1]} in {len(violations)} rows",
            )

    # --- Regional Excel workbooks exist ---
    for region_id, name in REGION_NAMES.items():
        xlsx_path = OUTPUTS_DIR / f"{name}_negative_prices.xlsx"
        check(xlsx_path.exists(), f"{xlsx_path.name} does not exist")

    # --- All-states workbook exists ---
    all_states_path = OUTPUTS_DIR / "All_States_negative_prices.xlsx"
    check(all_states_path.exists(), "All_States_negative_prices.xlsx does not exist")

    # --- No duplicate region/month combinations ---
    if "REGIONID" in df.columns and "YEAR_MONTH" in df.columns:
        dupes = df.duplicated(subset=["REGIONID", "YEAR_MONTH"], keep=False)
        check(dupes.sum() == 0, f"{dupes.sum()} duplicate region/month rows")


if __name__ == "__main__":
    print("Validating AEMO Negative Prices outputs...")
    validate()
    if errors:
        print(f"\n{len(errors)} validation error(s) found — aborting.")
        sys.exit(1)
    else:
        print("\nAll validations passed.")
