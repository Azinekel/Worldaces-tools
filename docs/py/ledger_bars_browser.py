"""Browser adapter for ledger_bars
"""
from __future__ import annotations

import json
import io
import base64
from collections import defaultdict

import matplotlib.pyplot as plt

# (Contents copied from docs/py/ledger_bars_browser.py)
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


def _pick(fieldnames, candidates, override=None):
    if override:
        if override not in fieldnames:
            raise ValueError(f"column {override!r} not in data; available: {', '.join(fieldnames)}")
        return override
    lower = {f.lower(): f for f in fieldnames}
    for c in candidates:
        if c in lower:
            return lower[c]
    return None


def _from_json(blob):
    if isinstance(blob, dict):
        for key in ("transactions", "data", "records", "items", "results"):
            if isinstance(blob.get(key), list):
                return blob[key]
        raise ValueError("JSON object has no list under any of: transactions/data/records")
    if not isinstance(blob, list):
        raise ValueError("JSON must be a list of records or an object wrapping one")
    return blob


def aggregate(records, cols, top=None):
    buckets = {"income": defaultdict(lambda: [0.0, 0]), "expense": defaultdict(lambda: [0.0, 0])}
    skipped = 0
    for rec in records:
        raw = rec.get(cols["amount"])
        try:
            value = float(str(raw).replace(",", "").replace("$", "").strip())
        except (TypeError, ValueError):
            skipped += 1
            continue

        if cols.get("type"):
            token = str(rec.get(cols["type"], "")).strip().lower()
            side = "expense" if any(w in token for w in EXPENSE_WORDS) else "income"
        else:
            side = "expense" if value < 0 else "income"

        name = str(rec.get(cols["source"], "") or "Unspecified")
        entry = buckets[side][name]
        entry[0] += abs(value)
        entry[1] += 1

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


def _prettify(name):
    if name.isupper() or "_" in name:
        return name.replace("_", " ").capitalize()
    return name


def _panel(ax, rows, colour, title, vmax, money, c):
    ax.set_facecolor(c["surface"]) 
    total = sum(r["total"] for r in rows)
    ax.text(0, 1.0, title.upper(), transform=ax.transAxes, ha="left", va="bottom",
            fontsize=8.5, fontweight="bold", color=c["ink2"]) 
    ax.text(1.0, 1.0, money(total), transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8.5, fontweight="bold", color=c["ink"]) 
    ax.plot([0, 1], [1.0, 1.0], transform=ax.transAxes, color=c["rule_strong"],
            linewidth=0.9, clip_on=False)

    for i, row in enumerate(rows):
        y = len(rows) - 1 - i
        ax.barh(y, row["total"], height=0.30, color=colour, zorder=3, linewidth=0)
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
        raise ValueError("nothing to plot -- no income and no expenditure rows")

    def money(v):
        return f"{currency}{v:,.0f}"

    vmax = max([r["total"] for r in inc + exp])
    rows_tall = max(len(inc), len(exp), 1)
    fig, axes = plt.subplots(
        1, 2, figsize=(13, 1.5 + rows_tall * 0.78),
        facecolor=c["surface"], gridspec_kw={"wspace": 0.30},
    )
    fig.patch.set_facecolor(c["surface"])

    _panel(axes[0], inc, c["income"], "Income", vmax, money, c)
    _panel(axes[1], exp, c["expense"], "Expenditure", vmax, money, c)

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


def render_from_json(json_text, theme="light", title=None, subtitle=None, currency="", dpi=150):
    blob = json.loads(json_text)
    records = _from_json(blob)
    if not records:
        raise ValueError("no transactions found in input")
    fields = list(records[0].keys())
    amount = _pick(fields, AMOUNT_KEYS)
    source = _pick(fields, SOURCE_KEYS)
    ttype = _pick(fields, TYPE_KEYS)
    if amount is None or source is None:
        raise ValueError(f"could not detect amount/source columns; available: {', '.join(fields)}")
    cols = {"amount": amount, "source": source, "type": ttype}
    data = aggregate(records, cols)
    fig = draw(data, theme=theme, title=title, subtitle=subtitle, currency=currency)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, facecolor=fig.get_facecolor())
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode('ascii')
    plt.close(fig)
    return b64
