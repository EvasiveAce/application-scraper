import os
import pandas as pd
from dash import Dash, dcc, html, Input, Output, ctx
import plotly.graph_objects as go
from datetime import datetime, timedelta

def load_latest_csv():
    csv_files = [f for f in os.listdir('.') if f.startswith('jobs_') and f.endswith('.csv')]
    if not csv_files:
        raise FileNotFoundError("No CSV found.")
    latest = sorted(csv_files)[-1]
    df = pd.read_csv(latest)
    # Convert posted_date to datetime
    df['posted_date'] = pd.to_datetime(df['posted_date'], errors='coerce')
    return df

df = load_latest_csv()

app = Dash(__name__)

colors = {
    'background': "#e7e5df",
    'surface': "#d3d0cb",
    'primary': '#44bba4',
    'secondary': '#e7bb41',
    'accent': '#393e41',
    'text': "#393e41",
    'text_secondary': "#5a5f62",
    'border': '#44bba4'
}

def create_breakdown_figure(filtered_df):
    """Create the breakdown figure based on filtered data"""
    junior_remote = filtered_df[(filtered_df["level"] == "Junior") & (filtered_df["is_remote"] == True)]
    junior_onsite = filtered_df[(filtered_df["level"] == "Junior") & (filtered_df["is_remote"] == False)]
    mid_remote = filtered_df[((filtered_df["level"] != "Junior") & (filtered_df["level"] != "Senior")) & (filtered_df["is_remote"] == True)]
    mid_onsite = filtered_df[((filtered_df["level"] != "Junior") & (filtered_df["level"] != "Senior")) & (filtered_df["is_remote"] == False)]
    senior_remote = filtered_df[(filtered_df["level"] == "Senior") & (filtered_df["is_remote"] == True)]
    senior_onsite = filtered_df[(filtered_df["level"] != "Senior") & (filtered_df["is_remote"] == False)]

    breakdown_data = {
        'Category': [
            "All Jobs", 
            "Senior - All", "Senior - Onsite", "Senior - Remote", 
            "Mid-Level - All", "Mid-Level - Onsite", "Mid-Level - Remote",
            "Junior - All", "Junior - Onsite", "Junior - Remote"
        ],
        
        'Count': [
            len(filtered_df),
            len(senior_onsite) + len(senior_remote),
            len(senior_onsite),
            len(senior_remote),
            
            len(mid_onsite) + len(mid_remote),
            len(mid_onsite),
            len(mid_remote),
            
            len(junior_onsite) + len(junior_remote),
            len(junior_onsite),
            len(junior_remote)
        ],

        'Color': [
            '#E6C229', 
            '#F17105', 
            '#D11149', 
            '#6610F2', 
            '#1a8fe3', 
            '#CBEF43',
            '#8DE969',
            '#00A6A6',
            '#EFCA08',
            '#F49F0A'
        ]
    }

    fig = go.Figure(data=[
        go.Bar(
            x=breakdown_data['Count'],
            y=breakdown_data['Category'],
            orientation='h',
            marker=dict(
                color=breakdown_data['Color'],
                line=dict(color='rgba(255,255,255,0.1)', width=1)
            ),
            text=breakdown_data['Count'],
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Count: %{x}<extra></extra>'
        )
    ])
    fig.update_layout(
        title=dict(text="Job Level & Location Breakdown", font=dict(size=20, color=colors['text'])),
        paper_bgcolor=colors['surface'],
        plot_bgcolor=colors['surface'],
        font=dict(color=colors['text']),
        xaxis=dict(
            title="Number of Jobs",
            gridcolor=colors['border'],
            showgrid=True
        ),
        yaxis=dict(
            title="",
            gridcolor=colors['border']
        ),
        margin=dict(l=200, r=20, t=60, b=60),
        hoverlabel=dict(bgcolor=colors['primary'], font_size=14)
    )
    return fig

fig_junior = create_breakdown_figure(df)

