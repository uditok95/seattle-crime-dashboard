"""
Preprocess both raw CSVs into a single lean file for deployment.
Keeps only the columns the dashboard needs — output is ~10 MB
instead of the 109 MB + 7.5 MB raw files.

Run once:  python preprocess.py
Output:    processed_data.csv  (commit this to GitHub)
"""
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

ORIG_CSV = r"D:\Foster '27\Q3\IS\SPD_Crime_Data__2008-Present_20260518 (1).csv"
SUPP_CSV = r"D:\Foster '27\Q3\IS\SPD_Crime_Data__2021tillMay.csv"
OUT_CSV  = r"D:\Foster '27\Q3\IS\processed_data.csv"

# Only these columns are used by the dashboard
KEEP = ["Offense ID", "Offense Date", "Offense Category",
        "NIBRS Offense Code Description", "Neighborhood"]

print("Loading and merging...")
orig = pd.read_csv(ORIG_CSV, usecols=KEEP, low_memory=False)
supp = pd.read_csv(SUPP_CSV, usecols=KEEP, low_memory=False)
df   = pd.concat([orig, supp], ignore_index=True)
df   = df.drop_duplicates(subset=["Offense ID"]).drop(columns=["Offense ID"])

print("Parsing dates...")
df["Offense Date"] = pd.to_datetime(df["Offense Date"],
                                     format="%Y %b %d %I:%M:%S %p", errors="coerce")
df = df[df["Offense Date"].dt.year.between(2021, 2025)].copy()

# Expand date columns so the CSV is plain integers (tiny file, fast to load)
df["Year"]      = df["Offense Date"].dt.year.astype("int16")
df["Month"]     = df["Offense Date"].dt.month.astype("int8")
df["DayOfWeek"] = df["Offense Date"].dt.day_name()
df["Hour"]      = df["Offense Date"].dt.hour.astype("int8")
df = df.drop(columns=["Offense Date"])

print(f"Rows: {len(df):,}   Columns: {df.columns.tolist()}")
df.to_csv(OUT_CSV, index=False)

size_mb = __import__("os").path.getsize(OUT_CSV) / 1_048_576
print(f"Saved: {OUT_CSV}  ({size_mb:.1f} MB)")
