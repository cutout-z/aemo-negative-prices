#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/workspace/repos/aemo-negative-prices}"
PYTHON="${PYTHON:-${APP_DIR}/.venv/bin/python}"
PIPELINE_ARGS="${PIPELINE_ARGS:---months-back 2}"
RUN_TESTS="${RUN_TESTS:-1}"
PUSH_CHANGES="${PUSH_CHANGES:-1}"
RUN_RAW_CACHE_PRUNE="${RUN_RAW_CACHE_PRUNE:-1}"
COMMIT_MESSAGE_PREFIX="${COMMIT_MESSAGE_PREFIX:-Update negative price analysis}"
# Set only for a deliberate, audited rewrite of settled months; recorded in the commit.
HISTORY_REWRITE_REASON="${HISTORY_REWRITE_REASON:-}"

cd "${APP_DIR}"

git fetch origin main
git checkout main
if ! git pull --ff-only origin main; then
  echo "origin/main is not fast-forwardable (rewritten?) — resetting onto it."
  git reset --hard origin/main
fi
# Start from the COMMITTED outputs. A failed or manual run may have left
# outputs/ edited or holding stray files; the incremental run would read the
# edited summary as its input, and `git add outputs/` below would publish both.
git checkout HEAD -- outputs/ 2>/dev/null || true
git clean -fdq -- outputs/
# Baseline = the COMMITTED summary, not the working tree (which a failed or
# manual run may have left modified). Both the settled-history guard and the
# "did anything change" check below compare against it.
before_summary="$(mktemp)"
git show HEAD:outputs/summary.csv > "${before_summary}" 2>/dev/null || : > "${before_summary}"

pipeline_extra=()
if [[ -s "${before_summary}" ]]; then
  pipeline_extra+=(--baseline "${before_summary}")
fi
if [[ -n "${HISTORY_REWRITE_REASON}" ]]; then
  pipeline_extra+=(--allow-history-rewrite "${HISTORY_REWRITE_REASON}")
fi

"${PYTHON}" -m src.main ${PIPELINE_ARGS} ${pipeline_extra[@]+"${pipeline_extra[@]}"}

if [[ "${RUN_TESTS}" == "1" ]]; then
  "${PYTHON}" tests/validate_outputs.py
fi

if [[ "${RUN_RAW_CACHE_PRUNE}" == "1" ]]; then
  "${APP_DIR}/deploy/prune-raw-cache.sh"
fi

git add outputs/

if [[ -s "${before_summary}" ]] && cmp -s "${before_summary}" outputs/summary.csv; then
  git restore --staged --worktree -- outputs/
  rm -f "${before_summary}"
  echo "No canonical summary.csv changes; skipping workbook-only publish noise."
  exit 0
fi
rm -f "${before_summary}"

if git diff --cached --quiet; then
  echo "No publishable output changes."
  exit 0
fi

git config user.name "${GIT_AUTHOR_NAME:-aemo-nas-bot}"
git config user.email "${GIT_AUTHOR_EMAIL:-aemo-nas-bot@users.noreply.github.com}"
# Label with the latest DATA month in the summary, not the run month.
data_month="$(awk -F, 'NR == 1 { for (i = 1; i <= NF; i++) if ($i == "YEAR_MONTH") c = i; next }
  c && $c > m { m = $c } END { print m }' outputs/summary.csv)"
commit_args=(-m "${COMMIT_MESSAGE_PREFIX} ${data_month:-$(date -u +%Y-%m)}")
if [[ -n "${HISTORY_REWRITE_REASON}" ]]; then
  commit_args+=(-m "History rewrite: ${HISTORY_REWRITE_REASON}")
fi
git commit "${commit_args[@]}"

if [[ "${PUSH_CHANGES}" == "1" ]]; then
  git push origin main
else
  echo "PUSH_CHANGES=0; commit created but not pushed."
fi
