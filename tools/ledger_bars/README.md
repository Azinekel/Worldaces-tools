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

# or fetch directly from the WorldAces API (pages through it automatically)
python ledger_bars.py --token YOUR_BEARER_TOKEN --out ledger.png

# fetch and also save the raw JSON for later reuse (e.g. to paste into the browser page)
python ledger_bars.py --token YOUR_BEARER_TOKEN --outjson transactions.json --out ledger.png
```

The script also works on its own (copy it as-is, with no dependency on the rest of the repo).

### Fetching directly with `--token`

Instead of exporting a JSON file by hand, pass `--token` with a WorldAces API bearer token and the
script pages through `https://api.worldaces.site/team/manage/transactions?page=&limit=100` itself
(100 items per page) until it has every transaction, using stdlib `urllib` only (no extra dependency).
Requests are sent with a regular browser `User-Agent`, since the API's WAF rejects the default
`Python-urllib/…` one with a 403 regardless of the token. `--input` and `--token` are mutually
exclusive; give one or the other. Use `--api-url` to point at a different endpoint if needed, and
`--outjson path.json` to save the fetched transactions to disk (the browser version can't fetch
itself — see below — so this is how you feed it real data).

## Input format

JSON (list of records, or an object with a `transactions`/`data`/`records` key) or CSV. Columns are
auto-detected:

- **amount** : `amount`, `value`, `total`, `sum`, `cost`
- **source/category** : `sourcetype`, `source`, `category`, `reason`, `description`, `label`
- **type** (income/expense, optional) : `type`, `direction`, `kind`, `flow` — if absent, the sign of
  the amount determines the direction (negative = expense)

See [`example_input.json`](./example_input.json) for a minimal example.

Can be generated with this worldaces api point : https://api.worldaces.site/team/manage/transactions?page=&limit=100
(or fetched automatically with `--token`, see below)

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

- The browser page cannot fetch transactions itself: `api.worldaces.site` doesn't send permissive
  CORS headers, so a token-based `fetch()` from a browser tab is blocked outright. The page explains
  this and shows the `--token` CLI command to run instead, then lets you paste the resulting JSON.
  The CLI's `--token` fetch is unaffected (no browser, no CORS).
