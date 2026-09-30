# Design pass 2026-09-30 — AEMO Negative Prices

Branch `design/2026-10`, one commit per BRIEF step. Base: `ddb96a1` (design prep).
Not merged, no PR. This note is how the next agent reconstructs intent without the transcript.

## Commits

| commit | step | what |
|---|---|---|
| `59dfce1` | 1 | token layer linked + built (`app.css` had been committed empty, 0 bytes); frame, header, `.card` shell, `.seg` region switch, `.btn` downloads, `.card-foot` footer; inline reset deleted (preflight is the only reset) |
| `0818bcb` | — | *Hermes, not this session:* `verify-design.py` strips CSS comments before reading tokens (the `--faint` comment "4.9:1 on --surface: …" was parsed as a `--surface` declaration, so the card-background check could never pass). Nothing on the page was changed for that check. |
| `11053e6` | 2 | KPI card for the selected region |
| `c5686a5` | 3 | heat table on `.th`/`.td`/`.seq-*`, legend, sticky header + pinned month column, provenance foot; inline `<style>` removed |
| `585740c` | 4 | downloads led by the selected region's workbook; count badges |
| `8cf7506` | 5 | loading skeletons, missing-file / empty-file / no-rows `.state` panels |
| `770d28d` | 6 | `data-theme` dark default, remembered Dark/Light toggle, `?theme=` forcing |
| `7889313` | 7 | phone: 32px targets, pinned-column edge; region switch beside the title on desktop |
| (this) | handback | after-screenshots, this note |

Step 8 (interactions) needed no code: `verify-interactions.py` stayed 25/25 after every step.

## Files changed

- `index.html` — the whole visible change. One inline `<script>` in `<head>` (theme before first
  paint) and the existing inline page script; no `<style>` block, no hex colour.
- `assets/css/app.css` — rebuilt by `./scripts/build-css.sh` after the last class change.
- `design/screens/after-*.png` — evidence (see below).
- `docs/design-pass-2026-09-30.md` — this note.

