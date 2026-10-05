"""Configuration for AEMO negative price analysis."""

from datetime import datetime

# NEM regions
REGIONS = ["NSW1", "QLD1", "VIC1", "SA1", "TAS1"]

# Friendly names for output files
REGION_NAMES = {
    "NSW1": "NSW",
    "QLD1": "QLD",
    "VIC1": "VIC",
    "SA1": "SA",
    "TAS1": "TAS",
}

# Negative price thresholds ($/MWh). An interval counts below a threshold when
# its RRP, rounded to whole cents (half away from zero), is strictly less than
# the threshold. So -0.004 rounds to 0.00 and is NOT below $0, while -0.005
# rounds to -0.01 and IS; likewise -10.004 is not below -$10 and -10.005 is.
# This matches AEMO's 2-dp PRICE_AND_DEMAND prices. See analyse.price_in_cents.
THRESHOLDS = [0, -10, -20, -30, -40, -50, -60, -70, -80]

# AEMO publishes DISPATCHPRICE.RRP as NUMBER(15,5): at most 5 decimal places.
RRP_DECIMALS = 5

# Analysis start date
START_DATE = datetime(2019, 5, 1)

# Daylight window (AEST market time), applied to the dispatch interval START.
# AEMO stamps each interval with SETTLEMENTDATE = interval END, so the interval
# 08:00-08:05 carries SETTLEMENTDATE 08:05. An interval is "daylight" when it
# starts in [08:00, 16:00): the first is 08:00-08:05 (stamped 08:05) and the
# last is 15:55-16:00 (stamped 16:00). Months are assigned by interval start too.
DAYLIGHT_START_HOUR = 8   # interval start 08:00 inclusive
DAYLIGHT_END_HOUR = 16    # interval start 16:00 exclusive

# Dispatch interval length and expected intervals per daylight hour
INTERVAL_MINUTES = 5
INTERVALS_PER_HOUR = 12
DAYLIGHT_HOURS = DAYLIGHT_END_HOUR - DAYLIGHT_START_HOUR
INTERVALS_PER_DAY = DAYLIGHT_HOURS * INTERVALS_PER_HOUR  # 96

# AEMO data settings
NEMWEB_BASE_URL = "https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/"
NEMOSIS_TABLE = "DISPATCHPRICE"

# Paths (relative to project root)
DATA_DIR = "data"
OUTPUT_DIR = "outputs"
SUMMARY_CSV = "outputs/summary.csv"

# Network retry settings
MAX_RETRIES = 3
RETRY_BACKOFF = 5  # seconds
