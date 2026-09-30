# Design-pass contract — AEMO Negative Prices

Read this before touching anything. `BRIEF.md` says *what* to build; this says how work here is
allowed to happen.

## The five hard rules

1. **Work on the branch, never on `main`.** This copy is on `design/2026-10`. `main` is published:
   GitHub Pages serves this repository and the NAS lane pushes `outputs/**` to it. Nothing lands on
   `main` until Zalen has looked at the rendered page.
2. **Presentation only.** Never touch the data or the pipeline: `outputs/**`, `data/**`, `src/**`,
   `deploy/**`, `.github/**`, `requirements.txt` and `tests/**` are off limits. This pass changes how
   the page looks, never what it says.
3. **Never invent data.** Every number on screen comes from `outputs/summary.csv` (435 rows — 5
   regions × 87 months, May 2019 → Jul 2026). No mock arrays, no sample series, no "for now" values.
   An empty panel is a state, not a gap to fill.
4. **Verify in a browser, not by grep.** Done = a real browser renders it with real data: element
   present, height > 0, text non-empty. An HTTP 200 on the HTML proves nothing about a visual change.
5. **Keep the three gates green.** They are committed and they are the handback evidence:

   | command | today (measured 2026-09-30, before the pass) | at handback |
   |---|---|---|
   | `/opt/anaconda3/bin/python3 tests/validate_outputs.py` | exit 0 — "All validations passed" | exit 0 (the data gate; not yours to edit) |
   | `/opt/anaconda3/bin/python3 scripts/verify-interactions.py` | exit 0 — 25 checks, "all interactions intact" | exit 0, unchanged |
   | `/opt/anaconda3/bin/python3 scripts/verify-design.py` | **exit 1** — 12 of 26 checks fail (listed in `BRIEF.md`) | **exit 0** — this is the pass's own gate |

## Facts

| | |
|---|---|
| What it is | One static page: `index.html` (142 lines — one inline `<style>`, one inline `<script>`) |
| Served by | **GitHub Pages from the repository root.** `.github/workflows/deploy-pages.yml` uploads `path: .` on any push to `main` touching `outputs/**`, `index.html` or `README.md`. Public, no server, no login, no build step at deploy. |
| **Everything committed here is public** | the published site *is* the tree at that commit. Never commit a secret, a private snapshot, or a screenshot you would not publish. Evidence lives in `design/` **on the branch** — it is not part of the site only for as long as it never reaches `main`. |
| Stack | hand-written HTML/CSS + vanilla JS · PapaParse 5.4.1 (CDN) for the CSV · the compiled Tailwind stylesheet `assets/css/app.css`, built by the standalone CLI (no Node, no npm) |
| Data | `outputs/summary.csv` (435 rows, 20 cols) + 6 regional/all-states `.xlsx`, fetched relative to the page — served because they are committed |
| Design language | `assets/css/tailwind.src.css` (the only file with literal colours) → `./scripts/build-css.sh` → `assets/css/app.css` (committed). Rules: `design/design-tokens.md`. Proof page: `design/tokens.html` |
| Data lane | `deploy/run-update.sh` on the NAS (QNAP `ai-wif-runner`): fetch → `checkout main` → `pull --ff-only`, **falling back to `git reset --hard origin/main`** → pipeline → validate → commit `outputs/**` as `aemo-nas-bot` → push. It never writes `index.html`. |
| Why this copy exists | The live checkout is `~/Documents/Zalen/AI Wif Brain Projects/AEMO Negative Prices`. The lane hard-resets it to `origin/main`, and macOS TCC blocks GUI agents (Claude Desktop) from running git under `~/Documents`. This clone carries its own `.git` and cannot be clobbered. |

## Local preview

```bash
cd ~/Design/"AEMO Negative Prices" && /opt/anaconda3/bin/python3 -m http.server 9360 --bind 127.0.0.1
# http://127.0.0.1:9360/index.html      9360 is this pass's port — do not take another
```

Cloud browsers cannot reach `127.0.0.1`; screenshots and checks go through Playwright:

```bash
/opt/anaconda3/bin/python3 scripts/verify-design.py --screens   # + design/screens/after-*.png
```

## DOM contract — the hooks the gates and the next agent depend on

| Hook | Meaning |
|---|---|
| `<html data-theme="dark\|light">` + a toggle control | theme; `?theme=light` / `?theme=dark` must force one |
| `#tabs` → `.seg` > `.seg-item` (active = `.seg-item-active`) | the 5 region switches |
| `#table`, `#thead`, `#tbody`, `.th` / `.td` | the heat table |
| heat cells: `td` carrying `seq-0` … `seq-7` | the ramp — no inline `rgb()` |
| `[data-heat-legend]` (or the card foot) naming `0%` and `100%` | the stated scale |
| `.kpi-value` + `.kpi-label` | the KPI row |
| `.state` > `.state-title` + `.state-body` | loading / missing-file / no-rows states |
| `a[download]` × 6 | the Excel downloads |
| `#footer` (or `.card-foot`) containing `Source:` and the as-of month | provenance |

Renaming or dropping any of these breaks a committed gate. If a name must change, change the gate in
the same commit and say why.

## Pitfalls

- **The heat colour is currently computed in JS per cell** (`heatColor()` / `textColor()` in the
  inline script). On the ramp the JS picks a *step* (`seq-3`), never a colour, and the light-theme
  variant comes from the tokens — that is what makes the theme flip work with no extra code.
- **Tailwind purges what its scanner cannot see.** `index.html` is a content source (so class strings
  built in the inline script are found), but a class you add only to the *CSS* does nothing until
  `./scripts/build-css.sh` runs and `assets/css/app.css` is committed.
- `.seq-*` are deliberately outside `@layer`, so purging never removes them.
- **Preflight is ON** in `tailwind.config.js`: it becomes the page's only reset the moment the inline
  `* { margin:0; padding:0 }` and body rules go (BRIEF step 1). Until then the inline block still wins
  — `app.css` is linked *before* it.
- The inline `<script>` also builds the tabs, the downloads row and the footer text. It is part of the
  page, not a separate asset.
- Nothing in this repo feeds the Brain dashboard or any lane. Do not add a side channel.

## Finishing (the handback)

- [ ] Working tree clean; everything committed **on `design/2026-10`**.
- [ ] Branch pushed: `git push -u origin design/2026-10` — a branch that exists only in this folder
      dies with the folder. (Do not push `main`, do not merge, do not open a PR.)
- [ ] All three gates run and their exact results stated.
- [ ] After-screenshots in `design/screens/` (desktop + phone, same scroll positions as `before-*.png`).
- [ ] `./scripts/build-css.sh` run after the last class change; `assets/css/app.css` committed.
- [ ] `git diff --stat main` shows no `outputs/**`, `src/**`, `deploy/**`, `tests/**`, `.github/**`.
- [ ] `docs/design-pass-2026-09-30.md` — what changed (files + visual summary), how it was verified,
      what you deliberately left alone, anything you suspect you bent. This is how the next agent
      reconstructs intent without the transcript.
- [ ] A short report: surfaces changed of the ones that exist; what is half-done; decisions the brief
      did not cover.

If time runs out mid-change: commit what works, leave the branch pushed, and say plainly what is
half-done. Never leave a half-finished change uncommitted — an end-session sweep would commit it as
one opaque blob.
