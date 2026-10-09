# Repo contract — AEMO Negative Prices (`cutout-z/aemo-negative-prices`)

Read this before touching anything. It says how work in this repo is allowed to happen, for design
passes and logic/integrity passes alike, whichever agent (Hermes, Claude Code, Codex) is doing it. The
family conventions and shared AEMO facts below are generated from the `agent-contracts` repo; where
this file's repo-specific rules are stricter, they win.

<!-- BEGIN agent-contracts:family -->
<!-- source: family/AGENTS.family.md sha256:116b1391e2bb — edit in cutout-z/agent-contracts, not here -->
## Family conventions (every repo, every agent)

*Generated from `agent-contracts/family/AGENTS.family.md`. Edit it there, never here: a drift check
reports any local edit.* These apply to every agent (Hermes, Claude Code, Codex or any other),
whatever app drives it. Where this repo's own rules (above or below this block) are stricter, they
win. Machine-specific conventions (which checkout is which, the lane runtime, where memory lives)
are in the owner's private contract, which reaches agents through their user-level instructions
where a harness supports it.

### Branches, concurrency, cleanup

- Work in a working clone, on a branch, never in a live or serving checkout: a live checkout is what
  serves or publishes, so an edit there goes out unreviewed. Merge to `main` only if this repo's
  contract says the agent may; otherwise push the branch and hand back for review.
- Other agents may be working in this repo right now. Fetch before you act. If a branch moved
  unexpectedly, or files you didn't touch changed, stop and report rather than reconcile.
- Use a worktree for parallel work, not a second clone. The exception is a live checkout: use a
  separate clone, because adding a worktree writes into the live checkout's `.git`. At session end,
  remove the worktrees you created and leave each checkout on the branch it was on when you arrived:
  a leftover worktree pins its branch, and a checkout left on your branch changes what the next
  agent, or a server running from it, sees.
- Push every branch you want kept. An unpushed branch is one disk failure from gone.

### Instructions and automation

- **`AGENTS.md` is the only instruction file.** `CLAUDE.md`, or any other harness-specific file, holds
  just a comment line and `@AGENTS.md`. Other harnesses never read those files, so a rule or fact put
  there reaches only one agent.
- **Nothing you depend on lives only in one harness or app.** Hooks, slash commands, plugins, app
  quick actions and app-scheduled tasks may speed things up. The only copy of any automation or rule
  goes in this repo (scripts, `AGENTS.md`) or the owner's scheduler, because the harness or app may be
  swapped.
- **Name the tier, not the model.** Briefs, skills and procedures say a tier and an effort (tier 0
  mechanical, 1 routine, 2 standard, 3 hard or review, 4 vision); `agent-contracts/tiers.yaml` maps
  each tier to a model per harness. Models change often, so a name in a skill goes stale.
- **A fact other agents need goes where they load it**: this repo's `AGENTS.md` Facts, with source
  and date. If it applies across repos, propose it for the shared facts block in your handback. Your
  own memory or skills are invisible to the other agents.

### What needs the owner's yes

An explicit instruction from the owner in the current session covers that action only, not similar
later ones: the yes was for what the owner saw, not for what follows. A repo contract may record a
standing permission from the owner (e.g. "the agent merges to `main` once `check.sh` is green"). It
counts as the owner's yes only for the actions and the agents it names, only in the repo whose
contract records it, and only as that text stands on `origin/main` when you start. It never covers
adding, widening or rewording a standing permission, or any change to `AGENTS.md` or this block:
those always need the owner's yes in the current session. Without either, declare these and wait
for a yes:

- **Publishing**: anything that changes what other people can see (`main` on a published repo,
  Pages, public data files).
- **Data and ETL**: data files, pipeline code, data contracts (columns, keys, paths, schemas).
  Lanes, dashboards and other repos read them, and a change breaks them silently.
- **The instruments**: `check.sh`, guard tests, audit and verify scripts. They are how anyone,
  including you, knows a change works. Never weaken one to make something pass. If one is wrong,
  say so and leave it.
- **Infra**: ports, scheduled jobs, servers, publish pipelines. Other jobs, and the owner, rely on
  them running as they are.
- **Another agent's state**: another agent's memory, config or notes. With the owner's yes any agent
  may change them; no agent is the only writer. The owning agent can't see your edit, so commit it
  where it's visible, and edit the source rather than a generated copy.

