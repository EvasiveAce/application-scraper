import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output
import plotly.express as px

def load_latest_csv():
    csv_files = [f for f in os.listdir('.') if f.startswith('jobs_') and f.endswith('.csv')]
    if not csv_files:
        raise FileNotFoundError("No CSV found.")
    latest = sorted(csv_files)[-1]
    return pd.read_csv(latest)

df = load_latest_csv()

app = Dash(__name__)

# --- FIGURES ---
top_companies = df['company'].value_counts().head(20)
fig_companies = px.bar(
    top_companies,
    x=top_companies.values,
    y=top_companies.index,
    orientation="h",
    title="Top Companies"
)

junior_remote = df[(df["junior_explicit"] == True) & (df["is_remote"] == True)]
junior_onsite = df[(df["junior_explicit"] == True) & (df["is_remote"] == False)]
non_junior = df[(df["junior_explicit"] == False)]

non_junior_remote = df[(df["junior_explicit"] == False) & (df["is_remote"] == True)]
non_junior_onsite = df[(df["junior_explicit"] == False) & (df["is_remote"] == False)]

count_remote = len(junior_remote)
count_onsite = len(junior_onsite)
count_remote_ns = len(non_junior_remote)
count_onsite_ns = len(non_junior_onsite)
count_junior_all = count_remote + count_onsite
count_total = len(df)


fig_junior = px.bar(
    x=[count_total, count_onsite_ns, count_remote_ns, count_junior_all, count_onsite, count_remote],
    y=["All", "Non Stated - On Site", "Non Stated - Remote", "Junior - All", "Junior - On Site", "Junior - Remote"],
    orientation="h",
    title="Job Breakdown",
    text_auto=True
)

roles = df['title'].str.split().str[0].value_counts().head(15)
fig_roles = px.bar(
    x=roles.index,
    y=roles.values,
    title="Top Job Role Keywords"
)

# App Layout
app.layout = html.Div([
    html.H1("Job Search Dashboard", style={"textAlign": "center"}),

    # Charts
    html.Div([
        dcc.Graph(id="companies", figure=fig_companies),
        dcc.Graph(id="junior", figure=fig_junior),
        dcc.Graph(id="roles", figure=fig_roles),
    ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr"}),

    html.H2("Filtered Job Links"),
    html.Div(id="results"),
])

# --- CALLBACK ---
@app.callback(
    Output("results", "children"),
    Input("companies", "clickData"),
    Input("junior", "clickData"),
    Input("roles", "clickData"),
)
def filter_jobs(test2, junior_click, test):

    filtered = df.copy()

    # ---- 2. Jr. filter ----
    if junior_click:
        label = junior_click["points"][0]["label"]

        if label == "All":
            filtered = df.copy()

        elif label == "Non Stated - Remote":
            filtered = filtered[
                (filtered["junior_explicit"] == False) &
                (filtered["is_remote"] == True)
            ]

        elif label == "Non Stated - On Site":
            filtered = filtered[
                (filtered["junior_explicit"] == False) &
                (filtered["is_remote"] == False)
            ]

        elif label == "Junior - All":
            filtered = filtered[filtered["junior_explicit"] == True]

        elif label == "Junior - Remote":
            filtered = filtered[
                (filtered["junior_explicit"] == True) &
                (filtered["is_remote"] == True)
            ]

        elif label == "Junior - On Site":
            filtered = filtered[
                (filtered["junior_explicit"] == True) &
                (filtered["is_remote"] == False)
            ]

    if filtered.empty:
        return html.P("No jobs match this filter.")

    # ---- Build clickable job links ----
    return [
        html.Div([
            dcc.Checklist(
                options=[{"label": "", "value": row["url"]}],
                value=[], 
                id={'type': 'job-checkbox', 'index': idx},
                inputStyle={"margin-right": "10px"}
            ),
            html.A(
                f"{row['title']} — {row['company']} - {row['location']}",
                href=row["url"],
                target="_blank",
            )
        ], style={"margin-bottom": "5px", "display": "flex", "alignItems": "center"})
        for idx, row in filtered.iterrows()
    ]

if __name__ == "__main__":
    app.run()