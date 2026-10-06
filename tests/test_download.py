"""src.download.get_latest_available_month against a stubbed nemweb (no network)."""

import re
from datetime import datetime

import pytest

from src import download


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code


def _probe(monkeypatch, today: datetime, published: tuple[int, int]):
    """Run the probe on ``today`` with every month up to ``published`` on nemweb.

    Returns (result, [(year, month) probed, in order]).
    """
    probed = []

    def head(url, **kwargs):
        y, m = map(int, re.search(r"MMSDM_(\d{4})_(\d{2})/$", url).groups())
        probed.append((y, m))
        return _Resp(200 if (y, m) <= published else 404)

    class _Today(datetime):
        @classmethod
        def now(cls, tz=None):
            return today

    monkeypatch.setattr(download.requests, "head", head)
    monkeypatch.setattr(download, "datetime", _Today)
    return download.get_latest_available_month(), probed


# --- L3: the probe stepped back 30 days at a time, so on these days it jumped
# from March straight to January and never asked for February.

@pytest.mark.parametrize("today", [
    datetime(2027, 3, 1),
    datetime(2027, 3, 2),
    datetime(2027, 3, 31),
    datetime(2028, 3, 1),   # leap year: 1 Mar - 30 days = 31 Jan
])
def test_probe_finds_february_in_early_and_late_march(monkeypatch, today):
    result, probed = _probe(monkeypatch, today, published=(today.year, 2))
    assert result == (today.year, 2)
    assert probed == [(today.year, 3), (today.year, 2)]


@pytest.mark.parametrize("today", [
    datetime(2026, 1, 1), datetime(2026, 1, 31), datetime(2026, 3, 1), datetime(2026, 3, 31),
    datetime(2026, 5, 31), datetime(2026, 7, 31), datetime(2026, 10, 31), datetime(2026, 12, 31),
])
def test_probe_steps_one_calendar_month_at_a_time(monkeypatch, today):
    # Nothing published: every probe 404s, so all four months are asked for.
    result, probed = _probe(monkeypatch, today, published=(1900, 1))
    assert result is None
    y, m = today.year, today.month
    want = []
    for _ in range(4):
        want.append((y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    assert probed == want


def test_probe_returns_current_month_when_published(monkeypatch):
    result, probed = _probe(monkeypatch, datetime(2026, 10, 6), published=(2026, 10))
    assert result == (2026, 10)
    assert probed == [(2026, 10)]
