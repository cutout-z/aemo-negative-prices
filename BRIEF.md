# BRIEF — AEMO Negative Prices redesign, pass 1

**Read `CLAUDE.md` → `AGENTS.md` (the contract) before writing code.** The first line of your session
should be `git status` and `git rev-parse --short HEAD` — if git fails here, stop and say so rather
than working around it.

*Handover prompt (if the session is started fresh, this is all that needs saying):*
> Project folder `~/Design/AEMO Negative Prices`. Read `CLAUDE.md`, then `AGENTS.md`, then execute
> `BRIEF.md` — and stop after step 1 to report.

## The goal, stated as an outcome

The dashboard is functionally complete and visually poor: a bare table from a 2019-era template. Make
it **look like it was designed by someone who cares** and like it belongs to the same product family as
the other AEMO dashboards — modern, restrained, scannable, honest about its own scale.

**Definition of done = the real page, rendering real data, looking right when screenshotted.**
Adopting a token file, adding a stylesheet, "styling centralised", or a theme module is NOT done. A
sibling pass delivered exactly that and nothing visible changed on 37 of 39 pages.

## Hard constraints

- **It stays static.** GitHub Pages serves the repo root — one page, no server, no build step at
  deploy, no self-hosting. Everything must work as plain files a browser loads.
- **Interactivity is client-side only.** Region switching, the CSV load, the six downloads and the
  footer's as-of line must all still work. Nothing you add may need a backend.
- **One page.** `index.html`. Do not split it or introduce a framework.
- **Presentation only** — `AGENTS.md` lists the forbidden trees.
- **No new dependencies beyond the compiled stylesheet.** PapaParse stays the only script (one CDN
  script tag is already there). No chart library is needed: the heat is HTML cells.

## The design language — adopt it, do not invent a second one

| Where | What |
|---|---|
| `assets/css/tailwind.src.css` | **The tokens.** Surfaces, text, status, radii, shadows, both themes, and the sequential ramp `--seq-0…7` / `.seq-0…7`. The only file with literal colours. |
| `design/design-tokens.md` | The seven rules (colour = entity, contrast floor, heat needs a stated scale, …) |
| `design/tokens.html` | **The proof page** — palette, type scale, controls, a dense table, the ramp and the states, rendered live. Open it first (`http://127.0.0.1:9360/design/tokens.html`). |
| `~/Design/aemo-credit-design` | The sibling AEMO pass (a 14-chart dashboard, same tokens). Match its language; do not copy its markup. |

The rules that matter most here: **the ramp is one hue with eight steps and the page states the
stops**; **a heat cell prints its number** (colour is never the only signal); **`--faint` is the floor
for 12px text**; **`.card` is the unit of composition, and its foot carries provenance**.

## Baseline — measured on this clone, 2026-09-30, before the pass

`python3 scripts/verify-design.py`: **12 of 26 checks fail**; `scripts/verify-interactions.py`: 25
checks, exit 0. Page facts: **3,026 px tall at 1440×900** (3.4 screens), 87 rows × 9 heat columns,
5 region tabs, 6 download buttons, footer reading "Data through Jul 2026". Phone 390px: 3,117 px tall,
no page-level sideways scroll, the table scrolls inside its wrapper (748 px of scroll width).

The failures, and the visible problems behind them:

1. **No shell and no orientation.** `h1` + one-line subtitle + a table. No card, no KPI row, no units
   line, nothing that answers "what does this page say?" before you read 87 rows — the region with the
   worst daylight negative pricing today, the latest month, the trend to the same month a year ago.
2. **The heat is a three-stop traffic-light gradient computed in JS per cell** (`heatColor()`:
   green `#63BE7B` → yellow `#FFEB84` → red `#F8696B`, plus a `textColor()` contrast guess). Red/green
   is the family's *status* language, not an intensity language; it collides with `.pill-good/warn/bad`.
3. **The scale is nowhere on screen.** No legend, no stops, no direction — 783 coloured cells that a
   reader has to reverse-engineer.
4. **2019 tab chrome.** `.tab` buttons with rounded top corners and a filled `#4472C4` active state;
   the family control is `.seg` / `.seg-item`.
5. **Accent blue `#4472C4` does the work of four roles** — header fill across 10 columns, buttons,
   links, hover. The family accent is one warm colour used sparingly.
6. **Numerics are centred with no tabular figures**, and the month column (text) is styled like the
   numbers. The family right-aligns numbers in tabular figures.