Never read, quote or commit secrets (`.env`, auth files, keys, tokens): repos, transcripts and
handback notes get copied and published.

### Verification standard

- A change is done when you have seen the evidence yourself: tests run (exact counts, failures
  named, pre-existing failures shown to exist on `main`), and for UI, a real browser render, or a
  plain statement that it wasn't rendered and why. A reviewer can check evidence, not belief.
- For a fix, show its test fails with the fix reverted and passes with it applied; otherwise nothing
  shows the test exercises the fix.
- Don't relay another agent's or subagent's numbers. Re-run or read the evidence yourself: a relayed
  number can't be traced, and you are the one signing the handback.

### Attribution and handback

- **Every commit names its agent** in a trailer, so audits and the owner's digest can tell which agent
  made each change, whatever app drove it: `Co-Authored-By: <Agent> <model> <email>`, e.g.
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. `<Agent>` is one word (`Claude`,
  `Codex`, `Hermes`, …); `<model>` is the model name without a provider prefix (e.g. `Opus 5.5`,
  `deepseek-v4.1-flash`). The email goes in angle brackets: Claude `noreply@anthropic.com`, Hermes
  `noreply@nousresearch.com` (as in existing commits), any other agent `<agent>@agents.invalid`.
  Audits match the key case-insensitively and the first word of the value.
- **Commit with the repo's configured identity.** Never set or override `user.name` or `user.email`,
  and never pass `--author`: on a public repo, author fields are published.
