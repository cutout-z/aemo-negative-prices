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

# Negative price thresholds (strictly less than)
THRESHOLDS = [0, -10, -20, -30, -40, -50, -60, -70, -80]

# Analysis start date
START_DATE = datetime(2019, 5, 1)

# Daylight hours filter (AEST market time)
DAYLIGHT_START_HOUR = 8   # 08:00 inclusive
DAYLIGHT_END_HOUR = 16    # 16:00 exclusive

# Expected 5-min intervals per daylight hour
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
