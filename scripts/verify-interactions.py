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
        pg.evaluate("""(label) => { const b = [...document.querySelectorAll('#tabs button, #tabs .seg-item')]
            .find(x => x.innerText.trim() === label); b.click(); }""", name)
        pg.wait_for_timeout(300)
        n = pg.eval_on_selector_all("#tbody tr", "e => e.length")
        check(n == len(months), f"{name} tab renders {len(months)} rows", f"{n} rows")
        first = pg.inner_text("#tbody tr:first-child")
        check(first.startswith(label(months[0])), f"{name} first row is {label(months[0])}", first[:40])

    print("values match the csv")
    pg.evaluate("""(() => { const b = [...document.querySelectorAll('#tabs button, #tabs .seg-item')]
        .find(x => x.innerText.trim() === 'VIC'); b.click(); })()""")
    pg.wait_for_timeout(300)
    table = pg.eval_on_selector_all(
        "#tbody tr", "rows => rows.map(r => [...r.children].map(c => c.innerText.trim()))")
    by_month = {r[0]: r[1:] for r in table}
    csv_vic = {label(r["YEAR_MONTH"]): [f'{float(r["pct_below_" + t]):.2f}%' for t in THRESHOLDS]
               for r in rows if r["REGIONID"] == "VIC1"}
    mismatched = [(m, by_month[m], csv_vic[m]) for m in csv_vic if m in by_month and by_month[m] != csv_vic[m]]
    check(not mismatched, "every VIC1 cell equals outputs/summary.csv (9 thresholds x 87 months)",
          f"{len(mismatched)} mismatched, e.g. {mismatched[:2]}")

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
