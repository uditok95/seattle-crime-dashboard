"""
Export all dashboard charts to a single shareable HTML file.
No server needed — recipient opens in any browser.
Run:  python export_html.py
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import warnings
warnings.filterwarnings("ignore")

ORIG_CSV    = r"D:\Foster '27\Q3\IS\SPD_Crime_Data__2008-Present_20260518 (1).csv"
SUPP_CSV    = r"D:\Foster '27\Q3\IS\SPD_Crime_Data__2021tillMay.csv"
OUTPUT_HTML = r"D:\Foster '27\Q3\IS\Seattle_Crime_Dashboard.html"
SEATTLE_POP = 749_000
UDIST_POP   = 49_000

PURPLE  = "#4B2E83"
GOLD    = "#B7A57A"
CREAM   = "#F5F0E8"
LIGHT_P = "#7B5EA7"

DENSE_HOODS = ["CAPITOL HILL","FIRST HILL","BELLTOWN","SLU/CASCADE",
               "DOWNTOWN COMMERCIAL","PIONEER SQUARE"]
RESID_HOODS = ["QUEEN ANNE","MAGNOLIA","BALLARD SOUTH","BALLARD NORTH",
               "WALLINGFORD","GREENWOOD","FREMONT","MADRONA/LESCHI"]
DAY_ORDER   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# ── LOAD, MERGE & CLEAN ───────────────────────────────────────────────────────
print("Loading and merging CSVs...")
orig = pd.read_csv(ORIG_CSV, low_memory=False)
supp = pd.read_csv(SUPP_CSV, low_memory=False)
df   = pd.concat([orig, supp], ignore_index=True)
df   = df.drop_duplicates(subset=["Offense ID"], keep="first")

df["Offense Date"] = pd.to_datetime(df["Offense Date"],
                                     format="%Y %b %d %I:%M:%S %p", errors="coerce")
df = df[df["Offense Date"].dt.year.between(2021, 2025)].copy()
df["Year"]      = df["Offense Date"].dt.year
df["Month"]     = df["Offense Date"].dt.month
df["DayOfWeek"] = df["Offense Date"].dt.day_name()
df["Hour"]      = df["Offense Date"].dt.hour
df["Season"]    = df["Month"].map({
    12:"Winter",1:"Winter",2:"Winter",
    3:"Spring", 4:"Spring", 5:"Spring",
    6:"Summer", 7:"Summer", 8:"Summer",
    9:"Fall",  10:"Fall",  11:"Fall"})
df["AreaType"] = df["Neighborhood"].apply(
    lambda n: "Dense/Urban" if n in DENSE_HOODS else
              "Residential" if n in RESID_HOODS else "Other")

PROP  = df["Offense Category"] == "PROPERTY CRIME"
BURG  = df["NIBRS Offense Code Description"] == "Burglary/Breaking & Entering"
TFMV  = df["NIBRS Offense Code Description"] == "Theft From Motor Vehicle"
UDIST = df["Neighborhood"].str.contains("UNIVERSITY", na=False)
print(f"Ready: {len(df):,} rows, {PROP.sum():,} property crimes.")

# ── PRE-COMPUTE ───────────────────────────────────────────────────────────────
prop_yr  = df[PROP].groupby("Year").size().reset_index(name="count")
crime_yr = (df[PROP].groupby(["Year","NIBRS Offense Code Description"])
            .size().reset_index(name="count"))
nbhd_yr  = (df[PROP].groupby(["Year","Neighborhood"])
            .size().reset_index(name="count"))

temp = df[BURG | TFMV].copy()
temp["CrimeType"] = temp["NIBRS Offense Code Description"].map({
    "Burglary/Breaking & Entering":"Burglary",
    "Theft From Motor Vehicle":"TFMV"})
hour_df   = temp.groupby(["Hour","CrimeType"]).size().reset_index(name="count")
dow_df    = temp.groupby(["DayOfWeek","CrimeType"]).size().reset_index(name="count")
month_df  = temp.groupby(["Month","CrimeType"]).size().reset_index(name="count")
season_df = temp.groupby(["Season","CrimeType"]).size().reset_index(name="count")

ud_yr    = df[PROP & UDIST].groupby("Year").size().reset_index(name="ud_count")
city_yr2 = df[PROP].groupby("Year").size().reset_index(name="city_count")
q3 = ud_yr.merge(city_yr2, on="Year")
q3["ud_per100k"]   = (q3["ud_count"]   / UDIST_POP   * 100_000).round(0)
q3["city_per100k"] = (q3["city_count"] / SEATTLE_POP * 100_000).round(0)
ud_mix = (df[PROP & UDIST]["NIBRS Offense Code Description"]
          .value_counts().head(6).reset_index()
          .rename(columns={"NIBRS Offense Code Description":"crime"}))

q4 = df[PROP & df["AreaType"].isin(["Dense/Urban","Residential"])].copy()
q4_mix = (q4.groupby(["AreaType","NIBRS Offense Code Description"])
          .size().reset_index(name="count"))
q4_mix["pct"] = q4_mix.groupby("AreaType")["count"].transform(
    lambda x: x / x.sum() * 100)
q4_yr = q4.groupby(["Year","AreaType"]).size().reset_index(name="count")

top10  = nbhd_yr.groupby("Neighborhood")["count"].sum().nlargest(10).index.tolist()
heat_d = nbhd_yr[nbhd_yr["Neighborhood"].isin(top10)]
pivot  = heat_d.pivot(index="Neighborhood", columns="Year", values="count").fillna(0)

# ── UW THEME HELPER ───────────────────────────────────────────────────────────
def uw(fig):
    fig.update_layout(paper_bgcolor=CREAM, plot_bgcolor=CREAM,
                      font=dict(family="Segoe UI, Arial", color="#333"),
                      title_font=dict(color=PURPLE, size=14),
                      legend=dict(bgcolor="rgba(0,0,0,0)"),
                      margin=dict(t=50,b=40,l=50,r=20))
    fig.update_xaxes(gridcolor="#E0DAD0", linecolor="#C0B8A8")
    fig.update_yaxes(gridcolor="#E0DAD0", linecolor="#C0B8A8")
    return fig

# ── BUILD CHARTS (use plain lists to guarantee JSON — not binary — encoding) --
print("Building charts...")

def to_lists(dframe, *cols):
    """Convert specified columns to plain Python lists for Plotly JSON encoding."""
    return {c: dframe[c].tolist() for c in cols}

charts = {}

# Q1
d = to_lists(prop_yr, "Year", "count")
charts["q1_trend"] = uw(go.Figure(go.Scatter(
    x=d["Year"], y=d["count"], mode="lines+markers",
    line=dict(color=PURPLE, width=3), marker=dict(size=10, color=PURPLE)
)).update_layout(title="Q1 | Property Crimes per Year (2021-2025)",
                 xaxis=dict(title="Year", tickmode="linear", tick0=2021, dtick=1),
                 yaxis_title="Incidents"))

type_2025 = crime_yr[crime_yr["Year"]==2025].nlargest(8,"count").sort_values("count")
d2 = to_lists(type_2025, "count", "NIBRS Offense Code Description")
charts["q1_types"] = uw(go.Figure(go.Bar(
    x=d2["count"], y=d2["NIBRS Offense Code Description"],
    orientation="h", marker_color=PURPLE
)).update_layout(title="Q1 | Property Crime Types — 2025",
                 yaxis={"categoryorder":"total ascending"},
                 xaxis_title="Incidents", yaxis_title=""))

charts["q1_heatmap"] = go.Figure(go.Heatmap(
    z=pivot.values.tolist(),
    x=[str(c) for c in pivot.columns.tolist()],
    y=pivot.index.tolist(),
    colorscale=[[0,CREAM],[0.5,LIGHT_P],[1,PURPLE]],
    text=pivot.values.astype(int).tolist(), texttemplate="%{text}",
    hovertemplate="Neighborhood: %{y}<br>Year: %{x}<br>Crimes: %{z}<extra></extra>"
))
charts["q1_heatmap"].update_layout(
    title="Q1 | Top 10 Neighborhoods — Property Crime Heatmap",
    paper_bgcolor=CREAM, plot_bgcolor=CREAM,
    font=dict(family="Segoe UI, Arial"), margin=dict(t=50,b=40,l=180,r=20))

# Q2
CMAP = {"Burglary": PURPLE, "TFMV": GOLD}
for name, src in [("q2_hour",hour_df),("q2_month",month_df)]:
    traces, axis = [], ("Hour" if "hour" in name else "Month")
    for ct, color in CMAP.items():
        sub = src[src["CrimeType"]==ct].sort_values(axis)
        d = to_lists(sub, axis, "count")
        traces.append(go.Bar(name=ct, x=d[axis], y=d["count"], marker_color=color))
    charts[name] = uw(go.Figure(traces).update_layout(
        barmode="group",
        title=f"Q2 | Incidents by {'Hour of Day' if 'hour' in name else 'Month'}",
        xaxis=dict(title="Hour (24h)" if "hour" in name else "Month (1=Jan)",
                   tickmode="linear", tick0=0, dtick=1),
        yaxis_title="Incidents"))

for ct, color in CMAP.items():
    pass  # dow and season use categorical x — build separately

dow_traces = []
for ct, color in CMAP.items():
    sub = dow_df[dow_df["CrimeType"]==ct]
    sub = sub[sub["DayOfWeek"].isin(DAY_ORDER)].set_index("DayOfWeek").reindex(DAY_ORDER).reset_index()
    dow_traces.append(go.Bar(name=ct, x=sub["DayOfWeek"].tolist(),
                             y=sub["count"].tolist(), marker_color=color))
charts["q2_dow"] = uw(go.Figure(dow_traces).update_layout(
    barmode="group", title="Q2 | Incidents by Day of Week",
    xaxis_title="", yaxis_title="Incidents"))

sea_order = ["Spring","Summer","Fall","Winter"]
sea_traces = []
for ct, color in CMAP.items():
    sub = season_df[season_df["CrimeType"]==ct].set_index("Season").reindex(sea_order).reset_index()
    sea_traces.append(go.Bar(name=ct, x=sub["Season"].tolist(),
                             y=sub["count"].tolist(), marker_color=color))
charts["q2_season"] = uw(go.Figure(sea_traces).update_layout(
    barmode="group", title="Q2 | Incidents by Season",
    xaxis_title="", yaxis_title="Incidents"))

# Q3
yrs = q3["Year"].tolist()
charts["q3_rate"] = uw(go.Figure([
    go.Bar(name="U-District",x=yrs,y=q3["ud_per100k"].tolist(),  marker_color=PURPLE),
    go.Bar(name="City-wide", x=yrs,y=q3["city_per100k"].tolist(),marker_color=GOLD),
]).update_layout(barmode="group",
    title="Q3 | Property Crime Rate per 100k Residents",
    xaxis=dict(title="Year",tickmode="linear",tick0=2021,dtick=1),
    yaxis_title="Incidents per 100k"))

d_ud = to_lists(ud_mix, "count", "crime")
charts["q3_udmix"] = uw(go.Figure(go.Bar(
    x=d_ud["count"], y=d_ud["crime"], orientation="h", marker_color=PURPLE
)).update_layout(title="Q3 | U-District Top 6 Property Crime Types",
                 yaxis={"categoryorder":"total ascending"},
                 xaxis_title="Incidents 2021-2025", yaxis_title=""))

# Q4
q4_fil = q4_mix[q4_mix["count"]>150].copy()
area_types = q4_fil["AreaType"].unique().tolist()
q4_traces = []
for at, color in [("Dense/Urban",PURPLE),("Residential",GOLD)]:
    sub = q4_fil[q4_fil["AreaType"]==at].sort_values("count")
    q4_traces.append(go.Bar(name=at, x=sub["pct"].tolist(),
                            y=sub["NIBRS Offense Code Description"].tolist(),
                            orientation="h", marker_color=color))
charts["q4_mix"] = uw(go.Figure(q4_traces).update_layout(
    barmode="group",
    title="Q4 | Crime Type Mix: Dense/Urban vs Residential (%)",
    xaxis_title="% of property crime in area type", yaxis_title=""))

q4_traces2 = []
for at, color in [("Dense/Urban",PURPLE),("Residential",GOLD)]:
    sub = q4_yr[q4_yr["AreaType"]==at].sort_values("Year")
    q4_traces2.append(go.Scatter(name=at, x=sub["Year"].tolist(), y=sub["count"].tolist(),
                                 mode="lines+markers", line_color=color, line_width=2,
                                 marker_size=8))
charts["q4_trend"] = uw(go.Figure(q4_traces2).update_layout(
    title="Q4 | Property Crime Trend by Area Type",
    xaxis=dict(title="Year",tickmode="linear",tick0=2021,dtick=1),
    yaxis_title="Incidents"))

# ── ASSEMBLE HTML ─────────────────────────────────────────────────────────────
print("Writing HTML...")

def stat_html(val, label, detail):
    return f"""<div style="background:#4B2E83;border-radius:10px;padding:20px 16px;
                text-align:center;flex:1;margin:6px;min-width:160px;">
      <div style="font-size:2.4rem;font-weight:bold;color:#B7A57A;line-height:1.1">{val}</div>
      <hr style="border-color:#B7A57A;width:36px;margin:8px auto"/>
      <div style="font-weight:bold;color:#fff;font-size:0.95rem">{label}</div>
      <div style="color:#ccc;font-size:0.78rem;margin-top:5px">{detail}</div>
    </div>"""

def q_header(num, title, sub):
    return f"""<div style="background:#4B2E83;color:#fff;padding:10px 18px;border-radius:8px;
                margin-bottom:18px;display:flex;align-items:center;gap:14px">
      <span style="background:#B7A57A;color:#4B2E83;border-radius:50%;width:34px;height:34px;
                   display:flex;align-items:center;justify-content:center;font-weight:bold;
                   font-size:1.1rem;flex-shrink:0">{num}</span>
      <div>
        <div style="font-size:1.1rem;font-weight:bold">{title}</div>
        <div style="font-size:0.82rem;color:#B7A57A">{sub}</div>
      </div></div>"""

# First chart uses include_plotlyjs='cdn' to inject Plotly 3.x correctly
# All others use False (Plotly already loaded)
FIRST = True
def chart_html(fig):
    global FIRST
    mode = "cdn" if FIRST else False
    FIRST = False
    return fig.to_html(full_html=False, include_plotlyjs=mode)

parts = ["""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Seattle Property Crime Dashboard</title>
<style>
* { box-sizing:border-box; }
body { font-family:'Segoe UI',Arial,sans-serif; background:#F0EAE0; margin:0; color:#333; }
.sec  { background:#fff; border-radius:12px; padding:26px; margin-bottom:28px;
        box-shadow:0 2px 8px rgba(0,0,0,.07); }
.row  { display:flex; flex-wrap:wrap; gap:14px; }
.col  { flex:1; min-width:300px; }
.stats{ display:flex; flex-wrap:wrap; margin-bottom:18px; }
</style></head><body>
<div style="background:#4B2E83;padding:20px 30px;display:flex;align-items:center;gap:16px;margin-bottom:24px">
  <div style="width:5px;background:#B7A57A;border-radius:3px;align-self:stretch"></div>
  <div>
    <h1 style="color:#fff;margin:0;font-size:1.8rem">Seattle Property Crime Analysis</h1>
    <p style="color:#B7A57A;margin:4px 0 0;font-size:0.88rem">
      SPD Crime Data 2021-2025 &nbsp;|&nbsp; 441,709 Records (full 2021 merged) &nbsp;|&nbsp; 4 Guiding Questions
    </p>
  </div>
</div>
<div style="max-width:1280px;margin:0 auto;padding:0 22px">
"""]

def section(header, stats, body):
    parts.append(f'<div class="sec">{header}<div class="stats">{stats}</div>{body}</div>')

# Q1
section(
    q_header("1","Property-Related Crimes",
             "Has residential crime in Seattle shifted over the past five years?"),
    (stat_html("-18.7%","Decline from Peak (2022->2025)","Crime fell from 45,026 to 36,596. Full 2021: 42,899") +
     stat_html("2022","Peak Crime Year","45,026 property crimes - highest in 5-year window") +
     stat_html("21.3%","Share is Burglary","Leading property crime type across 2021-2025")),
    f"""<div class="row">
      <div class="col">{chart_html(charts["q1_trend"])}</div>
      <div class="col">{chart_html(charts["q1_types"])}</div>
    </div>
    <div style="margin-top:14px">{chart_html(charts["q1_heatmap"])}</div>"""
)

# Q2
section(
    q_header("2","Temporal Fingerprint of Crime",
             "Hour-of-day, day-of-week, and seasonal patterns: Burglary vs TFMV"),
    (stat_html("63.5%","Burglaries at Night","Peak at midnight (5,422 incidents). Daytime only 36.5%.") +
     stat_html("62.1%","TFMV after 6 PM","Evening/overnight hours dominate vehicle theft") +
     stat_html("Fall","Peak Season - Both","Sep-Nov highest; Spring lowest for both types")),
    f"""<div class="row">
      <div class="col">{chart_html(charts["q2_hour"])}</div>
      <div class="col">{chart_html(charts["q2_dow"])}</div>
    </div>
    <div class="row" style="margin-top:14px">
      <div class="col">{chart_html(charts["q2_month"])}</div>
      <div class="col">{chart_html(charts["q2_season"])}</div>
    </div>"""
)

# Q3
section(
    q_header("3","U-District / UW-Adjacent Focus",
             "Per-capita property crime in the U-District vs city-wide Seattle"),
    (stat_html("4,097","U-District per 100k","Annual rate (2022-2024 avg)") +
     stat_html("5,666","City-wide per 100k","Seattle baseline rate (2022-2024 avg)") +
     stat_html("4.7%","U-District City Share","Despite ~6.5% of population - below city avg")),
    f"""<div class="row">
      <div class="col">{chart_html(charts["q3_rate"])}</div>
      <div class="col">{chart_html(charts["q3_udmix"])}</div>
    </div>"""
)

# Q4
section(
    q_header("4","Residential versus Apartment Living",
             "Do different housing types experience different crime patterns?"),
    (stat_html("25.3% vs 23.2%","Burglary: Urban > Residential","Dense neighborhoods carry a higher break-in share") +
     stat_html("16.0% vs 11.4%","Motor Vehicle Theft: Residential","Parked cars on streets face higher MVT share") +
     stat_html("9.8% vs 6.5%","Shoplifting: Urban-only","Commercial corridors drive retail theft")),
    f"""<div class="row">
      <div style="flex:2;min-width:380px">{chart_html(charts["q4_mix"])}</div>
      <div class="col">{chart_html(charts["q4_trend"])}</div>
    </div>"""
)

parts.append("""</div>
<div style="text-align:center;color:#999;padding:20px;font-size:0.78rem">
  Seattle Police Department Crime Data 2021-2025 &nbsp;|&nbsp; Built with Plotly
</div></body></html>""")

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write("\n".join(parts))

print(f"Done! Open in any browser:\n  {OUTPUT_HTML}")
