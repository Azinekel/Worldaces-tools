# World Aces H2H Statistics

A Jupyter Notebook tool for collecting World Aces match data and viewing Head-to-Head statistics between teams.

The project downloads match data directly from the World Aces API, builds a local match dataset, and lets you browse H2H matches and statistics without repeatedly requesting the API for every opponent.

## Files

* `H2HMatches.ipynb` — main notebook
* `cell1.py` — match data collection
* `cell2.py` — H2H match browser
* `cell3.py` — H2H summary/statistics
* `requirements.txt` — required Python packages

## Requirements

You need:

* Python 3
* Jupyter Notebook or JupyterLab
* A valid World Aces Bearer token

## Installation

Open a terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

You can also install the packages from a notebook with:

```python
%pip install -r requirements.txt
```

## How to run

Open:

```text
H2HMatches.ipynb
```

Run the cells in order.

### Cell 1 — Collect match data

Cell 1 asks for your World Aces Bearer token and then provides the Team ID and date-range controls.

Enter your Team ID, choose the period you want, and click **Fetch Matches**.

The script:

1. Finds the team's matches in the selected period.
2. Downloads the full JSON for each match.
3. Builds the match dataset.
4. Saves the full dataset as `match_statistics.csv`.
5. Displays the first five rows.

The complete dataset remains available in `df` for the following cells.

### Cell 2 — H2H Match Browser

Cell 2 uses the dataset already collected by Cell 1.

Select an opponent, competition, and number of matches to view the H2H match history.

No additional API requests are made by Cell 2.

### Cell 3 — H2H Summary

Cell 3 generates the H2H statistics dashboard, including overall record, match statistics, totals, and competition breakdown.

## Important

You need to run Cell 1 before Cell 2 and Cell 3 because they use the `df` and `TEAM_ID` created by Cell 1.

Do not share your Bearer token or commit it to GitHub.

## Updating an existing dataset

The match dataset can be saved as `match_statistics.csv` and reused for later H2H analysis.

Future versions may add automatic checking for new matches so existing datasets can be updated without downloading the same matches again.