7. **The header is the loudest element** — a solid accent block across all 10 columns, repeated on
   scroll (sticky). There is no unit line, no grouping cue, and the nine thresholds differ only by
   their label.
8. **The download row is six outlined buttons** with an inline `Download Excel:&nbsp;` label; "All
   States" is distinguished only by a different border colour.
9. **No empty/error state**: blocking `outputs/summary.csv` leaves the sentence "Failed to load data.
   Check that outputs/summary.csv exists." in the middle of an otherwise empty page — the family
   pattern is a `.state` panel that states the absence and what would fix it.
10. **No light theme, no toggle, no `?theme=` forcing.**
11. **Phone:** the month column scrolls out of view with the numbers (no sticky first column); the
    page's only phone concession is the wrapper's `overflow-x`.
12. **Provenance is one muted line** (`0.78rem`, `#888`) and it disagrees with the repo's own README:
    the footer says "Updates monthly on the 16th", while `README.md` describes a *daily* NAS probe that
    publishes only when the monthly data changes, and `deploy/run-update.sh` re-processes a 2-month
    overlap window daily. One of the two is stale — state what is actually true on the page, and don't
    change the README.

## Order of work

One commit per step. **Stop after step 1 and report before scaling to the rest.**

1. **Wire the token layer and the shell.** Add the `assets/css/app.css` link *before* the existing
   inline `<style>` so nothing shifts by accident, then convert the page chrome: frame, background,
   typography, the title/subtitle block, the tab row (`.seg` / `.seg-item`), the download row
   (`.btn`), the footer (`.card-foot`). Once the old inline rules for those elements are gone, delete
   the inline reset block — `preflight` is already ON in `tailwind.config.js` and must end up as the
   page's *only* reset (two competing resets is how spacing moves on its own) — then rebuild with
   `./scripts/build-css.sh` and commit `assets/css/app.css`. Report here.
2. **Header + KPI row.** What the page answers, at a glance, for the selected region — every value
   computed from `outputs/summary.csv` and each labelled with its month: latest month's share of
   daylight intervals below $0; the same month a year earlier (with the change); the deepest threshold
   that has ever been crossed, and when; the region's rank of the five. `.kpi-value` / `.kpi-label`,
   `.card` wrapped, no status colour on a number that is not a status.
3. **The heat table.** `.card` with head (title, the region seg, the unit) → body (table: `.th`/`.td`,
   sticky header, tabular figures, months in the first column) → foot (`Source:`, `as of <month>`,
   publication lag). Heat cells become `td.seq-0…7` — the JS picks a step from the value, never a
   colour — with a **legend that names the numeric stops and the direction**. Keep the month column
   pinned on phone widths.
4. **Filters and downloads.** The download row as `.btn`s (the region's workbook + All States, plus
   the CSV if it is genuinely useful) and `.badge`s for the counts the page already knows (rows, span
   of months).
5. **States.** Loading (skeleton), missing file (`.state` naming `outputs/summary.csv` and what would
   fix it), and a region/window with no rows. Absence is stated, never faked with a zero.
6. **Themes.** Dark default; a toggle that is remembered per viewer; `?theme=light` / `?theme=dark`
   force one. The ramp and every surface must flip from the tokens alone.
7. **Phone (390px).** Single column, no page-level sideways scroll, the numeric table scrolls inside
   its card with the month column pinned, tap targets ≥ 32px.
8. **The interactions you must not lose:** region switching, the CSV fetch, the six downloads, the
   sticky header, the footer's as-of line. `scripts/verify-interactions.py` is the gate.

## Evidence (part of done, not optional)

- `scripts/verify-design.py` exits **0** (28 checks). `--screens` writes `design/screens/after-*.png`.
- `scripts/verify-interactions.py` still exits **0**, same check count.
- `/opt/anaconda3/bin/python3 tests/validate_outputs.py` exits 0 ("All validations passed").
- Screenshots for every surface you changed, desktop **and** phone, at the same positions as
  `before-*.png` (top, full, phone, no-data). Evidence lives in `design/screens/` — never next to the
  page, never a new root-level folder.
- `./scripts/build-css.sh` run after the last class change, `assets/css/app.css` committed.
- `git diff --stat main` shows no `outputs/**`, `src/**`, `deploy/**`, `tests/**`, `.github/**`.

## Report back

Surfaces changed of the ones that exist; what is half-done; any decision the brief did not cover (in
particular: how you mapped the value range onto eight ramp steps and what the legend says). Do not
claim a surface is done because the HTML changed — it is done when a browser renders it with real data
and the gate says so.
