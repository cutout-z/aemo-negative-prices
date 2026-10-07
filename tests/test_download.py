"""src.download.get_latest_available_month against a stubbed nemweb (no network)."""

import re
from datetime import datetime

import pytest

from src import download


class _Resp:
    def __init__(self, status_code, url="", history=()):
        self.status_code = status_code
        self.url = url
        self.history = list(history)


def _probe(monkeypatch, today: datetime, published: tuple[int, int]):
    """Run the probe on ``today`` with every month up to ``published`` on nemweb.

    Returns (result, [(year, month) probed, in order]).
    """
    probed = []

    def head(url, **kwargs):
        y, m = map(int, re.search(r"MMSDM_(\d{4})_(\d{2})/$", url).groups())
        probed.append((y, m))
        return _Resp(200 if (y, m) <= published else 404, url)

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


# --- S2-3: a 403/5xx or a timeout on the newest month was taken as "not
# published", so the probe stepped back and the run settled, green, on an older
# month. Only a 404 (or AEMO's redirect to its /404 page) means "not published".

NOT_FOUND = "https://nemweb.com.au/404"


def _probe_with(monkeypatch, today: datetime, answer):
    """Run the probe on ``today``; ``answer(year, month, url)`` returns a _Resp or raises."""
    probed = []

    def head(url, **kwargs):
        y, m = map(int, re.search(r"MMSDM_(\d{4})_(\d{2})/$", url).groups())
        probed.append((y, m))
        return answer(y, m, url)

    class _Today(datetime):
        @classmethod
        def now(cls, tz=None):
            return today

    monkeypatch.setattr(download.requests, "head", head)
    monkeypatch.setattr(download, "datetime", _Today)
    monkeypatch.setattr(download.time, "sleep", lambda s: None)
    return download.get_latest_available_month(), probed


TODAY = datetime(2026, 11, 3)  # newest month asked for: 2026-11; 2026-10 is published
NEWEST, PUBLISHED = (2026, 11), (2026, 10)
RETRIES = download.config.MAX_RETRIES


def _published_or(newest_answer):
    def answer(y, m, url):
        if (y, m) == NEWEST:
            return newest_answer(url)
        return _Resp(200 if (y, m) <= PUBLISHED else 404, url)
    return answer


@pytest.mark.parametrize("status", [403, 500, 502, 503])
def test_error_status_on_newest_month_fails_the_probe(monkeypatch, status):
    result, probed = _probe_with(monkeypatch, TODAY, _published_or(lambda url: _Resp(status, url)))
    assert result is None
    assert probed == [NEWEST] * RETRIES  # retried, never stepped back to 2026-10


def test_timeout_on_newest_month_fails_the_probe(monkeypatch):
    def timeout(url):
        raise download.requests.Timeout("read timed out")
    result, probed = _probe_with(monkeypatch, TODAY, _published_or(timeout))
    assert result is None
    assert probed == [NEWEST] * RETRIES


def test_transient_error_is_retried(monkeypatch):
    answers = iter([_Resp(503), download.requests.ConnectionError("reset")])

    def flaky(url):
        nxt = next(answers, None)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt or _Resp(200, url)

    result, probed = _probe_with(monkeypatch, TODAY, _published_or(flaky))
    assert result == NEWEST
    assert probed == [NEWEST] * 3


@pytest.mark.parametrize("final_status", [403, 200, 404])
def test_redirect_to_aemo_404_page_means_not_published(monkeypatch, final_status):
    # AEMO sends a missing path to /404; Cloudflare may answer that page with a 403.
    def to_404(url):
        return _Resp(final_status, NOT_FOUND, history=[_Resp(302, url)])
    result, probed = _probe_with(monkeypatch, TODAY, _published_or(to_404))
    assert result == PUBLISHED
    assert probed == [NEWEST, PUBLISHED]


def test_redirect_elsewhere_with_403_fails_the_probe(monkeypatch):
    # e.g. a Cloudflare challenge page: not a "not found", so not a reason to step back.
    def challenge(url):
        return _Resp(403, "https://nemweb.com.au/cdn-cgi/challenge-platform/h/b", history=[_Resp(302, url)])
    result, probed = _probe_with(monkeypatch, TODAY, _published_or(challenge))
    assert result is None
    assert probed == [NEWEST] * RETRIES


@pytest.mark.parametrize("url, expected", [
    ("https://nemweb.com.au/404", True),
    ("https://nemweb.com.au/404/", True),
    ("https://nemweb.com.au/404.html", True),
    ("https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2026/MMSDM_2026_04/", False),
    ("https://nemweb.com.au/cdn-cgi/challenge-platform/h/b", False),
])
def test_not_published_recognises_only_the_404_page(url, expected):
    assert download._not_published(_Resp(403, url, history=[_Resp(302, "https://x/MMSDM_2026_11/")])) is expected
    assert download._not_published(_Resp(403, url)) is False  # no redirect: a plain 403
