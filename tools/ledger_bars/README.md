# ledger_bars

Two-panel bar chart (income / expenses) sharing a single scale, generated from a WorldAces
transaction export. Useful for seeing at a glance where money comes from and where it goes.

**Author:** Gutek

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python ledger_bars.py --input example_input.json
python ledger_bars.py --input transactions.csv --amount-col value --source-col category
python ledger_bars.py --input example_input.json --out ledger.png --theme dark
```

The script also works on its own (copy it as-is, with no dependency on the rest of the repo).

## Input format

JSON (list of records, or an object with a `transactions`/`data`/`records` key) or CSV. Columns are
auto-detected:

- **amount** : `amount`, `value`, `total`, `sum`, `cost`
- **source/category** : `sourcetype`, `source`, `category`, `reason`, `description`, `label`
- **type** (income/expense, optional) : `type`, `direction`, `kind`, `flow` — if absent, the sign of
  the amount determines the direction (negative = expense)

See [`example_input.json`](./example_input.json) for a minimal example.

Can be generated with this worldaces api point : https://api.worldaces.site/team/manage/transactions?page=&limit=100

## Useful options

| Option | Effect |
|---|---|
| `--top N` | Keep only the N largest sources on each side, grouping the rest under "Other" |
| `--theme dark` | Dark theme |
| `--currency '€'` | Prefix monetary labels |
| `--out output.png` | Write an image instead of opening a window |

## Output

A text summary in the terminal (totals by source, net) + a matplotlib chart (window or PNG depending
on `--out`).

## Known limitations / ideas

- It does not yet retrieve data directly from worldaces.io (requires handling authentication) — for
  now, you need to export the JSON manually.
