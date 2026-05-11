#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/aemo-negative-prices}"
RAW_CACHE_RETENTION_DAYS="${RAW_CACHE_RETENTION_DAYS:-120}"

find "${APP_DIR}/data" -type f \( -name '*.csv' -o -name '*.zip' -o -name '*.feather' -o -name '*.parquet' \) -mtime +"${RAW_CACHE_RETENTION_DAYS}" -delete 2>/dev/null || true
find "${APP_DIR}/data" -type d -empty -delete 2>/dev/null || true
