"""index.html shares the freshness tolerance with the output validator (no browser)."""

import re
from pathlib import Path

import validate_outputs as v

PAGE = Path(__file__).resolve().parent.parent / "index.html"


def test_page_overdue_threshold_matches_validator():
    found = re.findall(r"const MAX_PUBLICATION_LAG_DAYS = (\d+);", PAGE.read_text())
    assert found == [str(v.MAX_PUBLICATION_LAG_DAYS)]
