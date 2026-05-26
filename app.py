"""
Seattle Property Crime Dashboard — deployment entry point
Reads from processed_data.csv (pre-built from raw SPD CSVs).
Run locally:  python app.py
Deploy:       Render / Railway / any WSGI host
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import os, warnings
warnings.filterwarnings("ignore")

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATA_PATH   = os.path.join(os.path.dirname(__file__), "processed_data.csv")
SEATTLE_POP = 749_000
UDIST_POP   = 49_000

PURPLE  = "#4B2E83"
GOLD    = "#B7A57A"
CREAM   = "#F5F0E8"
WHITE   = "#FFFFFF"
LIGHT_P = "#7B5EA7"

DENSE_HOODS = ["CAPITOL HILL","FIRST HILL","BELLTOWN","SLU/CASCADE",
               "DOWNTOWN COMMERCIAL","PIONEER SQUARE"]
RESID_HOODS = ["QUEEN ANNE","MAGNOLIA","BALLARD SOUTH","BALLARD NORTH",
               "WALLINGFORD","GREENWOOD","FREMONT","MADRONA/LESCHI"]
DAY_ORDER   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
SEASON_MAP  = {12:"Winter",1:"Winter",2:"Winter",3:"Spring",4:"Spring",5:"Spring",
               6:"Summer",7:"Summer",8:"Summer",9:"Fall",10:"Fall",11:"Fall"}

# ── LOAD ──────────────────────────────────────────────────────────────────────
print("Loading processed data...")
df = pd.read_csv(DATA_PATH, low_memory=False)
df["Season"]   = df["Month"].map(SEASON_MAP)
df["AreaType"] = df["Neighborhood"].apply(
    lambda n: "Dense/Urban" if n in DENSE_HOODS else
              "Residential" if n in RESID_HOODS else "Other")

PROP  = df["Offense Category"] == "PROPERTY CRIME"
BURG  = df["NIBRS Offense Code Description"] == "Burglary/Breaking & Entering"
TFMV  = df["NIBRS Offense Code Description"] == "Theft From Motor Vehicle"
UDIST = df["Neighborhood"].str.contains("UNIVERSITY", na=False)
print(f"Ready: {len(df):,} rows | {PROP.sum():,} property crimes | years {df['Year'].min()}-{df['Year'].max()}")

# ── PRE-COMPUTE ───────────────────────────────────────────────────────────────
prop_yr  = df[PROP].groupby("Year").size().reset_index(name="count")
crime_yr = df[PROP].groupby(["Year","NIBRS Offense Code Description"]).size().reset_index(name="count")
nbhd_yr  = df[PROP].groupby(["Year","Neighborhood"]).size().reset_index(name="count")

temp = df[BURG | TFMV].copy()
temp["CrimeType"] = temp["NIBRS Offense Code Description"].map(
    {"Burglary/Breaking & Entering":"Burglary","Theft From Motor Vehicle":"TFMV"})
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
q4_mix = q4.groupby(["AreaType","NIBRS Offense Code Description"]).size().reset_index(name="count")
q4_mix["pct"] = q4_mix.groupby("AreaType")["count"].transform(lambda x: x / x.sum() * 100)
q4_yr  = q4.groupby(["Year","AreaType"]).size().reset_index(name="count")

# ── HELPERS ───────────────────────────────────────────────────────────────────
def uw(fig):
    fig.update_layout(paper_bgcolor=CREAM, plot_bgcolor=CREAM,
                      font=dict(family="Segoe UI, Arial", color="#333"),
                      title_font=dict(color=PURPLE, size=15),
                      legend=dict(bgcolor="rgba(0,0,0,0)"),
                      margin=dict(t=50,b=40,l=50,r=20))
    fig.update_xaxes(gridcolor="#E0DAD0", linecolor="#C0B8A8")
    fig.update_yaxes(gridcolor="#E0DAD0", linecolor="#C0B8A8")
    return fig

def stat_card(value, label, detail):
    return html.Div([
        html.Div(value, style={"fontSize":"2.8rem","fontWeight":"bold","color":GOLD,"lineHeight":"1.1"}),
        html.Hr(style={"borderColor":GOLD,"width":"40px","margin":"8px auto"}),
        html.Div(label, style={"fontWeight":"bold","color":WHITE,"fontSize":"1rem"}),
        html.Div(detail, style={"color":"#DDD","fontSize":"0.8rem","marginTop":"6px"}),
    ], style={"background":PURPLE,"borderRadius":"10px","padding":"24px 18px",
              "textAlign":"center","flex":"1","margin":"8px","minWidth":"180px",
              "boxShadow":"0 4px 12px rgba(0,0,0,.15)"})

def q_header(num, title, sub):
    return html.Div([
        html.Span(str(num), style={"background":GOLD,"color":PURPLE,"borderRadius":"50%",
                                   "width":"36px","height":"36px","display":"flex",
                                   "alignItems":"center","justifyContent":"center",
                                   "fontWeight":"bold","fontSize":"1.2rem","flexShrink":"0"}),
        html.Div([
            html.H2(title, style={"margin":"0","color":WHITE,"fontSize":"1.2rem"}),
            html.P(sub,    style={"margin":"0","color":GOLD,"fontSize":"0.85rem"}),
        ])
    ], style={"background":PURPLE,"padding":"10px 20px","borderRadius":"8px",
              "marginBottom":"20px","display":"flex","alignItems":"center","gap":"16px"})

sec = {"background":WHITE,"borderRadius":"12px","padding":"28px",
       "marginBottom":"32px","boxShadow":"0 2px 8px rgba(0,0,0,.07)"}

# ── APP & LAYOUT ──────────────────────────────────────────────────────────────
app = Dash(__name__, title="Seattle Property Crime Dashboard")
server = app.server  # expose Flask server for Gunicorn / Render

app.layout = html.Div(style={"background":"#F0EAE0","minHeight":"100vh",
                              "fontFamily":"Segoe UI, Arial"}, children=[
    html.Div([
        html.Div(style={"width":"6px","background":GOLD,"borderRadius":"3px",
                        "marginRight":"18px","alignSelf":"stretch"}),
        html.Div([
            html.H1("Seattle Property Crime Analysis",
                    style={"color":WHITE,"margin":"0","fontSize":"1.9rem"}),
            html.P("SPD Crime Data 2021-2025  |  441,709 Records  |  4 Guiding Questions",
                   style={"color":GOLD,"margin":"4px 0 0","fontSize":"0.9rem"}),
        ])
    ], style={"background":PURPLE,"padding":"22px 32px","display":"flex",
              "alignItems":"center","marginBottom":"28px"}),

    html.Div(style={"maxWidth":"1300px","margin":"0 auto","padding":"0 24px"}, children=[

        # Q1
        html.Div(style=sec, children=[
            q_header(1,"Property-Related Crimes",
                     "Has residential crime in Seattle shifted over the past five years?"),
            html.Div([
                stat_card("-18.7%","Decline from Peak (2022->2025)","45,026 -> 36,596  |  Full 2021: 42,899"),
                stat_card("2022","Peak Crime Year","45,026 property crimes"),
                stat_card("21.3%","Share is Burglary","Leading property crime 2021-2025"),
            ], style={"display":"flex","flexWrap":"wrap","marginBottom":"20px"}),
            html.Div([
                html.Div([dcc.Graph(figure=uw(go.Figure(go.Scatter(
                    x=prop_yr["Year"].tolist(), y=prop_yr["count"].tolist(),
                    mode="lines+markers", line=dict(color=PURPLE,width=3), marker=dict(size=10)
                )).update_layout(title="Property Crimes per Year",
                                 xaxis=dict(title="Year",tickmode="linear",tick0=2021,dtick=1),
                                 yaxis_title="Incidents")))],
                    style={"flex":"1.2","minWidth":"340px"}),
                html.Div([
                    dcc.Dropdown(id="q1-yr", clearable=False,
                        options=[{"label":str(y),"value":y} for y in range(2021,2026)],
                        value=2025, style={"marginBottom":"8px","width":"120px"}),
                    dcc.Graph(id="q1-type-bar"),
                ], style={"flex":"1","minWidth":"320px"}),
            ], style={"display":"flex","flexWrap":"wrap","gap":"16px"}),
            dcc.Graph(id="q1-heatmap"),
            dcc.Slider(id="q1-n", min=5, max=20, step=5, value=10,
                       marks={i:str(i) for i in [5,10,15,20]},
                       tooltip={"placement":"bottom"}),
            html.P("Top N neighborhoods",style={"textAlign":"center","color":"#888","fontSize":"0.8rem"}),
        ]),

        # Q2
        html.Div(style=sec, children=[
            q_header(2,"Temporal Fingerprint of Crime",
                     "Hour-of-day, day-of-week, and seasonal patterns: Burglary vs TFMV"),
            html.Div([
                stat_card("63.5%","Burglaries at Night","Peak midnight (5,422 incidents)"),
                stat_card("62.1%","TFMV after 6 PM","Evening/overnight hours dominate"),
                stat_card("Fall","Peak Season — Both","Sep-Nov highest; Spring lowest"),
            ], style={"display":"flex","flexWrap":"wrap","marginBottom":"20px"}),
            html.Div([
                html.Div([dcc.Graph(figure=uw(px.line(hour_df,x="Hour",y="count",color="CrimeType",
                    markers=True,title="By Hour of Day",
                    color_discrete_map={"Burglary":PURPLE,"TFMV":GOLD})
                    .update_layout(xaxis=dict(title="Hour (24h)",tickmode="linear",tick0=0,dtick=2),
                                   yaxis_title="Incidents")))], style={"flex":"1","minWidth":"340px"}),
                html.Div([dcc.Graph(figure=uw(px.bar(
                    dow_df[dow_df["DayOfWeek"].isin(DAY_ORDER)],
                    x="DayOfWeek",y="count",color="CrimeType",barmode="group",
                    title="By Day of Week",category_orders={"DayOfWeek":DAY_ORDER},
                    color_discrete_map={"Burglary":PURPLE,"TFMV":GOLD})
                    .update_layout(xaxis_title="",yaxis_title="Incidents")))],
                    style={"flex":"1","minWidth":"340px"}),
            ], style={"display":"flex","flexWrap":"wrap","gap":"16px"}),
            html.Div([
                html.Div([dcc.Graph(figure=uw(px.bar(month_df,x="Month",y="count",color="CrimeType",
                    barmode="group",title="By Month",
                    color_discrete_map={"Burglary":PURPLE,"TFMV":GOLD})
                    .update_layout(xaxis=dict(title="Month (1=Jan)",tickmode="linear",tick0=1,dtick=1),
                                   yaxis_title="Incidents")))], style={"flex":"1","minWidth":"340px"}),
                html.Div([dcc.Graph(figure=uw(px.bar(season_df,x="Season",y="count",color="CrimeType",
                    barmode="group",title="By Season",
                    color_discrete_map={"Burglary":PURPLE,"TFMV":GOLD},
                    category_orders={"Season":["Spring","Summer","Fall","Winter"]})
                    .update_layout(yaxis_title="Incidents")))], style={"flex":"1","minWidth":"340px"}),
            ], style={"display":"flex","flexWrap":"wrap","gap":"16px","marginTop":"16px"}),
        ]),

        # Q3
        html.Div(style=sec, children=[
            q_header(3,"U-District / UW-Adjacent Focus",
                     "Per-capita property crime in the U-District vs city-wide Seattle averages"),
            html.Div([
                stat_card("4,097","U-District per 100k","Annual rate (2022-2024 avg)"),
                stat_card("5,666","City-wide per 100k","Seattle baseline (2022-2024 avg)"),
                stat_card("4.7%","U-District City Share","Below per-capita average"),
            ], style={"display":"flex","flexWrap":"wrap","marginBottom":"20px"}),
            html.Div([
                html.Div([dcc.Graph(figure=uw(go.Figure([
                    go.Bar(name="U-District",x=q3["Year"].tolist(),y=q3["ud_per100k"].tolist(),marker_color=PURPLE),
                    go.Bar(name="City-wide", x=q3["Year"].tolist(),y=q3["city_per100k"].tolist(),marker_color=GOLD),
                ]).update_layout(barmode="group",title="Rate per 100k Residents",
                                 xaxis=dict(title="Year",tickmode="linear",tick0=2021,dtick=1),
                                 yaxis_title="Incidents per 100k")))],
                    style={"flex":"1","minWidth":"340px"}),
                html.Div([dcc.Graph(figure=uw(go.Figure(go.Bar(
                    x=ud_mix["count"].tolist(), y=ud_mix["crime"].tolist(),
                    orientation="h", marker_color=PURPLE
                )).update_layout(title="U-District Top Crime Types",
                                 yaxis={"categoryorder":"total ascending"},
                                 xaxis_title="Incidents 2021-2025",yaxis_title="")))],
                    style={"flex":"1","minWidth":"340px"}),
            ], style={"display":"flex","flexWrap":"wrap","gap":"16px"}),

            dcc.Graph(figure=uw(go.Figure([
                go.Scatter(
                    name="U-District",
                    x=q3["Year"].tolist(), y=q3["ud_count"].tolist(),
                    mode="lines+markers",
                    line=dict(color=PURPLE, width=3), marker=dict(size=9),
                ),
                go.Scatter(
                    name="City / 20",
                    x=q3["Year"].tolist(),
                    y=(q3["city_count"] / 20).round(0).tolist(),
                    mode="lines+markers",
                    line=dict(color=GOLD, width=2, dash="dash"), marker=dict(size=7),
                    hovertemplate="City/20: %{y}<extra></extra>",
                ),
            ]).update_layout(
                title="U-District vs City Trend (city scaled /20 for readability)",
                yaxis_title="Incidents",
                xaxis=dict(title="Year", tickmode="linear", tick0=2021, dtick=1),
            ))),
        ]),

        # Q4
        html.Div(style=sec, children=[
            q_header(4,"Residential versus Apartment Living",
                     "Do different housing types experience different crime patterns?"),
            html.Div([
                stat_card("25.3% vs 23.2%","Burglary: Urban > Residential","Dense areas have higher break-in share"),
                stat_card("16.0% vs 11.4%","Motor Vehicle Theft: Residential","Parked cars face higher MVT share"),
                stat_card("9.8% vs 6.5%","Shoplifting: Urban-only","Commercial corridors drive retail theft"),
            ], style={"display":"flex","flexWrap":"wrap","marginBottom":"20px"}),
            html.Div([
                html.Div([dcc.Graph(figure=uw(px.bar(
                    q4_mix[q4_mix["count"]>150].sort_values("count",ascending=False),
                    x="pct",y="NIBRS Offense Code Description",color="AreaType",
                    barmode="group",title="Crime Type Mix (%)",orientation="h",
                    color_discrete_map={"Dense/Urban":PURPLE,"Residential":GOLD})
                    .update_layout(yaxis={"categoryorder":"total ascending"},
                                   xaxis_title="% of property crime in area type",yaxis_title="")))],
                    style={"flex":"2","minWidth":"420px"}),
                html.Div([dcc.Graph(figure=uw(px.line(q4_yr,x="Year",y="count",color="AreaType",
                    markers=True,title="Trend by Area Type",
                    color_discrete_map={"Dense/Urban":PURPLE,"Residential":GOLD})
                    .update_layout(xaxis=dict(title="Year",tickmode="linear",tick0=2021,dtick=1),
                                   yaxis_title="Incidents")))],
                    style={"flex":"1","minWidth":"300px"}),
            ], style={"display":"flex","flexWrap":"wrap","gap":"16px"}),
        ]),
    ]),

    html.Div("Seattle Police Department Crime Data 2021-2025  |  Built with Plotly Dash",
             style={"textAlign":"center","color":"#999","padding":"20px","fontSize":"0.8rem"}),
])

# ── CALLBACKS ─────────────────────────────────────────────────────────────────
@app.callback(Output("q1-type-bar","figure"), Input("q1-yr","value"))
def update_type_bar(year):
    d = crime_yr[crime_yr["Year"]==year].nlargest(8,"count").sort_values("count")
    fig = go.Figure(go.Bar(x=d["count"].tolist(),
                           y=d["NIBRS Offense Code Description"].tolist(),
                           orientation="h", marker_color=PURPLE))
    fig.update_layout(title=f"Property Crime Types — {year}",
                      yaxis={"categoryorder":"total ascending"},
                      yaxis_title="", xaxis_title="Incidents")
    return uw(fig)

@app.callback(Output("q1-heatmap","figure"), Input("q1-n","value"))
def update_heatmap(n):
    top_n = nbhd_yr.groupby("Neighborhood")["count"].sum().nlargest(n).index.tolist()
    d = nbhd_yr[nbhd_yr["Neighborhood"].isin(top_n)]
    pivot = d.pivot(index="Neighborhood", columns="Year", values="count").fillna(0)
    fig = go.Figure(go.Heatmap(
        z=pivot.values.tolist(),
        x=[str(c) for c in pivot.columns.tolist()],
        y=pivot.index.tolist(),
        colorscale=[[0,CREAM],[0.5,LIGHT_P],[1,PURPLE]],
        text=pivot.values.astype(int).tolist(), texttemplate="%{text}",
        hovertemplate="Neighborhood: %{y}<br>Year: %{x}<br>Crimes: %{z}<extra></extra>",
    ))
    fig.update_layout(title=f"Top {n} Neighborhoods — Property Crimes Heatmap",
                      paper_bgcolor=CREAM, plot_bgcolor=CREAM,
                      font=dict(family="Segoe UI, Arial"),
                      margin=dict(t=50,b=40,l=180,r=20))
    return fig

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, host="0.0.0.0", port=port)
