#!/usr/bin/env python3
"""Render + token check for the AEMO Negative Prices page — the gate this pass must leave green.

    cd ~/Design/"AEMO Negative Prices" && python3 -m http.server 9360 --bind 127.0.0.1 &
    /opt/anaconda3/bin/python3 scripts/verify-design.py            # checks only
    /opt/anaconda3/bin/python3 scripts/verify-design.py --screens  # + design/screens/after-*.png

Why a script and not an eyeball: the failures this page actually produces are invisible in a diff —
a component class Tailwind never emitted, a heat cell still carrying an inline `rgb()`, a theme flip
that changes nothing because the page hard-codes its colours, a phone-width overflow. Exit 1 = fix it.

The DOM contract it checks is written down in AGENTS.md (section "DOM contract") — the gate is only
fair where the brief names it.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "http://127.0.0.1:9360/index.html"
SCREENS = ROOT / "design" / "screens"
TOKEN_SRC = ROOT / "assets" / "css" / "tailwind.src.css"
PAGE = ROOT / "index.html"

fails: list[str] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def rgb(value: str) -> tuple[int, int, int] | None:
    """Normalise '#171717' and 'rgb(23, 23, 23)' / 'rgba(...)' to one tuple."""
    v = (value or "").strip()
    if v.startswith("#"):
        v = v.lstrip("#")
        if len(v) == 3:
            v = "".join(c * 2 for c in v)
        try:
            return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
        except ValueError:
            return None
    if v.startswith("rgb"):
        parts = v[v.index("(") + 1:v.index(")")].split(",")
        try:
            return tuple(int(float(p)) for p in parts[:3])  # type: ignore[return-value]
        except ValueError:
            return None
    return None


def token_sets() -> tuple[dict[str, str], dict[str, str]]:
    """Read the two theme blocks out of the token source — the values the page must agree with."""
    css = TOKEN_SRC.read_text()
    dark_part, _, light_part = css.partition('[data-theme="light"]')
    grab = lambda s: dict(re.findall(r"--([a-z0-9-]+)\s*:\s*([^;]+);", s))
    return grab(dark_part), grab(light_part)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screens", action="store_true", help="write design/screens/after-*.png")
    args = ap.parse_args()

    dark, light = token_sets()

    # ---------------------------------------------------------------- static checks
    print("static")
    page = PAGE.read_text()
    check(bool(re.search(r'href="assets/css/app\.css"', page)),
          "index.html links assets/css/app.css",
          "no <link> to the compiled token layer")
    hexes = [h for h in re.findall(r"#[0-9a-fA-F]{3,8}\b", page)]
    check(not hexes, "no raw hex colour in index.html", f"found {sorted(set(hexes))}")
    check(re.search(r"data-theme", page) is not None,
          "index.html carries the theme attribute (dark default / light flip)")

    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1440, "height": 900})
        errors: list[str] = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(URL, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(1200)

        print("tokens")
        app_css_status = pg.evaluate(
            "async () => (await fetch('assets/css/app.css')).status"
        )
        check(app_css_status == 200, "assets/css/app.css is served (200)", f"got {app_css_status}")
        body_bg = rgb(pg.evaluate("getComputedStyle(document.body).backgroundColor"))
        check(body_bg == rgb(dark["bg"]), "body background is the --bg token",
              f"body {body_bg} vs --bg {rgb(dark['bg'])}")
        n_cards = pg.eval_on_selector_all(".card", "e => e.length")
        check(n_cards >= 2, "the page is composed of .card panels", f"{n_cards} found")
        if n_cards:
            card_bg = rgb(pg.evaluate(
                "getComputedStyle(document.querySelector('.card')).backgroundColor"))
            check(card_bg == rgb(dark["surface"]), ".card background is the --surface token",
                  f"{card_bg} vs {rgb(dark['surface'])}")

        print("shell")
        n_kpi = pg.eval_on_selector_all(".kpi-value", "e => e.length")
        kpi_text = pg.eval_on_selector_all(
            ".kpi-value", "e => e.map(x => (x.innerText||'').trim()).filter(Boolean)")
        check(n_kpi >= 1, "a KPI row exists (.kpi-value)", f"{n_kpi} found")
        check(len(kpi_text) == n_kpi and all(kpi_text), "every KPI value renders text",
              f"empty: {n_kpi - len(kpi_text)}")

        print("the heat table")
        rows = pg.eval_on_selector_all("#tbody tr", "e => e.length")
        check(rows == 87, "87 month rows render for the default region", f"{rows} rows")
        heat = pg.eval_on_selector_all(
            "td", "e => e.filter(x => /%/.test(x.innerText)).map(x => ({cls: x.className, txt: x.innerText.trim(), bg: getComputedStyle(x).backgroundColor}))")
        check(len(heat) >= 700, "the heat cells render (9 thresholds x 87 months)",
              f"{len(heat)} cells")
        seq = [c for c in heat if re.search(r"\bseq-\d\b", c["cls"] or "")]
        check(len(seq) == len(heat), "every heat cell uses the .seq-* ramp",
              f"{len(heat) - len(seq)} cells not on the ramp")
        inline = [c for c in heat if "rgb" in (c["bg"] or "") and not re.search(r"\bseq-\d\b", c["cls"] or "")]
        check(not inline, "no heat cell carries an inline rgb() colour", f"{len(inline)} do")
        check(all(c["txt"] for c in heat), "every heat cell prints its number (colour is not the only signal)")
        used = {int(re.search(r"\bseq-(\d)\b", c["cls"]).group(1)) for c in seq if re.search(r"\bseq-(\d)\b", c["cls"])}
        check(len(used) >= 4, "the ramp is actually graded, not one flat step", f"steps used: {sorted(used)}")

        legend_txt = " ".join(pg.eval_on_selector_all(
            "[data-heat-legend], .seq-legend, .card-foot", "e => e.map(x => x.innerText)"))
        check("0%" in legend_txt and "100%" in legend_txt,
              "the heat scale is stated on screen (0% … 100%)", "no legend naming the stops")

        prov = pg.evaluate("document.body.innerText")
        check("Source:" in prov, "provenance states the source")
        check(bool(re.search(r"(as of|Data through|through)\s+\w+\s+\d{4}", prov)),
              "provenance states the as-of month")

        print("interaction hooks")
        tabs = pg.eval_on_selector_all("#tabs button, #tabs .seg-item", "e => e.map(x => x.innerText.trim())")
        check(len(tabs) == 5 and tabs[:1] == ["NSW"], "5 region tabs render", f"{tabs}")
        clean = pg.eval_on_selector_all("#tabs button, #tabs .seg-item",
                                       "e => e.map(x => ({t: x.innerText.trim(), h: x.getBoundingClientRect().height}))")
        check(all(c["h"] >= 28 for c in clean), "tab targets are >= 28px tall",
              f"{[c for c in clean if c['h'] < 28]}")
        before = pg.inner_text("#tbody tr:first-child")
        pg.evaluate("""(() => { const b=[...document.querySelectorAll('#tabs button, #tabs .seg-item')]
            .find(x => x.innerText.trim() === 'VIC'); b.click(); })()""")
        pg.wait_for_timeout(400)
        after = pg.inner_text("#tbody tr:first-child")
        check(before != after, "clicking a region tab re-renders the table", "row 1 unchanged")
        dl = pg.eval_on_selector_all("a[download]", "e => e.map(x => x.getAttribute('href'))")
        check(len(dl) == 6 and all(h and h.endswith(".xlsx") for h in dl),
              "6 Excel downloads are wired (5 regions + All States)", f"{dl}")

        print("themes and phone")
        flip = pg.evaluate("""(() => {
            const r = document.documentElement, before = getComputedStyle(document.body).backgroundColor;
            r.setAttribute('data-theme','light');
            const after = getComputedStyle(document.body).backgroundColor;
            r.setAttribute('data-theme','dark');
            return {before, after}; })()""")
        check(rgb(flip["after"]) == rgb(light["bg"]),
              "the light theme flips body to the light --bg token",
              f"{flip['after']} vs {rgb(light['bg'])}")

        phone = br.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        phone.goto(URL, wait_until="networkidle", timeout=60000)
        phone.wait_for_timeout(1000)
        over = phone.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check(over <= 1, "no page-level horizontal overflow at 390px", f"{over}px")
        wrapped = phone.evaluate("""(() => { const w = document.querySelector('.table-wrap, .card-body');
            return w ? w.scrollWidth > w.clientWidth : false; })()""")
        check(wrapped or over <= 1, "the wide numeric table scrolls inside its card at 390px")

        state = br.new_page(viewport={"width": 1440, "height": 900})
        state.route("**/outputs/summary.csv", lambda r: r.abort())
        state.goto(URL, wait_until="domcontentloaded", timeout=60000)
        state.wait_for_timeout(1500)
        st = state.eval_on_selector_all(".state", "e => e.map(x => x.innerText)")
        check(bool(st), "a missing data file renders a .state panel, not a bare error string",
              "no .state element")

        check(not errors, "no JS errors on load", "; ".join(errors[:3]))

        if args.screens:
            SCREENS.mkdir(parents=True, exist_ok=True)
            for fname, page_obj, full in (("after-top.png", pg, False), ("after-full.png", pg, True),
                                          ("after-phone.png", phone, True)):
                page_obj.screenshot(path=str(SCREENS / fname), full_page=full)
            state.screenshot(path=str(SCREENS / "after-nodata.png"))
            pg.evaluate("""(() => { const b=[...document.querySelectorAll('#tabs button, #tabs .seg-item')]
                .find(x => x.innerText.trim() === 'VIC'); b.click(); })()""")
            pg.wait_for_timeout(600)
            pg.screenshot(path=str(SCREENS / "after-vic-top.png"))
            print(f"  wrote screenshots to {SCREENS}")

        br.close()

    print(f"\n{len(fails)} check(s) failed" if fails else "\nall checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
