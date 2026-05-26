# Seattle Property Crime Analysis Dashboard

Interactive Plotly Dash dashboard analyzing SPD crime data 2021-2025 across 4 guiding questions.

## Live Dashboard
> Deployed on Render: https://seattle-crime-dashboard.onrender.com/ 

## Guiding Questions
1. **Property-related crimes** — Has residential crime shifted over 5 years?
2. **Temporal fingerprint** — Hour-of-day, day-of-week, seasonal patterns: Burglary vs TFMV
3. **U-District focus** — Per-capita crime vs city-wide Seattle
4. **Residential vs Apartment** — Do housing types experience different crime patterns?

## Key Findings
| Q | Stat | Value |
|---|------|-------|
| Q1 | Decline from peak (2022→2025) | **-18.7%** |
| Q1 | Peak crime year | **2022** (45,026 incidents) |
| Q2 | Burglaries occurring at night | **63.5%** |
| Q2 | TFMV occurring after 6 PM | **62.1%** |
| Q3 | U-District rate per 100k | **4,097** vs 5,666 city-wide |
| Q4 | Shoplifting share — dense/urban | **9.8%** vs 6.5% residential |

## Run Locally

```bash
# 1. Clone
git clone https://github.com/uditok95/seattle-crime-dashboard.git
cd seattle-crime-dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python app.py
# Open http://127.0.0.1:8050
```

> `processed_data.csv` is included — no need to download the raw CSVs.

## Files
| File | Purpose |
|------|---------|
| `app.py` | Main Dash app (reads `processed_data.csv`) |
| `processed_data.csv` | Pre-processed dataset (412k rows, 28 MB) |
| `spd_analysis.py` | Full analysis script (requires raw CSVs) |
| `spd_analysis.sql` | DuckDB SQL queries for all 4 questions |
| `export_html.py` | Generate standalone shareable HTML |
| `Seattle_Crime_Dashboard.html` | Static shareable dashboard |
| `preprocess.py` | Rebuild `processed_data.csv` from raw CSVs |

## Data Source
Seattle Police Department Open Data  
[data.seattle.gov — SPD Crime Data 2008-Present](https://data.seattle.gov/Public-Safety/SPD-Crime-Data-2008-Present/tazs-3rd5)

