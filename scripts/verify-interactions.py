#!/usr/bin/env python3
"""Behaviour check for the AEMO Negative Prices page — every interaction a design pass must NOT lose.

    cd ~/Design/"AEMO Negative Prices" && python3 -m http.server 9382 --bind 127.0.0.1 &
    /opt/anaconda3/bin/python3 scripts/verify-interactions.py

Green TODAY, on the unstyled page, and it must still be green at handback: it tests what the page
does, not what it looks like. Numbers are read from outputs/summary.csv itself, so a restyle that
silently re-maps a column fails here. Reads only; writes nothing. Exit 1 on any breakage.
"""
from __future__ import annotations

import csv
import pathlib
import sys
from decimal import ROUND_HALF_UP, Decimal

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "http://127.0.0.1:9382/index.html"
CSV = ROOT / "outputs" / "summary.csv"
REGIONS = {"NSW": "NSW1", "QLD": "QLD1", "VIC": "VIC1", "SA": "SA1", "TAS": "TAS1"}
THRESHOLDS = ["0", "neg10", "neg20", "neg30", "neg40", "neg50", "neg60", "neg70", "neg80"]

fails: list[str] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def read_csv() -> list[dict[str, str]]:
    with CSV.open() as fh:
        return list(csv.DictReader(fh))


rows = read_csv()
months = sorted({r["YEAR_MONTH"] for r in rows})
latest = months[-1]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def label(ym: str) -> str:
    y, m = ym.split("-")
    return f"{MONTHS[int(m) - 1]} {y}"


TH_LABELS = ["< $0", "< −$10", "< −$20", "< −$30", "< −$40", "< −$50", "< −$60", "< −$70", "< −$80"]
NAMES = {v: k for k, v in REGIONS.items()}


def region_rows(region: str) -> list[dict[str, str]]:
    return sorted((r for r in rows if r["REGIONID"] == region), key=lambda r: r["YEAR_MONTH"])


def pct2(v: str) -> str:
    """Two decimals, rounded on the exact decimal in the file (not a binary float)."""
    return f"{Decimal(v).quantize(Decimal('0.01'), ROUND_HALF_UP)}%"


def thousands(v: str) -> str:
    return f"{int(v):,}"


def expected_kpis(region: str) -> list[list[str]]:
    """The KPI row recomputed from summary.csv alone — value, label, note for each of the four tiles."""
    reg = region_rows(region)
    last = reg[-1]
    month = last["YEAR_MONTH"]
    now = Decimal(last["pct_below_0"])
    t1 = [pct2(last["pct_below_0"]), f"Below $0 · {label(month)}",
          f"{thousands(last['count_below_0'])} of {thousands(last['total_daylight_intervals'])} daylight intervals"]

    y, m = month.split("-")
    prev_month = f"{int(y) - 1}-{m}"
    prev = next((r for r in reg if r["YEAR_MONTH"] == prev_month), None)
    if prev:
        then = Decimal(prev["pct_below_0"])
        d = now - then
        word = "unchanged" if abs(d) < Decimal("0.005") else \
            f"{'up' if d > 0 else 'down'} {abs(d).quantize(Decimal('0.01'), ROUND_HALF_UP)} pts"
        t2 = [pct2(prev["pct_below_0"]), f"Below $0 · {label(prev_month)}", f"{label(month)} is {word}"]
    else:
        t2 = ["N/A", f"Below $0 · {label(prev_month)}", "no row for this month in the data"]

    deep = max((i for i, t in enumerate(THRESHOLDS) if any(int(r[f"count_below_{t}"]) > 0 for r in reg)),
               default=-1)
    if deep >= 0:
        hits = [r for r in reg if int(r[f"count_below_{THRESHOLDS[deep]}"]) > 0]
        t3 = [TH_LABELS[deep], "Deepest threshold crossed",
              f"last in {label(hits[-1]['YEAR_MONTH'])} · {len(hits)} of {len(reg)} months"]
    else:
        t3 = ["None", "Deepest threshold crossed", f"no interval below $0 in {len(reg)} months"]

    peers = [r for r in rows if r["YEAR_MONTH"] == month]
    higher = sum(Decimal(r["pct_below_0"]) > now for r in peers)
    tied = sum(r["REGIONID"] != region and Decimal(r["pct_below_0"]) == now for r in peers)
    top = peers[0]
    for r in peers[1:]:                       # first-wins on ties, as the page's reduce does
        if Decimal(r["pct_below_0"]) > Decimal(top["pct_below_0"]):
            top = r
    note = (f"highest of the {len(peers)} in {label(month)}" if top["REGIONID"] == region
            else f"highest: {NAMES[top['REGIONID']]} at {pct2(top['pct_below_0'])}")
    t4 = [f"{'=' if tied else ''}{higher + 1} of {len(peers)}", f"Rank below $0 · {label(month)}", note]
    return [t1, t2, t3, t4]


def click_tab(page, name: str) -> None:
    page.evaluate("""(label) => { const b = [...document.querySelectorAll('#tabs button, #tabs .seg-item')]
        .find(x => x.innerText.trim() === label); b.click(); }""", name)
    page.wait_for_timeout(300)


print(f"csv: {len(rows)} rows · {len(months)} months · latest {latest}")

