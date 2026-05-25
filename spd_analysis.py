"""
SPD Crime Data Analysis — Full 2021-2025
Merges the main CSV (2021 May onwards by report date) with the
Jan-May 2021 supplement, deduplicates on Offense ID, then answers
all 4 guiding questions.
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

ORIG_CSV  = r"D:\Foster '27\Q3\IS\SPD_Crime_Data__2008-Present_20260518 (1).csv"
SUPP_CSV  = r"D:\Foster '27\Q3\IS\SPD_Crime_Data__2021tillMay.csv"

# ── LOAD & MERGE ──────────────────────────────────────────────────────────────
print("Loading CSVs...")
orig = pd.read_csv(ORIG_CSV, low_memory=False)
supp = pd.read_csv(SUPP_CSV, low_memory=False)
print(f"  Original rows : {len(orig):,}")
print(f"  Supplement rows: {len(supp):,}")

# Concatenate — put supplement first so orig rows win on dedup
df = pd.concat([orig, supp], ignore_index=True)
before = len(df)
df = df.drop_duplicates(subset=["Offense ID"], keep="first")
print(f"  Combined rows  : {before:,}")
print(f"  After dedup    : {len(df):,}  (removed {before - len(df):,} duplicates)")

# ── CLEAN ─────────────────────────────────────────────────────────────────────
df.columns = df.columns.str.strip()
df["Offense Date"] = pd.to_datetime(df["Offense Date"],
                                     format="%Y %b %d %I:%M:%S %p", errors="coerce")
df = df[df["Offense Date"].dt.year.between(2021, 2025)].copy()

df["Year"]      = df["Offense Date"].dt.year
df["Month"]     = df["Offense Date"].dt.month
df["DayOfWeek"] = df["Offense Date"].dt.day_name()
df["Hour"]      = df["Offense Date"].dt.hour
df["Season"]    = df["Month"].map({
    12:"Winter",1:"Winter",2:"Winter",
    3:"Spring",4:"Spring",5:"Spring",
    6:"Summer",7:"Summer",8:"Summer",
    9:"Fall",10:"Fall",11:"Fall"})

PROP  = df["Offense Category"] == "PROPERTY CRIME"
BURG  = df["NIBRS Offense Code Description"] == "Burglary/Breaking & Entering"
TFMV  = df["NIBRS Offense Code Description"] == "Theft From Motor Vehicle"
UDIST = df["Neighborhood"].str.contains("UNIVERSITY", na=False)

print(f"\nRows after filtering 2021-2025 : {len(df):,}")
print(f"  Property crimes : {PROP.sum():,}")
print(f"  Burglaries      : {BURG.sum():,}")
print(f"  TFMV            : {TFMV.sum():,}")

# ── Q1 ────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("Q1 — PROPERTY CRIME TREND (2021–2025, full year)")
print("="*60)

prop_yr = df[PROP].groupby("Year").size()
print("\nProperty crimes per year:")
print(prop_yr.to_string())

y2021 = prop_yr.get(2021, 0)
y2022 = prop_yr.get(2022, 0)
y2025 = prop_yr.get(2025, 0)
pct_21_25 = (y2025 - y2021) / y2021 * 100
pct_22_25 = (y2025 - y2022) / y2022 * 100
print(f"\n2021->2025 change : {pct_21_25:+.1f}%")
print(f"2022->2025 change : {pct_22_25:+.1f}%")
print(f"Peak year         : {prop_yr.idxmax()} ({prop_yr.max():,})")

yoy = prop_yr.pct_change() * 100
print("\nYear-over-year % change:")
print(yoy.dropna().round(1).to_string())

top_type = df[PROP]["NIBRS Offense Code Description"].value_counts()
print(f"\nTop property crime: {top_type.index[0]} ({top_type.iloc[0]/PROP.sum()*100:.1f}%)")

print("\nTop 10 neighborhoods (2025):")
print(df[PROP & (df["Year"]==2025)]["Neighborhood"].value_counts().head(10).to_string())

# ── Q2 ────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("Q2 — TEMPORAL FINGERPRINT")
print("="*60)

burg_hr   = df[BURG].groupby("Hour").size()
tfmv_hr   = df[TFMV].groupby("Hour").size()
burg_day  = df[BURG]["DayOfWeek"].value_counts()
tfmv_day  = df[TFMV]["DayOfWeek"].value_counts()
burg_mo   = df[BURG].groupby("Month").size()
tfmv_mo   = df[TFMV].groupby("Month").size()
burg_sea  = df[BURG]["Season"].value_counts()
tfmv_sea  = df[TFMV]["Season"].value_counts()

burg_night = df[BURG & ~df["Hour"].between(6,17)].shape[0] / BURG.sum() * 100
tfmv_night = df[TFMV & (df["Hour"].lt(6) | df["Hour"].ge(18))].shape[0] / TFMV.sum() * 100

print(f"Burglary night (not 6am-6pm): {burg_night:.1f}%  |  peak hour: {burg_hr.idxmax()}:00")
print(f"TFMV evening/night (6pm+):   {tfmv_night:.1f}%  |  peak hour: {tfmv_hr.idxmax()}:00")
print(f"Burglary peak day: {burg_day.idxmax()}  |  peak season: {burg_sea.idxmax()}")
print(f"TFMV peak day    : {tfmv_day.idxmax()}  |  peak season: {tfmv_sea.idxmax()}")

print("\nBurglary by hour:\n", burg_hr.to_string())
print("\nTFMV by hour:\n", tfmv_hr.to_string())
print("\nBurglary by season:\n", burg_sea.to_string())
print("\nTFMV by season:\n", tfmv_sea.to_string())

# ── Q3 ────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("Q3 — U-DISTRICT vs CITY-WIDE")
print("="*60)

SEATTLE_POP = 749_000
UDIST_POP   = 49_000

ud_yr   = df[PROP & UDIST].groupby("Year").size()
city_yr = df[PROP].groupby("Year").size()

print("\nU-District property crimes per year:"); print(ud_yr.to_string())
print("\nCity-wide property crimes per year:"); print(city_yr.to_string())

mask = [2022, 2023, 2024]
ud_avg   = ud_yr[ud_yr.index.isin(mask)].mean()
city_avg = city_yr[city_yr.index.isin(mask)].mean()
ud_r     = ud_avg   / UDIST_POP   * 100_000
city_r   = city_avg / SEATTLE_POP * 100_000
print(f"\nU-District per 100k  : {ud_r:,.0f}")
print(f"City-wide per 100k   : {city_r:,.0f}")
print(f"Ratio (UD / city)    : {ud_r/city_r:.2f}x")
print(f"U-District city share: {ud_yr[ud_yr.index.isin(mask)].sum() / city_yr[city_yr.index.isin(mask)].sum()*100:.1f}%")

# ── Q4 ────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("Q4 — RESIDENTIAL vs DENSE/URBAN AREA TYPE")
print("="*60)

DENSE = ["CAPITOL HILL","FIRST HILL","BELLTOWN","SLU/CASCADE",
         "DOWNTOWN COMMERCIAL","PIONEER SQUARE"]
RESID = ["QUEEN ANNE","MAGNOLIA","BALLARD SOUTH","BALLARD NORTH",
         "WALLINGFORD","GREENWOOD","FREMONT","MADRONA/LESCHI"]

df["AreaType"] = df["Neighborhood"].apply(
    lambda n: "Dense/Urban" if n in DENSE else
              "Residential" if n in RESID else "Other")

q4 = df[PROP & df["AreaType"].isin(["Dense/Urban","Residential"])].copy()
q4_mix = (q4.groupby(["AreaType","NIBRS Offense Code Description"])
          .size().reset_index(name="count"))
q4_mix["pct"] = q4_mix.groupby("AreaType")["count"].transform(
    lambda x: x / x.sum() * 100).round(1)

print("\nCrime type mix by area type:")
print(q4_mix[q4_mix["count"]>100]
      .sort_values(["AreaType","count"], ascending=[True,False])
      .to_string(index=False))

for at in ["Dense/Urban","Residential"]:
    sub = q4_mix[q4_mix["AreaType"]==at]
    burg_pct = sub[sub["NIBRS Offense Code Description"]=="Burglary/Breaking & Entering"]["pct"].values
    mvt_pct  = sub[sub["NIBRS Offense Code Description"]=="Motor Vehicle Theft"]["pct"].values
    shop_pct = sub[sub["NIBRS Offense Code Description"]=="Shoplifting"]["pct"].values
    print(f"\n{at}: Burglary {burg_pct[0] if len(burg_pct) else 'N/A'}% | "
          f"MVT {mvt_pct[0] if len(mvt_pct) else 'N/A'}% | "
          f"Shoplifting {shop_pct[0] if len(shop_pct) else 'N/A'}%")

print("\nAnalysis complete.")
