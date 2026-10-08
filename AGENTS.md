# Repo contract — AEMO Negative Prices (`cutout-z/aemo-negative-prices`)

Read this before touching anything. It says how work in this repo is allowed to happen, for design
passes and logic/integrity passes alike, whichever agent (Hermes, Claude Code, Codex) is doing it. The
family conventions and shared AEMO facts below are generated from the `agent-contracts` repo; where
this file's repo-specific rules are stricter, they win.

<!-- BEGIN agent-contracts:family -->
<!-- source: family/AGENTS.family.md sha256:f43f0fc253a7 — edit in cutout-z/agent-contracts, not here -->
## Family conventions (every repo, every agent)

*Generated from `agent-contracts/family/AGENTS.family.md`. Edit it there, never here: a drift check
reports any local edit.* These apply to every agent (Hermes, Claude Code, Codex or any other),
whatever app drives it. Where this repo's own rules (above or below this block) are stricter, they
win. Machine-specific conventions (which checkout is which, the lane runtime, where memory lives)
are in the owner's private contract, which each harness loads separately.

### Branches, concurrency, cleanup

- Work in a working clone, on a branch, never in a live or serving checkout. Merge to `main` only if
  this repo's contract says the agent may; otherwise push the branch and hand back for review.
- Other agents may be working in this repo right now. Fetch before you act. If a branch moved
  unexpectedly, or files you didn't touch changed, stop and report rather than reconcile.
- Use a worktree for parallel work, not a second clone. At session end, remove the worktrees you
  created and leave each checkout on the branch it was on when you arrived.
- Push every branch you want kept. An unpushed branch is one disk failure from gone.

### What needs the owner's yes

An explicit instruction from the owner in the current session covers that action only, not similar
later ones. Without one, declare these and wait for a yes:

- **Publishing**: anything that changes what other people can see (`main` on a published repo,
  Pages, public data files).
- **Data and ETL**: data files, pipeline code, data contracts (columns, keys, paths, schemas).
- **The instruments**: `check.sh`, guard tests, audit and verify scripts. Never weaken one to make
  something pass. If one is wrong, say so and leave it.
- **Infra**: ports, scheduled jobs, servers, publish pipelines.
- **Another agent's state**: another agent's memory, config or notes.

Never read, quote or commit secrets: `.env`, auth files, keys, tokens.

### Verification standard

- A change is done when you have seen the evidence yourself: tests run (exact counts, failures
  named, pre-existing failures shown to exist on `main`), and for UI, a real browser render.
- For a fix, show its test fails with the fix reverted and passes with it applied.
- Don't relay another agent's or subagent's numbers. Re-run or read the evidence yourself.

### Attribution and handback

- **Every commit names its agent** in a trailer: `Co-Authored-By: <Agent> <model> <email>`, e.g.
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, `Co-Authored-By: Codex …`,
  `Co-Authored-By: Hermes …`. Audits match on the `Co-Authored-By: <Agent>` prefix.
- **End every piece of work with a handback note on the branch**, using the repo's own path
  convention, or `docs/handback-<YYYY-MM-DD>-<topic>.md` if it has none. On a repo whose `main` is
  published, keep notes and evidence on the branch; they don't merge. Start the note with:

  ```yaml
  ---
  project: <project name as on the owner's board>
  agent: claude | codex | hermes
  branch: <branch>
  merged: false
  status: <one line>
  outstanding:
    - "to-do [mac-local] <item>"   # [mac-local] = only actionable on the owner's Mac
  ---
  ```

  Then cover what changed, the evidence, what's left, and any decision the brief didn't cover.
<!-- END agent-contracts:family -->

<!-- BEGIN agent-contracts:aemo-facts -->
<!-- source: facts/AEMO-FACTS.md sha256:c6c3cdf689bd — edit in cutout-z/agent-contracts, not here -->
## AEMO shared facts — every agent, every repo