Untouched: `outputs/**`, `data/**`, `src/**`, `deploy/**`, `tests/**`, `.github/**`,
`requirements.txt`, `README.md`, `assets/css/tailwind.src.css` (token values), `tailwind.config.js`,
both gate scripts (apart from Hermes' `0818bcb`).

## Visual summary

- **Shell:** `--bg` frame, inset `--canvas` panel (≥640px), 1160px column, header with eyebrow /
  title / subtitle (copy unchanged). Page height at 1440×900: **3,026 → 1,504 px**; phone 390px:
  **3,117 → ~1,990 px**.
- **KPI card** ("SA at a glance"), four tiles, all computed in the page from `outputs/summary.csv`
  for the active region, each naming its month:
  1. share below $0 in the latest month, with `count_below_0` of `total_daylight_intervals`;
  2. the same month a year earlier, and the change in percentage points (words, no status colour;
     a missing year-earlier row prints `N/A`);
  3. the deepest threshold ever crossed (from `count_below_*`), last month crossed, months crossed;
  4. rank of the regions on the latest month's share below $0 (1 = most; ties `=n`).
- **Heat table card:** title, unit line, badges (months, span, thresholds), region `.seg`, legend,
  table, provenance foot.
  - Heat cells are `td.td-num.seq-N`; `heatStep()` picks the step, never a colour. The light
    variant comes from the tokens.
  - **Ramp mapping:** `0` → seq-0 · `(0,1)` → 1 · `[1,5)` → 2 · `[5,10)` → 3 · `[10,20)` → 4 ·
    `[20,35)` → 5 · `[35,50)` → 6 · `[50,100]` → 7. Uneven on purpose: 880 of 3,915 cells are exactly
    0 and the median is 1.6%, so equal 12.5-point bins would paint most of the table one step. All
    eight steps are used. `HEAT_STOPS` in the script and the legend `<ol>` in the markup must move
    together.
  - **Legend** (`[data-heat-legend]`): eight swatches labelled `0%`, `<1%`, `1–5%`, `5–10%`,
    `10–20%`, `20–35%`, `35–50%`, `50–100%`, then "→ more of the month's daylight below the price ·
    each range includes its lower bound".
  - The table scrolls inside the card (`max-h: min(72vh, 760px)`) so the sticky header actually
    sticks, and opens scrolled to the newest months. The month column is pinned at every width.
  - Foot: `Source: AEMO DISPATCHPRICE (RRP, intervention pricing excluded) via NEMOSIS · as of
    <latest month> · Checked daily; a month appears once AEMO publishes that month's archive`.
    This replaces "Updates monthly on the 16th", which contradicted README "Update Schedule" and
    `deploy/run-update.sh`.
- **Downloads card:** the active region's workbook is the one `.btn-primary`, then All States, then
  the other four as `.btn-ghost`. The subtitle states the contents (region workbook = three sheets,
  All States = a percentages sheet per region, per `src/excel_output.py`).
- **Page footer row:** "figures computed in your browser from outputs/summary.csv" (a plain link)
  and the Dark / Light toggle.
- **States:** skeletons while loading. The region switch, footer source line and downloads render
  before the CSV arrives. A failed fetch shows a `.state` in each card naming `outputs/summary.csv`
  and what fixes it; an empty file and a region with no rows each have their own `.state`.

## How it was verified (2026-09-30, local preview on 127.0.0.1:9360)

| gate | before the pass | at handback |
|---|---|---|
| `tests/validate_outputs.py` | exit 0 | **exit 0** — "All validations passed." |
| `scripts/verify-interactions.py` | 25 checks, exit 0 | **25 checks, exit 0** — "all interactions intact" |
| `scripts/verify-design.py` | 12 of 26 fail | **27 of 27 pass, exit 0** |

The design gate reports 27 checks; BRIEF.md says 28. The count went 26 → 27 when the page gained
`.card` panels (the card-background check only runs when a card exists). No check was removed.

Also checked in a browser (Playwright, scratch scripts, not committed):
- KPI values for all five regions against an independent read of the CSV.
- The CSV aborted, the CSV with TAS1 rows removed (rank becomes "2 of 4"), and a held request
  (skeletons). No JS errors in any of them.
- At 390×844: no page overflow; no visible button or link under 32px; month column at the wrapper's
  left edge when scrolled fully right.
- Theme: toggle persists across reload; `?theme=dark` overrides a saved "light" without changing it.

Screenshots in `design/screens/`: `after-top`, `after-full`, `after-phone`, `after-nodata`,
`after-vic-top` (from `verify-design.py --screens`), plus `after-light-top` and `after-light-phone`.
**`after-top.png` shows VIC, not the default SA:** the gate clicks VIC during its checks before it
takes screenshots, so `after-top` and `after-vic-top` are identical.

## Deliberately left alone

- README (the brief says not to change it), token values, Tailwind config.
- No CSV `a[download]`: both gates require exactly six `a[download]` links ending `.xlsx`. The CSV
  is a plain link in the page footer instead.
- No publication-lag figure in the foot: the repo doesn't record one, so the foot states the
  mechanism (checked daily; a month appears once AEMO publishes it) rather than a number.
- No group header row in `<thead>`: the interaction gate counts exactly 10 `#thead th`. The grouping
  cue ("below the column's threshold, $/MWh") is in the unit line.
- The sibling `~/Design/aemo-credit-design` was not read (blocked in this session). The language
  comes from this repo's tokens and `design/tokens.html` only.

## Where I may have bent the brief

1. **The table scrolls inside its card.** That is the only way a sticky header works under a
   horizontally scrolling wrapper. It also halves the page height, but 87 months sit in a ~720px
   pane that opens on the newest rows. If a long page is preferred, drop `max-h-*` from
   `.table-wrap`; the header then stops sticking (as it did before the pass).
2. **Step 1 built the table card early.** `.card-foot` needs a card; step 3 then filled it in.
3. **Six download buttons, not "the region's workbook + All States".** The gates pin six; the
   selected region leads and the others are quieter.
4. **The theme toggle is at the bottom of the page, not in the header.** The interaction gate's
   keyboard check presses Tab once and expects a region tab. A header toggle would take that focus,
   and its Enter would flip the theme.
5. **A second inline `<script>`** (in `<head>`, sets the theme before first paint). It is not a new
   dependency; PapaParse is still the only external script.
6. **Month cells are `<th scope="row" class="td …">`**, not `<td>`, for accessibility. `.td` is kept
   so the DOM-contract class still applies; both gates read them fine.
7. **"Deepest threshold crossed" shows `< −$80` for every region,** because every region has
   crossed the deepest tracked threshold. The tile's detail line (last month crossed, months
   crossed) is what differs between regions. The value is still computed, so it would change if a
   region never reached −$80.