- **End every piece of work with a handback note.** It is the durable record; app session lists and
  an agent's memory are not, and both may be swapped. Use the repo's own path and branch convention
  if it has one; it wins, including whether notes merge. Otherwise use
  `handbacks/<YYYY-MM-DD>-<topic>.md`. On a repo whose `main` is published (a public repo, or one that
  deploys or builds a site from `main`), commit the note on its own branch, `handback/<your-branch>`:
  push it, and never merge or delete it, so the record survives the work branch's merge without
  landing on `main`. On a public repo every pushed branch is public too, so keep notes there free of
  private details. The frontmatter goes above the first line of any repo template:

  ```yaml
  ---
  project: <project name as on the owner's dashboard>
  agent: <the trailer's Agent, lowercase: claude, codex, hermes, …>
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
<!-- source: facts/AEMO-FACTS.md sha256:c32c596c4a5d — edit in cutout-z/agent-contracts, not here -->
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
| TLF orientation | `TRANSMISSIONLOSSFACTOR` = **Import** MLF; `SECONDARY_TLF` = **Export** MLF for BIDIRECTIONAL (battery) units. A battery's export MLF comes from `SECONDARY_TLF`, never `TRANSMISSIONLOSSFACTOR`. Confirmed 51/51 differing batteries against AEMO's 2026-27 workbook. The MLF Tracker used the import factor for FY24-25/FY25-26 battery export values until fix `dbaf6f7` (2026-10-05); downstream battery revenue was restated (~−$13.1M across 26 batteries' months) after the fix. | 2026-10-05 | AEMO 2026-27 MLF workbook; `cutout-z/aemo-generator-credit-dashboard`: `audits/Logic Pass Rollout 2026-10-05.md` |
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
| Shared sidebar | `index.html` loads `https://cutout-z.github.io/aemo-dashboards/nav.js` (repo `cutout-z/aemo-dashboards`, added 2026-10-10): the sidebar and phone top bar every AEMO dashboard shares. It changes there, not here, and a change there reaches this page with no PR here. It pads `body` by 232px at 1024px and wider, so check layout changes at that width. Keep the tag plain (not `defer`) at the end of `<head>` |
| Styles | `assets/css/tailwind.src.css` (tokens, the only literal colours) → Tailwind v3.4.17 standalone → `assets/css/app.css` (committed). Build script `scripts/build-css.sh` exists only on `design/2026-10` |
| Pipeline | Python: NEMOSIS ≥3.8.1, pandas, openpyxl, requests (`requirements.txt`); `src/` = config, download, analyse, excel_output, main |
| Data lane | NAS (QNAP `ai-wif-runner`), `nas-job aemo-negative-prices` → `deploy/run-update.sh`, `PIPELINE_ARGS=--months-back 2`; commits as `aemo-nas-bot` and pushes `main` only when `summary.csv` changes (`deploy/README.md`, `deploy/env.example`) |
| Lane behaviour | `git reset --hard origin/main` if `main` is not fast-forwardable; restores and cleans `outputs/` before each run (`deploy/run-update.sh`) |
| Fallback | `.github/workflows/monthly-update.yml`, manual dispatch only; commits `outputs/` as `github-actions[bot]` |
| Lane cadence | README says daily (`README.md:38`, `:125`); `deploy/README.md` states no cadence. The time, 08:42 AWST (`42 8 * * *`), comes from the owner's host crontab, checked 2026-10-08 (unverified: not in this repo). The lane commits only when `summary.csv` changes, so history shows data changes, not runs: bot data commits on the 1st at 00:42 UTC from `25550ad` (2026-07-01) to `2e93b1d` (2026-10-01), plus off-cycle ones on 2026-05-11 (`78bf7ab`) and 2026-05-13 (`470a8be`). When daily runs began is unverified |
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
cd <worktree> && python3 -m pytest -q -p no:cacheprovider   # synthetic, no network
cd <worktree> && python3 tests/validate_outputs.py           # the data gate, exit 0
```

**Baseline (2026-10-08, `1abdd27`, fresh worktree): `126 passed`, 0 failed; `validate_outputs.py`
exit 0 ("All validations passed", 440 rows).** No test needs gitignored data. `-p no:cacheprovider`
keeps `.pytest_cache/` (not gitignored) out of the tree.

Local preview, port **9360** (the port the 2026-10 design pass used; `design/2026-10:AGENTS.md`).
Serve the worktree you are in:

```bash
cd <worktree> && python3 -m http.server 9360 --bind 127.0.0.1
# http://127.0.0.1:9360/index.html   (?theme=light / ?theme=dark forces a theme)
```

Browser checks go through Playwright (cloud browsers cannot reach `127.0.0.1`). The render and
behaviour gates `scripts/verify-design.py` / `scripts/verify-interactions.py` are **not on `main`**;
take them from `design/2026-10` into your branch, never into `main`. Never run the pipeline or the
lane from a pass: they download from nemweb and push.

Ports (`design/2026-10:scripts/verify-design.py:4,27`, `verify-interactions.py:4,21`): the gates
need **9382**, not 9360, and their header serves a hard-coded checkout path, not your worktree.
9382 collides with the Historical Prices gates (its tag `design-2026-10-evidence`, `scripts/verify-design.py:25`): never run both at
once. Moving the gate port is an instruments change and needs the owner's yes. Reserved
elsewhere, never use (unverified: not in this repo): 8050, 9250–9259, 9300, 9330, 9350, 9351; sibling repos' 9370, 9380, 9381.

## Pitfalls that have bitten

- **Partial by-path merge.** An anchored path filter dropped `assets/css/app.css`, so `main` served
  the new markup on the old stylesheet (`21aac42`, commit message). Carry
  `index.html` and `app.css` together, and remember a CSS-only push does not trigger a deploy.
- **Tailwind purges unseen classes.** After a class change rebuild `app.css` and commit it.
  `HEAT_STOPS` in the script and the legend `<ol>` must move together (`index.html:138-139`).
- **Downloads always point at `main`.** A branch preview links `raw/main` workbooks, not the branch's.
- **The data gate is date-dependent.** Every month that ended >35 days ago must be present, so
  `validate_outputs.py` on unchanged data can start failing (`2a3b70f`). That is staleness, not you.
- **Leftovers in `outputs/` leaked into lane runs** (an edited `summary.csv` read as input; fixed
  `ac9a14a`), and **commits were labelled with the run month** (`2e93b1d` "2026-10" added 2026-08; fixed `c5ca812`).
- **Copy drift.** The page footer said "Updates monthly on the 16th" (`f8277f5`, still at `ddb96a1`),
  contradicting README and `deploy/`; `index.html:412` now says "checked daily". Schedule and lag copy
  must match README "Update Schedule" / "Publication lag".

## Working alongside other agents

- The NAS lane pushes to `main` on its own and hard-resets its checkout; a hand commit there is lost.
- Hermes owns the lane. Do not edit the lane registry or NAS runner tooling from here (neither is
  in this repo).
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
