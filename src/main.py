"""CLI orchestrator for AEMO negative price analysis."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from . import config
from .download import download_month, download_range, get_latest_available_month
from .analyse import analyse_month
from .excel_output import generate_all_workbooks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_summary() -> pd.DataFrame | None:
    """Load existing summary.csv if it exists and is valid."""
    summary_path = PROJECT_ROOT / config.SUMMARY_CSV
    if not summary_path.exists():
        return None
    try:
        df = pd.read_csv(summary_path)
        if df.empty or "YEAR_MONTH" not in df.columns:
            logger.warning("summary.csv is empty or malformed, will do full refresh")
            return None
        return df
    except Exception as e:
        logger.warning(f"Corrupt summary.csv ({e}), falling back to full refresh")
        return None


def save_summary(df: pd.DataFrame):
    """Save summary DataFrame to CSV."""
    summary_path = PROJECT_ROOT / config.SUMMARY_CSV
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(summary_path, index=False)
    logger.info(f"Saved summary.csv ({len(df)} rows)")


def get_existing_months(summary: pd.DataFrame | None) -> set[str]:
    """Get set of already-processed YEAR_MONTH values."""
    if summary is None:
        return set()
    return set(summary["YEAR_MONTH"].unique())


def months_in_range(start_year: int, start_month: int,
                    end_year: int, end_month: int) -> list[tuple[int, int]]:
    """Generate list of (year, month) tuples in range inclusive."""
    result = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        result.append((y, m))
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return result


def _month_labels(months: list[tuple[int, int]], months_back: int) -> set[str]:
    if months_back <= 0:
        return set()
    return {f"{y}-{m:02d}" for y, m in months[-months_back:]}


def _assert_settled_history_unchanged(
    before: pd.DataFrame | None,
    after: pd.DataFrame,
    mutable_months: set[str],
) -> None:
    """Abort normal runs if settled historical month statistics change."""
    if before is None or before.empty or after.empty:
        return

    key_cols = ["REGIONID", "YEAR_MONTH"]
    columns = [c for c in before.columns if c in after.columns]
    if not all(c in columns for c in key_cols):
        return

    before_protected = before[~before["YEAR_MONTH"].isin(mutable_months)][columns]
    after_protected = after[after["YEAR_MONTH"].isin(before_protected["YEAR_MONTH"])][columns]
    before_protected = before_protected.sort_values(key_cols).reset_index(drop=True)
    after_protected = after_protected.sort_values(key_cols).reset_index(drop=True)

    try:
        assert_frame_equal(before_protected, after_protected, check_dtype=False)
    except AssertionError as exc:
        raise RuntimeError(
            "Negative price run attempted to change settled months outside the "
            "mutable window. Use --full-refresh only for deliberate audited rewrites."
        ) from exc

    logger.info(
        "Settled-history guard: %d protected region-month rows unchanged",
        len(before_protected),
    )


def run(full_refresh: bool = False, months_back: int = 1):
    """Main execution flow."""
    cache_dir = str(PROJECT_ROOT / config.DATA_DIR)
    output_dir = str(PROJECT_ROOT / config.OUTPUT_DIR)

    # Step 1: Load existing summary
    summary = None if full_refresh else load_summary()
    settled_before = summary.copy() if summary is not None and not full_refresh else None
    existing_months = get_existing_months(summary)

    if full_refresh:
        logger.info("Full refresh mode — will re-download all data from May 2019")
    elif summary is not None:
        logger.info(f"Loaded summary.csv with {len(existing_months)} months of data")
    else:
        logger.info("No existing summary found — will do initial full download")

    # Step 2: Probe AEMO for latest available month
    latest = get_latest_available_month()
    if latest is None:
        logger.error("Cannot determine latest available month. Exiting.")
        sys.exit(1)

    latest_year, latest_month = latest
    today = datetime.now().date()
    if (latest_year, latest_month) == (today.year, today.month):
        if today.month == 1:
            latest_year, latest_month = today.year - 1, 12
        else:
            latest_year, latest_month = today.year, today.month - 1
        logger.info(f"Current month in progress — capping at {latest_year}-{latest_month:02d}")

    # Step 3: Determine which months to process
    all_months = months_in_range(
        config.START_DATE.year, config.START_DATE.month,
        latest_year, latest_month,
    )
    force_months = _month_labels(all_months, months_back)
    if force_months:
        logger.info("Mutable window: %s", ", ".join(sorted(force_months)))

    if full_refresh:
        months_to_process = all_months
    else:
        months_to_process = [
            (y, m) for y, m in all_months
            if f"{y}-{m:02d}" not in existing_months or f"{y}-{m:02d}" in force_months
        ]

    if not months_to_process:
        logger.info("Already up to date — no new months to process.")
        # Still regenerate Excel in case format changed
        if summary is not None and not summary.empty:
            generate_all_workbooks(summary, output_dir)
        return

    logger.info(f"Processing {len(months_to_process)} month(s): "
                f"{months_to_process[0][0]}-{months_to_process[0][1]:02d} to "
                f"{months_to_process[-1][0]}-{months_to_process[-1][1]:02d}")

    # Step 4: Download and analyse each month
    new_results = []
    for year, month in months_to_process:
        try:
            ym = f"{year}-{month:02d}"
            raw_df = download_month(
                year,
                month,
                cache_dir,
                force=(not full_refresh and ym in force_months),
            )
            if raw_df.empty:
                logger.warning(f"No data for {year}-{month:02d}, skipping")
                continue
            stats = analyse_month(raw_df)
            new_results.append(stats)
        except Exception as e:
            logger.error(f"Failed to process {year}-{month:02d}: {e}")
            continue

    # Step 5: Merge with existing summary
    if new_results:
        new_summary = pd.concat(new_results, ignore_index=True)

        if summary is not None and not full_refresh:
            summary = pd.concat([summary, new_summary], ignore_index=True)
            # Remove any duplicates (prefer new data)
            summary = summary.drop_duplicates(
                subset=["REGIONID", "YEAR_MONTH"], keep="last"
            )
        else:
            summary = new_summary

        summary = summary.sort_values(["REGIONID", "YEAR_MONTH"]).reset_index(drop=True)
    elif summary is None:
        logger.error("No data was successfully processed.")
        sys.exit(1)

    if not full_refresh:
        _assert_settled_history_unchanged(settled_before, summary, force_months)

    # Step 6: Save summary and generate Excel
    save_summary(summary)
    generate_all_workbooks(summary, output_dir)

    logger.info("Done.")


def main():
    parser = argparse.ArgumentParser(description="AEMO Negative Electricity Price Analysis")
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Re-download all data from May 2019 (default: incremental update)",
    )
    parser.add_argument(
        "--months-back",
        type=int,
        default=1,
        help="Number of recent complete months to reprocess in incremental mode",
    )
    args = parser.parse_args()
    run(full_refresh=args.full_refresh, months_back=args.months_back)


if __name__ == "__main__":
    main()
