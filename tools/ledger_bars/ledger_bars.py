#!/usr/bin/env python3
"""Faceted income-vs-expenditure bar chart for a transaction ledger.

Two panels sharing ONE value scale, so a bar on the left is directly comparable to
a bar on the right. Colour carries polarity only (income vs expenditure) -- never
identity -- so the palette is two hues, not one per source.

Standalone: no imports from this package. Copy this single file anywhere.

    python ledger_bars.py --input transactions.json
    python ledger_bars.py --input ledger.csv --amount-col value --source-col category
    python ledger_bars.py --input transactions.json --out ledger.png --theme dark

Input may be:
  * JSON  -- a list of records, or {"transactions": [...]}
  * CSV   -- any delimiter sniffable by csv.Sniffer
  * stdin -- "--input -" reads JSON from stdin

Columns are auto-detected and can be overridden. If no income/expense column
exists, direction is taken from the sign of the amount (negative = expenditure).

Palette note: the blue/red diverging pair is validated for colour-vision
deficiency in both themes (worst-pair OKLab dE 21.6 light / 19.2 dark against a
target of 8). Swap the hexes only if you re-validate them.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict

import matplotlib.pyplot as plt

# ── palette ───────────────────────────────────────────────────────────────────
THEMES = {
    "light": {
        "income": "#2a78d6", "expense": "#e34948",
        "surface": "#ffffff", "ink": "#10141a", "ink2": "#4a545f",
        "ink3": "#6e7782", "rule": "#dfe4ea", "rule_strong": "#c3cad2",
    },
    "dark": {
        "income": "#3987e5", "expense": "#e66767",
        "surface": "#16191d", "ink": "#f4f6f8", "ink2": "#b6bec7",
        "ink3": "#88929d", "rule": "#262b31", "rule_strong": "#363c44",
    },
}

AMOUNT_KEYS = ("amount", "value", "total", "sum", "cost")
SOURCE_KEYS = ("sourcetype", "source", "category", "reason", "description", "label")
TYPE_KEYS = ("type", "direction", "kind", "flow")

EXPENSE_WORDS = ("expense", "expenditure", "debit", "spend", "out", "cost", "payment")


# ── loading ───────────────────────────────────────────────────────────────────
def _pick(fieldnames, candidates, override=None):
    """Resolve a column name: explicit override wins, else first candidate present."""
    if override:
        if override not in fieldnames:
            raise SystemExit(
                f"column {override!r} not in data; available: {', '.join(fieldnames)}"
            )
        return override
    lower = {f.lower(): f for f in fieldnames}
    for c in candidates:
        if c in lower:
            return lower[c]
    return None


def _read_records(path):
    """Return a list of dicts from JSON, CSV, or stdin."""
    if path == "-":
        return _from_json(json.load(sys.stdin))
    with open(path, "r", encoding="utf-8-sig") as fh:
        head = fh.read(2048)
        fh.seek(0)
        if head.lstrip()[:1] in "[{":
            return _from_json(json.load(fh))
        try:
            dialect = csv.Sniffer().sniff(head)
        except csv.Error:
            dialect = csv.excel
        return list(csv.DictReader(fh, dialect=dialect))


def _from_json(blob):
    if isinstance(blob, dict):
        for key in ("transactions", "data", "records", "items", "results"):
            if isinstance(blob.get(key), list):
                return blob[key]
        raise SystemExit("JSON object has no list under any of: transactions/data/records")
    if not isinstance(blob, list):
        raise SystemExit("JSON must be a list of records or an object wrapping one")
    return blob


def load(path, amount_col=None, source_col=None, type_col=None):
    """Return (records, resolved_column_names)."""
    records = _read_records(path)
    if not records:
        raise SystemExit("no transactions found in input")

    fields = list(records[0].keys())
    amount = _pick(fields, AMOUNT_KEYS, amount_col)
    source = _pick(fields, SOURCE_KEYS, source_col)
    ttype = _pick(fields, TYPE_KEYS, type_col)
    if amount is None:
        raise SystemExit(f"no amount column found; use --amount-col. Available: {', '.join(fields)}")
    if source is None:
        raise SystemExit(f"no source column found; use --source-col. Available: {', '.join(fields)}")
    return records, {"amount": amount, "source": source, "type": ttype}


def aggregate(records, cols, top=None):
    """Fold records into {'income': [...], 'expense': [...]}, each sorted desc.

    Direction comes from the type column when present, otherwise from the sign of
    the amount. Magnitudes are always positive.
    """
    buckets = {"income": defaultdict(lambda: [0.0, 0]), "expense": defaultdict(lambda: [0.0, 0])}
    skipped = 0
    for rec in records:
        raw = rec.get(cols["amount"])
        try:
            value = float(str(raw).replace(",", "").replace("$", "").strip())
        except (TypeError, ValueError):
            skipped += 1
            continue

        if cols["type"]:
            token = str(rec.get(cols["type"], "")).strip().lower()
            side = "expense" if any(w in token for w in EXPENSE_WORDS) else "income"
        else:
            side = "expense" if value < 0 else "income"

        name = str(rec.get(cols["source"], "") or "Unspecified")
        entry = buckets[side][name]
        entry[0] += abs(value)
        entry[1] += 1

    if skipped:
        print(f"  skipped {skipped} row(s) with an unparseable amount", file=sys.stderr)

    out = {}
    for side, group in buckets.items():
        rows = sorted(
            ({"source": k, "total": v[0], "n": v[1]} for k, v in group.items()),
            key=lambda r: -r["total"],
        )
        if top and len(rows) > top:
            tail = rows[top:]
            rows = rows[:top] + [{
                "source": f"Other ({len(tail)} sources)",
                "total": sum(r["total"] for r in tail),
                "n": sum(r["n"] for r in tail),
            }]
        out[side] = rows
    return out


# ── drawing ───────────────────────────────────────────────────────────────────
def _prettify(name):
    """MATCH_REWARD -> Match reward. Leaves already-readable names alone."""
    if name.isupper() or "_" in name:
        return name.replace("_", " ").capitalize()
    return name


def _panel(ax, rows, colour, title, vmax, money, c):
    ax.set_facecolor(c["surface"])

    total = sum(r["total"] for r in rows)
    # Facet header: name left, total right, on a rule.
    ax.text(0, 1.0, title.upper(), transform=ax.transAxes, ha="left", va="bottom",
            fontsize=8.5, fontweight="bold", color=c["ink2"])
    ax.text(1.0, 1.0, money(total), transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8.5, fontweight="bold", color=c["ink"])
    ax.plot([0, 1], [1.0, 1.0], transform=ax.transAxes, color=c["rule_strong"],
            linewidth=0.9, clip_on=False)

    for i, row in enumerate(rows):
        y = len(rows) - 1 - i          # first row at the top
        ax.barh(y, row["total"], height=0.30, color=colour, zorder=3, linewidth=0)
        # name + count sit above the bar; value rides just past its tip
        ax.text(0, y + 0.34, _prettify(row["source"]), ha="left", va="bottom",
                fontsize=9.5, fontweight="bold", color=c["ink"])
        ax.text(vmax * 1.20, y + 0.34, f"×{row['n']:,}", ha="right", va="bottom",
                fontsize=8, color=c["ink3"])
        ax.text(row["total"] + vmax * 0.015, y, money(row["total"]), ha="left", va="center",
                fontsize=9.5, fontweight="bold", color=c["ink"])

    ax.set_xlim(0, vmax * 1.20)
    ax.set_ylim(-0.6, len(rows) - 0.35)
    ax.set_yticks([])
    ax.set_xticks([0, vmax])
    ax.set_xticklabels(["0", money(vmax)], fontsize=7.5, color=c["ink3"])
    ax.tick_params(axis="x", length=0, pad=6)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(c["rule"])
    ax.spines["bottom"].set_linewidth(0.8)


def draw(data, theme="light", title=None, subtitle=None, currency=""):
    c = THEMES[theme]
    inc, exp = data["income"], data["expense"]
    if not inc and not exp:
        raise SystemExit("nothing to plot -- no income and no expenditure rows")

    def money(v):
        return f"{currency}{v:,.0f}"

    # ONE scale across both panels. This is the whole point of the layout: bar
    # lengths must be comparable across the facet boundary.
    vmax = max([r["total"] for r in inc + exp])

    rows_tall = max(len(inc), len(exp), 1)
    fig, axes = plt.subplots(
        1, 2, figsize=(13, 1.5 + rows_tall * 0.78),
        facecolor=c["surface"], gridspec_kw={"wspace": 0.30},
    )
    fig.patch.set_facecolor(c["surface"])

    _panel(axes[0], inc, c["income"], "Income", vmax, money, c)
    _panel(axes[1], exp, c["expense"], "Expenditure", vmax, money, c)

    # Equal row pitch across panels even when one side has fewer sources.
    for ax, rows in zip(axes, (inc, exp)):
        ax.set_ylim(-0.6, rows_tall - 0.35)

    head = title or "Where the money comes from, and where it goes"
    fig.suptitle(head, x=0.037, y=0.990, ha="left", va="top", fontsize=16.5,
                 fontweight="bold", color=c["ink"])
    sub = subtitle or (
        f"{sum(r['n'] for r in inc + exp):,} transactions · both panels share one scale, "
        f"so bars are comparable across the divide · ×n = transaction count"
    )
    fig.text(0.037, 0.928, sub, ha="left", va="top", fontsize=9.5, color=c["ink2"])

    # Legend: identity never rests on colour alone.
    handles = [
        plt.Line2D([], [], marker="s", linestyle="", markersize=8,
                   markerfacecolor=c["income"], markeredgecolor="none", label="Income"),
        plt.Line2D([], [], marker="s", linestyle="", markersize=8,
                   markerfacecolor=c["expense"], markeredgecolor="none", label="Expenditure"),
    ]
    leg = fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.965, 1.0),
                     frameon=False, ncol=2, fontsize=9.5, handletextpad=0.5, columnspacing=1.4)
    for text in leg.get_texts():
        text.set_color(c["ink2"])

    fig.subplots_adjust(top=0.86, bottom=0.07, left=0.037, right=0.965)
    return fig


# ── cli ───────────────────────────────────────────────────────────────────────
def main(argv=None):
    p = argparse.ArgumentParser(
        description="Faceted income vs expenditure bar chart from a transaction ledger.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", required=True, help="path to a JSON or CSV ledger, or '-' for JSON on stdin")
    p.add_argument("--out", help="write a PNG here instead of opening a window")
    p.add_argument("--theme", choices=("light", "dark"), default="light")
    p.add_argument("--top", type=int, help="keep the N largest sources per side, fold the rest into 'Other'")
    p.add_argument("--currency", default="", help="prefix for money labels, e.g. '$'")
    p.add_argument("--title", help="override the headline")
    p.add_argument("--subtitle", help="override the standfirst")
    p.add_argument("--amount-col", help="override the amount column")
    p.add_argument("--source-col", help="override the source/category column")
    p.add_argument("--type-col", help="override the income/expense column")
    p.add_argument("--dpi", type=int, default=200)
    args = p.parse_args(argv)

    records, cols = load(args.input, args.amount_col, args.source_col, args.type_col)
    detected = ", ".join(f"{k}={v!r}" for k, v in cols.items() if v)
    print(f"{len(records):,} transactions · columns: {detected}")
    if not cols["type"]:
        print("  no income/expense column found -- using the sign of the amount")

    data = aggregate(records, cols, top=args.top)

    # Print the figures too, so a terminal run is useful on its own.
    for side in ("income", "expense"):
        rows = data[side]
        if not rows:
            continue
        print(f"\n{side.upper():<12} {sum(r['total'] for r in rows):>14,.0f}")
        for r in rows:
            print(f"  {_prettify(r['source']):<28} {r['total']:>12,.0f}  n={r['n']:,}")
    inc_t = sum(r["total"] for r in data["income"])
    exp_t = sum(r["total"] for r in data["expense"])
    print(f"\n{'NET':<12} {inc_t - exp_t:>14,.0f}")

    fig = draw(data, theme=args.theme, title=args.title, subtitle=args.subtitle,
               currency=args.currency)
    if args.out:
        fig.savefig(args.out, dpi=args.dpi, facecolor=fig.get_facecolor())
        print(f"\nwrote {args.out}")
    else:
        plt.show()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