One canonical home for cross-repo AEMO domain facts, so a fact established in one repo is never
invisible to an agent working in another (the battery-MLF lesson, 2026-10-05: the TLF orientation
was established inside one repo's rollout doc while other agents recomputed with the wrong factor).

**Who reads this:** any agent (Hermes, Claude Code, Codex) working in an AEMO repo. It is stamped
into each AEMO repo's `AGENTS.md` between `agent-contracts:aemo-facts` markers, and the `aemo-audit`
and `aemo-logic-pass` skills point here instead of duplicating facts. A fact here overrides anything
remembered or re-derived.

**Maintenance:** append with date + source; supersede in place (`~~SUPERSEDED~~ <date> <reason>`).
Location: `agent-contracts/facts/AEMO-FACTS.md` (git, `cutout-z/agent-contracts`). Edit here only; `scripts/stamp.py` copies it into each AEMO repo's AGENTS.md.

| Fact | Detail | Verified | Source |
|---|---|---|---|
| TLF orientation | `TRANSMISSIONLOSSFACTOR` = **Import** MLF; `SECONDARY_TLF` = **Export** MLF for BIDIRECTIONAL (battery) units. A battery's export MLF comes from `SECONDARY_TLF`, never `TRANSMISSIONLOSSFACTOR`. Confirmed 51/51 differing batteries against AEMO's 2026-27 workbook. The MLF Tracker used the import factor for FY24-25/FY25-26 battery export values until fix `dbaf6f7` (2026-10-05); downstream battery revenue was restated (~−$13.1M across 26 batteries' months) after the fix. | 2026-10-05 | AEMO 2026-27 MLF workbook; `aemo-credit-design/audits/Logic Pass Rollout 2026-10-05.md` |
| FCAS regime | FCAS causer-pays contribution factors are DEAD — replaced by the Frequency Performance Payment (FPP) on 8 June 2025 (5-minute contribution factors on NEMWEB). Never recommend or resurrect causer-pays factor tracking; FPP cost-allocation factors per DUID are the future extension. | 2026-09-01 | AEMO/NEMWEB; `aemo-audit` skill; credit repo `docs/FUTURE_DATA_SOURCES.md` |
<!-- END agent-contracts:aemo-facts -->

## Hard rules

1. **`main` is the public site.** `.github/workflows/deploy-pages.yml` uploads the whole repo root
   (`path: .`) to GitHub Pages. Anything committed to `main` is published, this file included. Gates,
   screenshots, briefs and pass notes stay on their branch (`da03ece`: "scripts/, design/ and
   screenshots stay on the branch, because Pages serves the repo root"). Never commit a secret.
2. **Never hand-edit `outputs/**`.** The NAS lane owns it (`deploy/run-update.sh` stages
   `outputs/` only). It changes only by running `src.main`; never edit the CSV or a workbook by hand.
   `data/**` is the gitignored NEMOSIS cache; `tools/` is the gitignored Tailwind binary. Neither is
   ever committed.
3. **Settled history needs the owner's yes and a reason.** Months outside `--months-back` are guarded
   against the committed `HEAD:outputs/summary.csv`; changing one needs
   `--allow-history-rewrite "<reason>"`, recorded in the commit (`src/main.py`, README "Full Refresh").
   Precedent: `66aee7c` (logic-pass rewrite, 363 of 440 rows changed, with before/after examples).
4. **The data contracts below do not change without the owner's yes.** The page, README links, workbook
   readers and the validator all depend on them.
5. **Keep the suite and the data gate green.** `pytest` and `tests/validate_outputs.py` (commands
   below). If a change breaks a test, the change or the test is wrong, deliberately: say which.

## Facts

| | |
|---|---|
| What it is | Share of daylight 5-min dispatch intervals with RRP below 9 thresholds ($0 … −$80), 5 NEM regions, May 2019 → latest published month (README) |
| Served by | GitHub Pages via an Actions workflow from `main`, repo root: https://cutout-z.github.io/aemo-negative-prices/ (README; `deploy-pages.yml`) |
| Deploy trigger | push to `main` touching `outputs/**`, `index.html`, `README.md` or the workflow, or manual dispatch (`deploy-pages.yml`). **`assets/**` is not in the list** |
| Page | `index.html` (431 lines, root), vanilla JS + PapaParse 5.4.1 (CDN); reads `outputs/summary.csv` relative to the page |
| Styles | `assets/css/tailwind.src.css` (tokens, the only literal colours) → Tailwind v3.4.17 standalone → `assets/css/app.css` (committed). Build script `scripts/build-css.sh` exists only on `design/2026-10` |
| Pipeline | Python: NEMOSIS ≥3.8.1, pandas, openpyxl, requests (`requirements.txt`); `src/` = config, download, analyse, excel_output, main |
| Data lane | NAS (QNAP `ai-wif-runner`), `nas-job aemo-negative-prices` → `deploy/run-update.sh`, `PIPELINE_ARGS=--months-back 2`; commits as `aemo-nas-bot` and pushes `main` only when `summary.csv` changes (`deploy/README.md`, `deploy/env.example`) |
| Lane behaviour | `git reset --hard origin/main` if `main` is not fast-forwardable; restores and cleans `outputs/` before each run (`deploy/run-update.sh`) |
| Fallback | `.github/workflows/monthly-update.yml`, manual dispatch only; commits `outputs/` as `github-actions[bot]` |
| Lane cadence | **conflict, unverified**: README and `deploy/README.md` say daily; private ops notes list cron `42 8 1 * *` (monthly). Bot commits since 2026-07 land on the 1st |
| Latest data | 440 rows = 5 regions × 88 months, 2019-05 → 2026-08 (`outputs/summary.csv`, 2026-10-08) |

## Data contracts (the owner's yes to change)

- `outputs/summary.csv`: 21 columns, `REGIONID, YEAR_MONTH, total_daylight_intervals`, then
  `count_below_{0,neg10,…,neg80}` / `pct_below_…` pairs. `REGIONID` ∈ NSW1 QLD1 VIC1 SA1 TAS1,
  `YEAR_MONTH` = `YYYY-MM`, pct = `round(count/total×100, 2)` on a 0–100 scale (`tests/validate_outputs.py`).
- Workbooks: `outputs/{NSW,QLD,VIC,SA,TAS,All_States}_negative_prices.xlsx`, sheets Percentages /
  Heatmap / Audit (README). `index.html` and README link them by absolute `raw/main` URL.
- Method (`src/config.py`): interval **start** in [08:00, 16:00) AEST, 96/day; RRP rounded to whole
  cents half away from zero, then strictly below the threshold; thresholds `0, −10 … −80`; only
  `INTERVENTION = 0` rows kept (README).
- `MAX_PUBLICATION_LAG_DAYS = 35` in `tests/validate_outputs.py` and `index.html` must match
  (`tests/test_page.py`).
- Page hooks the design gates read (`#tabs`, `#thead`, `#tbody`, `seq-0…7` heat cells,
  `[data-heat-legend]`, six `a[download]` `.xlsx`, `#footer`): listed in `design/2026-10:AGENTS.md`.

## Verify

```bash
cd <worktree> && /opt/anaconda3/bin/python3 -m pytest -q -p no:cacheprovider   # synthetic, no network
cd <worktree> && /opt/anaconda3/bin/python3 tests/validate_outputs.py           # the data gate, exit 0
```

**Baseline (2026-10-08, `1abdd27`, fresh worktree): `126 passed`, 0 failed; `validate_outputs.py`
exit 0 ("All validations passed", 440 rows).** No test needs gitignored data. `-p no:cacheprovider`
keeps `.pytest_cache/` (not gitignored) out of the tree.

Local preview, port **9360** (the port the 2026-10 design pass used; `design/2026-10:AGENTS.md`):

```bash
cd <worktree> && /opt/anaconda3/bin/python3 -m http.server 9360 --bind 127.0.0.1
# http://127.0.0.1:9360/index.html   (?theme=light / ?theme=dark forces a theme)
```

Browser checks go through Playwright (cloud browsers cannot reach `127.0.0.1`). The render and
behaviour gates `scripts/verify-design.py` / `scripts/verify-interactions.py` are **not on `main`**;
take them from `design/2026-10` into your branch, never into `main`. Never run the pipeline, the lane
or `brain-ops-nas workflow aemo-negative-prices` from a pass: they download from nemweb and push.

## Pitfalls that have bitten

- **Partial by-path merge.** An anchored path filter dropped `assets/css/app.css`, so `main` served
  the new markup on the old stylesheet (`21aac42`; private design-pass notes). Carry
  `index.html` and `app.css` together, and remember a CSS-only push does not trigger a deploy.
- **Tailwind purges unseen classes.** After a class change rebuild `app.css` and commit it.
  `HEAT_STOPS` in the script and the legend `<ol>` must move together (design pass note).
- **Downloads always point at `main`.** A branch preview links `raw/main` workbooks, not the branch's.
- **The data gate is date-dependent.** Every month that ended >35 days ago must be present, so
  `validate_outputs.py` on unchanged data can start failing (`2a3b70f`). That is staleness, not you.
- **Leftovers in `outputs/` leaked into lane runs** (an edited `summary.csv` read as input; fixed
  `ac9a14a`), and **commits were labelled with the run month** (`2e93b1d` "2026-10" added 2026-08; fixed `c5ca812`).
- **Copy drift.** The page said "Updates monthly on the 16th", contradicting README and `deploy/`
  (design pass note). Schedule and lag copy must match README "Update Schedule" / "Publication lag".

## Working alongside other agents

- The NAS lane pushes to `main` on its own and hard-resets its checkout; a hand commit there is lost.
- Hermes owns the lane (its private project note's "latest: Feb 2026" and "monthly" lines are stale). Do not edit the lane registry
  (`tools/nas-runner/configs/brain-ops.nas.toml`, NAS runner tooling) from here.
- Design: `index.html`, `assets/css/**`. Logic: `src/**`, `tests/**`, `deploy/**`, `.github/**`.
  If a pass needs a data file that does not exist, stop and say so; never synthesise one.

## Handback checklist

- [ ] `pytest` and `tests/validate_outputs.py` run; exact counts stated, any failure named and
      classed (yours, staleness, or environmental).
- [ ] No hand edit under `outputs/**`; no `data/`, `tools/`, `.pytest_cache/` in the diff.
- [ ] Any settled-history change carries the owner's yes and the `--allow-history-rewrite` reason.
- [ ] Visual change: rendered on 9360 at desktop and phone, both themes, gates from `design/2026-10`
      green; `app.css` rebuilt and committed.
- [ ] Nothing meant to stay private (screenshots, briefs, pass notes, gates) headed for `main`.
- [ ] Report: what changed, how it was verified, what you left alone, what you had to decide.
