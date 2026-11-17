"""Rendered-page smoke: load index.html in headless chromium, offline, with the data the repo commits.

No server and no port: page_harness routes http://aemo.test/ to this checkout, PapaParse to a vendored
copy, nav.js to an empty script, and aborts (and records) every other request.
"""

import csv
import datetime as dt
import re

import pytest

pytest.importorskip("playwright")

from page_harness import ROOT, assert_clean, loaded_page  # noqa: E402

READY = "document.querySelectorAll('#tbody tr').length > 0"


def _month(ym):
    return dt.date(int(ym[:4]), int(ym[5:7]), 1).strftime("%b %Y")


def _rows(region):
    with open(ROOT / "outputs" / "summary.csv", newline="") as f:
        return [r for r in csv.DictReader(f) if r["REGIONID"] == region]


def test_page_renders_the_committed_data_with_no_errors():
    sa = _rows("SA1")  # the page opens on SA
    latest = max(r["YEAR_MONTH"] for r in sa)
    with loaded_page(wait_for=READY) as (page, log):
        assert_clean(log)
        # four stat tiles, each led by a number (a percentage, a count or a rank), none still a skeleton
        tiles = page.locator("#kpis > div")
        assert tiles.count() == 4
        for i in range(4):
            text = tiles.nth(i).inner_text().strip()
            assert re.match(r"^[\d,.]+", text), text
        assert page.locator("#kpis .skeleton").count() == 0
        # one body row per committed SA month, filled with percentages
        assert page.locator("#tbody tr").count() == len(sa)
        assert "%" in page.locator("#tbody tr").first.inner_text()
        for sel in ("#kpis", "#table", "#tabs", "#footer"):
            box = page.locator(sel).bounding_box()
            assert box and box["height"] > 0 and page.locator(sel).is_visible(), sel
        assert page.locator("#tabs button:not([disabled])").count() == 5
        assert page.locator("#tabs .skeleton").count() == 0
        assert page.locator("#downloads a").count() >= 3
        footer = page.locator("#footer").inner_text()
        assert f"as of {_month(latest)}" in footer, footer


def test_region_switch_rerenders_the_table():
    qld = _rows("QLD1")
    with loaded_page(wait_for=READY) as (page, log):
        page.locator("#tabs button", has_text="QLD").click()
        page.wait_for_function(f"document.querySelectorAll('#tbody tr').length === {len(qld)}")
        assert_clean(log)


def test_page_renders_at_phone_width():
    with loaded_page(width=400, height=800, wait_for=READY) as (page, log):
        assert_clean(log)
        assert page.locator("#tbody tr").count() > 0
        assert page.locator("#kpis").is_visible()