with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1440, "height": 900})
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(1200)

    print("data")
    check(pg.eval_on_selector_all("#tbody tr", "e => e.length") == len(months),
          "the active region renders one row per month",
          f"{pg.eval_on_selector_all('#tbody tr', 'e => e.length')} rows vs {len(months)} months")
    check(bool(pg.eval_on_selector_all(".tab.active, .seg-item-active, [aria-selected=true]",
                                       "e => e.length")),
          "exactly one region tab is marked active")

    print("tabs")
    for name, region in REGIONS.items():
        click_tab(pg, name)
        reg = region_rows(region)
        n = pg.eval_on_selector_all("#tbody tr", "e => e.length")
        check(n == len(reg), f"{name} tab renders {len(reg)} rows (its months in the csv)", f"{n} rows")
        first = pg.inner_text("#tbody tr:first-child")
        first_label = label(reg[0]["YEAR_MONTH"])
        check(first.startswith(first_label), f"{name} first row is {first_label}", first[:40])

    print("values match the csv (every region, every cell, the KPI row and the badges)")
    for name, region in REGIONS.items():
        click_tab(pg, name)
        reg = region_rows(region)
        table = pg.eval_on_selector_all(
            "#tbody tr", "rows => rows.map(r => [...r.children].map(c => c.innerText.trim()))")
        by_month = {r[0]: r[1:] for r in table}
        want = {label(r["YEAR_MONTH"]): [pct2(r["pct_below_" + t]) for t in THRESHOLDS] for r in reg}
        missing = [m for m in want if m not in by_month]
        extra = [m for m in by_month if m not in want]
        mismatched = [(m, by_month[m], want[m]) for m in want if m in by_month and by_month[m] != want[m]]
        check(not missing and not extra and not mismatched,
              f"{name}: every cell equals summary.csv ({len(THRESHOLDS)} thresholds x {len(reg)} months)",
              f"missing {missing[:2]}, extra {extra[:2]}, {len(mismatched)} mismatched, e.g. {mismatched[:2]}")

        tiles = pg.eval_on_selector_all(
            "#kpis > div", "e => e.map(t => [...t.children].map(c => c.innerText.trim()))")
        exp = expected_kpis(region)
        check(tiles == exp, f"{name}: the four KPI tiles equal the figures recomputed from the csv",
              f"page {tiles} vs csv {exp}")

        badges = pg.eval_on_selector_all("#badges .badge", "e => e.map(x => x.innerText.trim())")
        want_b = [f"{len(reg)} months", f"{label(reg[0]['YEAR_MONTH'])} – {label(reg[-1]['YEAR_MONTH'])}",
                  f"{len(THRESHOLDS)} thresholds"]
        check(badges == want_b, f"{name}: the table badges state the csv's span", f"{badges} vs {want_b}")
    click_tab(pg, "VIC")
    table = pg.eval_on_selector_all(
        "#tbody tr", "rows => rows.map(r => [...r.children].map(c => c.innerText.trim()))")

    print("table shape")
    heads = pg.eval_on_selector_all("#thead th", "e => e.map(x => x.innerText.trim())")
    check(len(heads) == 10, "10 header cells (month + 9 thresholds)", f"{heads}")
    check("80" in heads[-1] and "0" in heads[1], "the threshold headers run $0 -> -$80", f"{heads}")
    non_increasing = [r for r in table if any(float(a.rstrip("%")) < float(b.rstrip("%"))
                                              for a, b in zip(r[1:], r[2:]))]
    check(not non_increasing, "each row is non-increasing across thresholds (no column re-mapped)",
          f"{len(non_increasing)} rows out of order")
    sticky = pg.eval_on_selector_all("#thead th", "e => e.map(x => getComputedStyle(x).position)")
    check(all(s == "sticky" for s in sticky), "header cells stay sticky", f"{set(sticky)}")

    print("downloads and footer")
    hrefs = pg.eval_on_selector_all("a[download]", "e => e.map(x => x.getAttribute('href'))")
    want = ["NSW_negative_prices.xlsx", "QLD_negative_prices.xlsx", "VIC_negative_prices.xlsx",
            "SA_negative_prices.xlsx", "TAS_negative_prices.xlsx", "All_States_negative_prices.xlsx"]
    check(len(hrefs) == 6 and all(any(h.endswith(w) for w in want) for h in hrefs),
          "the 6 Excel downloads keep their targets", f"{hrefs}")
    foot = pg.inner_text("#footer") if pg.query_selector("#footer") else pg.inner_text("body")
    check(label(latest) in foot, f"the footer states the as-of month ({label(latest)})", foot[-120:])
    check("Source:" in foot, "the footer states the source")

    print("keyboard")
    pg.keyboard.press("Tab")
    focused = pg.evaluate("document.activeElement.innerText.trim()")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(300)
    check(bool(focused), "a region tab can take focus", f"activeElement={focused!r}")

    print("phone")
    phone = br.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    phone.goto(URL, wait_until="networkidle", timeout=60000)
    phone.wait_for_timeout(1000)
    wrap = phone.evaluate("""(() => { const w = document.querySelector('.table-wrap');
        if (!w) return null; w.scrollLeft = 9999;
        return {sw: w.scrollWidth, cw: w.clientWidth, sl: w.scrollLeft}; })()""")
    check(wrap is not None, "the table lives in a scrollable wrapper at 390px")
    check(wrap and wrap["sw"] > wrap["cw"] and wrap["sl"] > 0,
          "the last threshold columns are reachable by scrolling the table", f"{wrap}")
    check(phone.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1,
          "the page itself does not scroll sideways at 390px")

    check(not errors, "no JS/console errors", "; ".join(errors[:3]))
    br.close()

print(f"\n{len(fails)} check(s) failed" if fails else "\nall interactions intact")
sys.exit(1 if fails else 0)
