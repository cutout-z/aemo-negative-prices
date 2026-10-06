"""deploy/run-update.sh against a local bare 'origin' and a stub Python (no network)."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "deploy" / "run-update.sh"
COMMITTED = "REGIONID,YEAR_MONTH,count_below_0\nSA1,2026-06,10\n"
DIRTY = "REGIONID,YEAR_MONTH,count_below_0\nSA1,2026-06,11\n"

# Stands in for "python -m src.main ...": records its argv, the summary it would
# read as input and the --baseline file's content, then writes $NEW_SUMMARY.
STUB = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$STUB_LOG/args"
cp outputs/summary.csv "$STUB_LOG/input"
prev=""
for a in "$@"; do
  if [[ "$prev" == "--baseline" ]]; then cp "$a" "$STUB_LOG/baseline"; fi
  prev="$a"
done
printf '%s' "$NEW_SUMMARY" > outputs/summary.csv
"""

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          capture_output=True, text=True, check=True).stdout


@pytest.fixture
def lane(tmp_path):
    origin = tmp_path / "origin.git"
    seed = tmp_path / "seed"
    app = tmp_path / "app"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
    (seed / "outputs").mkdir()
    (seed / "outputs" / "summary.csv").write_text(COMMITTED)
    _git(seed, "add", ".")
    _git(seed, "commit", "-qm", "seed")
    _git(seed, "push", "-q", str(origin), "main")
    subprocess.run(["git", "clone", "-q", str(origin), str(app)], check=True)

    log = tmp_path / "log"
    log.mkdir()
    stub = tmp_path / "python"
    stub.write_text(STUB)
    stub.chmod(0o755)

    def run(new_summary, **env):
        full_env = {
            **os.environ,
            "APP_DIR": str(app), "PYTHON": str(stub), "STUB_LOG": str(log),
            "NEW_SUMMARY": new_summary, "PIPELINE_ARGS": "--months-back 2",
            "RUN_TESTS": "0", "PUSH_CHANGES": "0", "RUN_RAW_CACHE_PRUNE": "0",
            "GIT_AUTHOR_NAME": "bot", "GIT_AUTHOR_EMAIL": "bot@example.invalid",
            **env,
        }
        return subprocess.run(["bash", str(SCRIPT)], env=full_env, capture_output=True, text=True)

    class Lane:
        pass

    lane = Lane()
    lane.app, lane.log, lane.run = app, log, run
    return lane


def test_baseline_is_committed_summary_not_working_tree(lane):
    (lane.app / "outputs" / "summary.csv").write_text(DIRTY)  # left over by a failed run
    result = lane.run(COMMITTED)
    assert result.returncode == 0, result.stderr
    assert (lane.log / "baseline").read_text() == COMMITTED
    args = (lane.log / "args").read_text().split("\n")
    assert args[:5] == ["-m", "src.main", "--months-back", "2", "--baseline"]
    assert "--allow-history-rewrite" not in args
    # Output equals the committed file: nothing to publish.
    assert "No canonical summary.csv changes" in result.stdout


def test_history_rewrite_reason_is_passed_and_recorded(lane):
    result = lane.run(DIRTY, HISTORY_REWRITE_REASON="H1 interval-start window")
    assert result.returncode == 0, result.stderr
    args = (lane.log / "args").read_text().split("\n")
    i = args.index("--allow-history-rewrite")
    assert args[i + 1] == "H1 interval-start window"
    body = _git(lane.app, "log", "-1", "--format=%B")
    assert "History rewrite: H1 interval-start window" in body


def test_commit_is_labelled_with_latest_data_month(lane):
    new = COMMITTED + "SA1,2026-08,12\nSA1,2026-07,9\n"
    result = lane.run(new)
    assert result.returncode == 0, result.stderr
    assert _git(lane.app, "log", "-1", "--format=%s").strip() == "Update negative price analysis 2026-08"


def test_run_starts_from_committed_outputs_not_leftovers(lane):
    # A failed or manual run left the summary edited and a stray file in outputs/.
    (lane.app / "outputs" / "summary.csv").write_text(DIRTY)
    (lane.app / "outputs" / "stray.xlsx").write_text("left over")
    new = COMMITTED + "SA1,2026-07,9\n"
    result = lane.run(new)
    assert result.returncode == 0, result.stderr
    # The incremental run reads the committed summary, not the edited one ...
    assert (lane.log / "input").read_text() == COMMITTED
    # ... and only the pipeline's own outputs are published.
    published = _git(lane.app, "show", "--name-only", "--format=", "HEAD").split()
    assert published == ["outputs/summary.csv"]
    assert not (lane.app / "outputs" / "stray.xlsx").exists()
