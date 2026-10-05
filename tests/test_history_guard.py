"""Settled-history guard: compares against the COMMITTED summary (no network)."""

import logging
import subprocess

import numpy as np
import pandas as pd
import pytest

from src import config
from src import main as M
from src.analyse import analyse_month


# --- synthetic raw data and a fake NEMOSIS download ---------------------------

def _raw_month(year: int, month: int) -> pd.DataFrame:
    """Daylight DISPATCHPRICE rows (end stamps 08:05..16:00) for the 5 regions."""
    days = pd.Period(f"{year}-{month:02d}", freq="M").days_in_month
    stamps = [
        pd.Timestamp(year, month, d, 8, 5) + pd.Timedelta(minutes=5 * i)
        for d in range(1, days + 1)
        for i in range(96)
    ]
    frames = []
    for k, region in enumerate(config.REGIONS):
        rng = np.random.default_rng(year * 100 + month * 7 + k)
        frames.append(pd.DataFrame({
            "SETTLEMENTDATE": stamps,
            "REGIONID": region,
            "RRP": rng.uniform(-90, 60, len(stamps)).round(5),
        }))
    return pd.concat(frames, ignore_index=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A git repo whose committed outputs/summary.csv covers 2019-05..2019-08."""
    git = ["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    monkeypatch.setattr(M, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(M, "download_month", lambda y, m, cache, force=False: _raw_month(y, m))
    monkeypatch.setattr(M, "generate_all_workbooks", lambda summary, out: None)
    latest = {"value": (2019, 8)}
    monkeypatch.setattr(M, "get_latest_available_month", lambda: latest["value"])
    (tmp_path / "data").mkdir()

    M.run(full_refresh=True)  # no committed baseline yet: guard skipped
    subprocess.run([*git, "add", "outputs/summary.csv"], check=True)
    subprocess.run([*git, "commit", "-qm", "publish"], check=True)

    class Repo:
        root = tmp_path
        summary = tmp_path / "outputs" / "summary.csv"
        set_latest = staticmethod(lambda y, m: latest.update(value=(y, m)))

        @staticmethod
        def committed() -> str:
            return subprocess.run([*git, "show", "HEAD:outputs/summary.csv"],
                                  capture_output=True, text=True, check=True).stdout

    return Repo


def _bump(path, region, ym, col="count_below_0"):
    df = pd.read_csv(path)
    df.loc[(df.REGIONID == region) & (df.YEAR_MONTH == ym), col] += 1
    df.to_csv(path, index=False)


# --- load_baseline -------------------------------------------------------------

def test_baseline_is_the_committed_file_not_the_working_tree(repo):
    _bump(repo.summary, "SA1", "2019-06")
    baseline = M.load_baseline(None, repo.root)
    working = pd.read_csv(repo.summary)
    assert not baseline.equals(working)
    assert baseline.to_csv(index=False) == repo.committed()


def test_baseline_from_explicit_path(repo, tmp_path):
    other = tmp_path / "published.csv"
    other.write_text(repo.committed())
    assert M.load_baseline(str(other), repo.root).to_csv(index=False) == repo.committed()


def test_no_committed_summary_skips_guard(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        assert M.load_baseline(None, tmp_path) is None
    assert "No committed" in caplog.text


# --- the guard in real runs ----------------------------------------------------

def test_incremental_run_unchanged_history_passes(repo):
    before = repo.summary.read_text()
    M.run(months_back=2)
    assert repo.summary.read_text() == before


def test_incremental_run_refuses_changed_settled_month(repo):
    # The audit's demonstration: a settled month altered in the working tree is
    # never reprocessed, so the old guard compared the file with itself.
    _bump(repo.summary, "SA1", "2019-06")
    with pytest.raises(RuntimeError, match=r"SA1 2019-06: count_below_0"):
        M.run(months_back=2)


def test_mutable_window_may_change(repo):
    _bump(repo.summary, "SA1", "2019-08")  # inside --months-back 2: recomputed
    M.run(months_back=2)
    assert repo.summary.read_text() == repo.committed()


def test_removed_settled_month_is_refused(repo, monkeypatch):
    real = M.download_month

    def without_tas_may(y, m, cache, force=False):
        df = real(y, m, cache)
        return df[df.REGIONID != "TAS1"] if (y, m) == (2019, 5) else df

    monkeypatch.setattr(M, "download_month", without_tas_may)
    with pytest.raises(RuntimeError, match=r"TAS1 2019-05: row removed"):
        M.run(full_refresh=True)


def test_full_refresh_method_change_needs_reason(repo, monkeypatch, caplog):
    # A method change (every price $1 lower) alters every settled month.
    monkeypatch.setattr(M, "analyse_month", lambda df: analyse_month(df.assign(RRP=df["RRP"] - 1.0)))
    with pytest.raises(RuntimeError, match="--allow-history-rewrite"):
        M.run(full_refresh=True)
    assert repo.summary.read_text() == repo.committed()  # nothing written

    with caplog.at_level(logging.WARNING):
        M.run(full_refresh=True, allow_history_rewrite="H1 interval-start window")
    assert "HISTORY REWRITE ALLOWED: H1 interval-start window" in caplog.text
    assert repo.summary.read_text() != repo.committed()


def test_new_month_is_not_a_history_change(repo):
    repo.set_latest(2019, 9)
    M.run(months_back=1)
    df = pd.read_csv(repo.summary)
    assert df.YEAR_MONTH.max() == "2019-09"


def test_settled_history_changes_reports_columns():
    base = pd.DataFrame({"REGIONID": ["SA1", "SA1"], "YEAR_MONTH": ["2019-05", "2019-06"],
                         "count_below_0": [3, 4], "pct_below_0": [0.1, 0.13]})
    after = base.copy()
    after.loc[0, "pct_below_0"] = 0.11
    assert M._settled_history_changes(base, after, {"2019-06"}) == [
        "SA1 2019-05: pct_below_0 0.1 -> 0.11"
    ]
    assert M._settled_history_changes(base, after, {"2019-05"}) == []
    assert M._settled_history_changes(None, after, set()) == []