# App Layout
app.layout = html.Div([
    dcc.Store(id='date-filter-state', data='all'),
    
    html.Div([
        html.H1("Job Search Dashboard", 
                style={
                    "textAlign": "center",
                    "color": colors['text'],
                    "marginBottom": "10px",
                    "fontSize": "2.5rem",
                    "fontWeight": "700"
                }),
        html.P(f"Total Jobs Found: {len(df)} | Last Updated: {df['scraped_at'].iloc[0] if len(df) > 0 else 'N/A'}",
               style={
                   "textAlign": "center",
                   "color": colors['text_secondary'],
                   "fontSize": "1.1rem"
               })
    ], style={
        "padding": "30px 20px",
        "backgroundColor": colors['background'],
        "borderBottom": f"2px solid {colors['border']}"
    }),

    html.Div([
        html.H3("Filter by Date Posted:", 
                style={
                    "color": colors['text'],
                    "marginBottom": "15px",
                    "fontSize": "1.3rem"
                }),
        html.Div([
            html.Button("Last 24 Hours", id="btn-day", n_clicks=0,
                       style={
                           "padding": "10px 20px",
                           "margin": "5px",
                           "backgroundColor": colors['primary'],
                           "color": "white",
                           "border": "none",
                           "borderRadius": "5px",
                           "cursor": "pointer",
                           "fontSize": "1rem",
                           "fontWeight": "500"
                       }),
            html.Button("Last 7 Days", id="btn-week", n_clicks=0,
                       style={
                           "padding": "10px 20px",
                           "margin": "5px",
                           "backgroundColor": colors['secondary'],
                           "color": "white",
                           "border": "none",
                           "borderRadius": "5px",
                           "cursor": "pointer",
                           "fontSize": "1rem",
                           "fontWeight": "500"
                       }),
            html.Button("All Time", id="btn-all", n_clicks=0,
                       style={
                           "padding": "10px 20px",
                           "margin": "5px",
                           "backgroundColor": colors['accent'],
                           "color": "white",
                           "border": "none",
                           "borderRadius": "5px",
                           "cursor": "pointer",
                           "fontSize": "1rem",
                           "fontWeight": "500"
                       })
        ], style={"display": "flex", "justifyContent": "center", "flexWrap": "wrap"})
    ], style={
        "padding": "20px",
        "backgroundColor": colors['background'],
        "textAlign": "center"
    }),

    html.Div([
        html.Div([
            dcc.Graph(id="junior", figure=fig_junior, style={"height": "500px"})
        ], style={"padding": "20px"}),
    ], style={
        "display": "grid",
        "gridTemplateColumns": "repeat(auto-fit, minmax(400px, 1fr))",
        "gap": "20px",
        "backgroundColor": colors['background'],
        "padding": "20px"
    }),

    html.Div([
        html.Div([
            html.H2("Job Listings", 
                    style={
                        "color": colors['text'],
                        "marginBottom": "20px",
                        "fontSize": "1.8rem"
                    }),
            html.P("Click on any chart segment to filter jobs. Click again to reset.",
                style={"color": colors['text_secondary'], "marginBottom": "20px"})
        ], style={"padding": "20px 30px"}),
        
        html.Div(id="results", style={"padding": "0 30px 30px 30px"})
    ], style={
        "backgroundColor": colors['background'],
        "minHeight": "400px"
    })
], style={
    "backgroundColor": colors['background'],
    "minHeight": "100vh",
    "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    
})

@app.callback(
    Output('date-filter-state', 'data'),
    [Input("btn-day", "n_clicks"),
     Input("btn-week", "n_clicks"),
     Input("btn-all", "n_clicks")]
)
def update_date_filter(btn_day, btn_week, btn_all):
    if not ctx.triggered:
        return 'all'
    
    button_id = ctx.triggered_id
    
    if button_id == "btn-day":
        return 'day'
    elif button_id == "btn-week":
        return 'week'
    elif button_id == "btn-all":
        return 'all'
    
    return 'all'

@app.callback(
    [Output("junior", "figure"),
     Output("results", "children")],
    [Input('date-filter-state', 'data'),
     Input("junior", "clickData")]
)
def filter_jobs(date_filter, junior_click):
    # Apply date filter first
    date_filtered = df.copy()
    
    if date_filter == 'day':
        cutoff_date = datetime.now() - timedelta(days=1)
        date_filtered = date_filtered[date_filtered['posted_date'] >= cutoff_date]
    elif date_filter == 'week':
        cutoff_date = datetime.now() - timedelta(days=7)
        date_filtered = date_filtered[date_filtered['posted_date'] >= cutoff_date]
    
    # Always create chart based on date-filtered data (shows all categories)
    updated_fig = create_breakdown_figure(date_filtered)
    
    # For job listings, apply both date AND chart click filters
    results_filtered = date_filtered.copy()
    
    if junior_click:
        label = junior_click["points"][0]["y"]

        if label == "Senior - All":
            results_filtered = results_filtered[results_filtered["level"] == "Senior"]

        elif label == "Senior - Remote":
            results_filtered = results_filtered[
                (results_filtered["level"] == "Senior") &
                (results_filtered["is_remote"] == True)
            ]

        elif label == "Senior - Onsite":
            results_filtered = results_filtered[
                (results_filtered["level"] == "Senior") &
                (results_filtered["is_remote"] == False)
            ]
            
        elif label == "Mid-Level - All":
            results_filtered = results_filtered[((results_filtered["level"] != "Senior") & (results_filtered["level"] != "Junior"))]

        elif label == "Mid-Level - Remote":
            results_filtered = results_filtered[
                ((results_filtered["level"] != "Senior") & (results_filtered["level"] != "Junior")) &
                (results_filtered["is_remote"] == True)
            ]

        elif label == "Mid-Level - Onsite":
            results_filtered = results_filtered[
                ((results_filtered["level"] != "Senior") & (results_filtered["level"] != "Junior")) &
                (results_filtered["is_remote"] == False)
            ]
        
        elif label == "Junior - All":
            results_filtered = results_filtered[results_filtered["level"] == "Junior"]

        elif label == "Junior - Remote":
            results_filtered = results_filtered[
                (results_filtered["level"] == "Junior") &
                (results_filtered["is_remote"] == True)
            ]
            
        elif label == "Junior - Onsite":
            results_filtered = results_filtered[
                (results_filtered["level"] == "Junior") &
                (results_filtered["is_remote"] == False)
            ]

    if results_filtered.empty:
        return updated_fig, html.P("No jobs match this filter.", style={"color": colors['text']})

    job_listings = [
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
                style={"color": colors['primary'], "textDecoration": "none"}
            )
        ], style={"margin-bottom": "5px", "display": "flex", "alignItems": "center"})
        for idx, row in results_filtered.iterrows()
    ]

    return updated_fig, job_listings

if __name__ == "__main__":
    app.run()