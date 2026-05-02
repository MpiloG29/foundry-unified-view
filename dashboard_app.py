import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dash_table, dcc, html

DATA_PATH = "unified_manufacturing_view.csv"


def load_data() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        from unified import build_unified_view

        build_unified_view()

    df = pd.read_csv(DATA_PATH)
    date_columns = [
        "cycle_start_timestamp",
        "pressure_cycle_end_timestamp",
        "peak_pressure_timestamp",
        "temperature_timestamp",
        "silicon_timestamp",
    ]
    for column in date_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    df["production_day"] = pd.to_datetime(df["cycle_start_timestamp"]).dt.date.astype(str)
    df["has_alert"] = df[
        [
            "pressure_outlier",
            "temperature_outlier",
            "silicon_drift_alert",
            "missing_alignment_alert",
        ]
    ].any(axis=1)
    return df.sort_values("cycle_start_timestamp")


df = load_data()

app = Dash(__name__)
server = app.server

COLORS = {
    "background": "#f7f8fb",
    "surface": "#ffffff",
    "border": "#d9dee8",
    "text": "#172033",
    "muted": "#64708a",
    "blue": "#2563eb",
    "green": "#047857",
    "amber": "#b45309",
    "red": "#dc2626",
}


def metric_card(label: str, value: str, tone: str = "blue") -> html.Div:
    return html.Div(
        [html.Div(label, className="metric-label"), html.Div(value, className=f"metric-value {tone}")],
        className="metric-card",
    )


def dropdown_options(values):
    return [{"label": value, "value": value} for value in sorted(values)]


app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        html.H1("Core Unified View"),
                        html.P("Live foundry dashboard for aligned pressure, temperature, silicon, and quality signals."),
                    ],
                    className="title-block",
                ),
                html.Div(
                    [
                        html.Label("Part Type"),
                        dcc.Dropdown(
                            id="part-type-filter",
                            options=dropdown_options(df["part_type"].dropna().unique()),
                            multi=True,
                            placeholder="All part types",
                        ),
                        html.Label("Batch"),
                        dcc.Dropdown(
                            id="batch-filter",
                            options=dropdown_options(df["production_batch_id"].dropna().unique()),
                            multi=True,
                            placeholder="All batches",
                        ),
                        html.Label("Production Date"),
                        dcc.DatePickerRange(
                            id="date-filter",
                            min_date_allowed=df["cycle_start_timestamp"].min().date(),
                            max_date_allowed=df["cycle_start_timestamp"].max().date(),
                            start_date=df["cycle_start_timestamp"].min().date(),
                            end_date=df["cycle_start_timestamp"].max().date(),
                            display_format="YYYY-MM-DD",
                        ),
                    ],
                    className="filters",
                ),
            ],
            className="topbar",
        ),
        html.Div(id="metric-row", className="metric-row"),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.H2("Unified Part View"),
                                html.Div(id="table-count", className="subtle"),
                            ],
                            className="panel-heading",
                        ),
                        dash_table.DataTable(
                            id="parts-table",
                            columns=[
                                {"name": "Part ID", "id": "unique_part_identifier"},
                                {"name": "Type", "id": "part_type"},
                                {"name": "Batch", "id": "production_batch_id"},
                                {"name": "Cycle Start", "id": "cycle_start_timestamp"},
                                {"name": "Max Pressure", "id": "max_pressure", "type": "numeric", "format": {"specifier": ".2f"}},
                                {"name": "Time to Peak", "id": "time_to_peak_min", "type": "numeric", "format": {"specifier": ".1f"}},
                                {"name": "Temp C", "id": "casting_temperature_C", "type": "numeric", "format": {"specifier": ".1f"}},
                                {"name": "Silicon %", "id": "silicon_content_percent", "type": "numeric", "format": {"specifier": ".2f"}},
                                {"name": "Quality", "id": "unified_part_quality_index", "type": "numeric", "format": {"specifier": ".1f"}},
                            ],
                            page_size=12,
                            sort_action="native",
                            filter_action="native",
                            row_selectable="single",
                            selected_rows=[0],
                            style_as_list_view=True,
                            style_cell={
                                "fontFamily": "Inter, Segoe UI, Arial, sans-serif",
                                "fontSize": "13px",
                                "padding": "9px",
                                "textAlign": "left",
                                "border": "0",
                                "minWidth": "88px",
                            },
                            style_header={
                                "backgroundColor": "#eef2f7",
                                "fontWeight": "700",
                                "color": COLORS["text"],
                                "border": "0",
                            },
                            style_data_conditional=[
                                {
                                    "if": {"filter_query": "{has_alert} = True"},
                                    "backgroundColor": "#fff1f2",
                                    "color": "#7f1d1d",
                                },
                                {
                                    "if": {"state": "selected"},
                                    "backgroundColor": "#dbeafe",
                                    "border": "1px solid #2563eb",
                                },
                            ],
                        ),
                    ],
                    className="panel wide",
                ),
                html.Div(
                    [
                        html.H2("Anomaly Alerts"),
                        html.Div(id="alert-list", className="alert-list"),
                    ],
                    className="panel narrow",
                ),
            ],
            className="main-grid",
        ),
        html.Div(
            [
                html.Div([dcc.Graph(id="pressure-cycle-chart", config={"displayModeBar": False})], className="panel"),
                html.Div([dcc.Graph(id="temperature-chart", config={"displayModeBar": False})], className="panel"),
                html.Div([dcc.Graph(id="silicon-chart", config={"displayModeBar": False})], className="panel"),
                html.Div([dcc.Graph(id="quality-chart", config={"displayModeBar": False})], className="panel"),
            ],
            className="chart-grid",
        ),
    ],
    className="app-shell",
)


@app.callback(
    Output("parts-table", "data"),
    Output("table-count", "children"),
    Output("metric-row", "children"),
    Output("pressure-cycle-chart", "figure"),
    Output("temperature-chart", "figure"),
    Output("silicon-chart", "figure"),
    Output("quality-chart", "figure"),
    Output("alert-list", "children"),
    Input("part-type-filter", "value"),
    Input("batch-filter", "value"),
    Input("date-filter", "start_date"),
    Input("date-filter", "end_date"),
)
def update_dashboard(part_types, batches, start_date, end_date):
    filtered = df.copy()

    if part_types:
        filtered = filtered[filtered["part_type"].isin(part_types)]
    if batches:
        filtered = filtered[filtered["production_batch_id"].isin(batches)]
    if start_date:
        filtered = filtered[filtered["cycle_start_timestamp"] >= pd.to_datetime(start_date)]
    if end_date:
        end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1)
        filtered = filtered[filtered["cycle_start_timestamp"] < end_ts]

    if filtered.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(template="plotly_white", title="No records match the filters")
        return [], "0 parts", [], empty_fig, empty_fig, empty_fig, empty_fig, html.Div("No alerts")

    table_df = filtered.copy()
    for column in ["cycle_start_timestamp", "peak_pressure_timestamp", "temperature_timestamp", "silicon_timestamp"]:
        table_df[column] = table_df[column].dt.strftime("%Y-%m-%d %H:%M").fillna("")

    metrics = [
        metric_card("Parts", f"{len(filtered):,}"),
        metric_card("Avg Max Pressure", f"{filtered['max_pressure'].mean():.2f}"),
        metric_card("Avg Temp", f"{filtered['casting_temperature_C'].mean():.1f} C", "amber"),
        metric_card("Avg Silicon", f"{filtered['silicon_content_percent'].mean():.2f}%", "green"),
        metric_card("Alerts", f"{int(filtered['has_alert'].sum())}", "red"),
    ]

    pressure_fig = go.Figure()
    pressure_fig.add_trace(
        go.Scatter(
            x=filtered["cycle_start_timestamp"],
            y=filtered["max_pressure"],
            mode="lines+markers",
            name="Max pressure",
            line={"color": COLORS["blue"], "width": 2},
            marker={"size": 7},
            customdata=filtered[["unique_part_identifier", "part_type", "time_to_peak_min"]],
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Max: %{y:.2f}<br>Peak in %{customdata[2]:.1f} min<extra></extra>",
        )
    )
    pressure_fig.add_trace(
        go.Scatter(
            x=filtered["peak_pressure_timestamp"],
            y=filtered["max_pressure"],
            mode="markers",
            name="Peak marker",
            marker={"symbol": "triangle-up", "size": 11, "color": COLORS["red"]},
            hovertemplate="Peak timestamp: %{x}<br>Pressure: %{y:.2f}<extra></extra>",
        )
    )
    pressure_fig.update_layout(
        title="Pressure Cycle Explorer",
        xaxis_title="Production cycle",
        yaxis_title="Pressure",
        template="plotly_white",
        margin={"l": 45, "r": 20, "t": 55, "b": 40},
    )

    batch_temp = filtered.groupby("production_batch_id", as_index=False).agg(
        avg_temp=("casting_temperature_C", "mean"),
        temp_std=("casting_temperature_C", "std"),
        stability=("temperature_stability_index", "mean"),
    )
    temp_fig = go.Figure()
    temp_fig.add_trace(
        go.Bar(
            x=batch_temp["production_batch_id"],
            y=batch_temp["avg_temp"],
            name="Avg temp",
            marker_color=COLORS["amber"],
            error_y={"type": "data", "array": batch_temp["temp_std"].fillna(0), "visible": True},
        )
    )
    temp_fig.add_trace(
        go.Scatter(
            x=batch_temp["production_batch_id"],
            y=batch_temp["stability"],
            name="Stability index",
            yaxis="y2",
            mode="lines+markers",
            line={"color": COLORS["green"], "width": 3},
        )
    )
    temp_fig.update_layout(
        title="Temperature Stability Monitor",
        xaxis_title="Batch",
        yaxis_title="Temperature C",
        yaxis2={"title": "Stability index", "overlaying": "y", "side": "right", "range": [0, 100]},
        template="plotly_white",
        margin={"l": 45, "r": 55, "t": 55, "b": 70},
    )

    silicon_fig = go.Figure()
    silicon_fig.add_trace(
        go.Scatter(
            x=filtered["cycle_start_timestamp"],
            y=filtered["silicon_content_percent"],
            mode="lines+markers",
            line={"shape": "hv", "color": COLORS["green"], "width": 3},
            name="Applied silicon",
            connectgaps=False,
            hovertemplate="Cycle: %{x}<br>Silicon: %{y:.2f}%<extra></extra>",
        )
    )
    silicon_alerts = filtered[filtered["silicon_drift_alert"] | filtered["missing_alignment_alert"]]
    silicon_fig.add_trace(
        go.Scatter(
            x=silicon_alerts["cycle_start_timestamp"],
            y=silicon_alerts["silicon_content_percent"],
            mode="markers",
            marker={"color": COLORS["red"], "size": 11, "symbol": "x"},
            name="Silicon alert",
        )
    )
    silicon_fig.update_layout(
        title="Silicon Content Overlay",
        xaxis_title="Production cycle",
        yaxis_title="Silicon content %",
        template="plotly_white",
        margin={"l": 45, "r": 20, "t": 55, "b": 40},
    )

    quality_fig = px.scatter(
        filtered,
        x="casting_temperature_C",
        y="max_pressure",
        color="part_type",
        size="time_to_peak_min",
        symbol="has_alert",
        hover_name="unique_part_identifier",
        hover_data={
            "production_batch_id": True,
            "unified_part_quality_index": ":.1f",
            "silicon_content_percent": ":.2f",
            "time_to_peak_min": ":.1f",
        },
        title="Anomaly Alerts and Quality Map",
        labels={
            "casting_temperature_C": "Casting temperature C",
            "max_pressure": "Max pressure",
            "part_type": "Part type",
            "has_alert": "Has alert",
        },
        template="plotly_white",
    )
    quality_fig.update_traces(marker={"line": {"width": 1, "color": "#1f2937"}})
    quality_fig.update_layout(margin={"l": 45, "r": 20, "t": 55, "b": 40})

    alert_rows = filtered[filtered["has_alert"]].head(8)
    if alert_rows.empty:
        alert_list = html.Div("No anomalies in the selected view.", className="empty-alert")
    else:
        alert_items = []
        for _, row in alert_rows.iterrows():
            labels = []
            if row["pressure_outlier"]:
                labels.append("Pressure")
            if row["temperature_outlier"]:
                labels.append("Temperature")
            if row["silicon_drift_alert"]:
                labels.append("Silicon drift")
            if row["missing_alignment_alert"]:
                labels.append("Missing join")
            alert_items.append(
                html.Div(
                    [
                        html.Div(row["unique_part_identifier"], className="alert-title"),
                        html.Div(f"{row['part_type']} | {row['production_batch_id']}", className="alert-meta"),
                        html.Div(", ".join(labels), className="alert-tags"),
                    ],
                    className="alert-item",
                )
            )
        alert_list = alert_items

    return (
        table_df.to_dict("records"),
        f"{len(filtered):,} parts in view",
        metrics,
        pressure_fig,
        temp_fig,
        silicon_fig,
        quality_fig,
        alert_list,
    )


app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Core Unified View</title>
        {%favicon%}
        {%css%}
        <style>
            * { box-sizing: border-box; }
            body {
                margin: 0;
                background: #f7f8fb;
                color: #172033;
                font-family: Inter, Segoe UI, Arial, sans-serif;
            }
            .app-shell { min-height: 100vh; padding: 22px; }
            .topbar {
                display: grid;
                grid-template-columns: minmax(260px, 1fr) minmax(420px, 1.8fr);
                gap: 18px;
                align-items: stretch;
                margin-bottom: 16px;
            }
            .title-block, .filters, .panel, .metric-card {
                background: #ffffff;
                border: 1px solid #d9dee8;
                border-radius: 8px;
                box-shadow: 0 10px 24px rgba(22, 32, 51, 0.06);
            }
            .title-block { padding: 20px 22px; }
            h1 { margin: 0; font-size: 30px; line-height: 1.1; letter-spacing: 0; }
            h2 { margin: 0; font-size: 17px; letter-spacing: 0; }
            p { margin: 8px 0 0; color: #64708a; line-height: 1.45; }
            .filters {
                display: grid;
                grid-template-columns: 1fr 1fr auto;
                gap: 8px 12px;
                padding: 14px;
                align-items: end;
            }
            .filters label {
                color: #4b5871;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
            }
            .metric-row {
                display: grid;
                grid-template-columns: repeat(5, minmax(140px, 1fr));
                gap: 12px;
                margin-bottom: 16px;
            }
            .metric-card { padding: 15px; min-height: 82px; }
            .metric-label {
                color: #64708a;
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
            }
            .metric-value { margin-top: 8px; font-size: 28px; font-weight: 800; color: #2563eb; }
            .metric-value.green { color: #047857; }
            .metric-value.amber { color: #b45309; }
            .metric-value.red { color: #dc2626; }
            .main-grid {
                display: grid;
                grid-template-columns: minmax(0, 2.5fr) minmax(280px, 0.8fr);
                gap: 16px;
                margin-bottom: 16px;
            }
            .chart-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 16px;
            }
            .panel { padding: 15px; overflow: hidden; }
            .panel-heading {
                display: flex;
                justify-content: space-between;
                gap: 12px;
                align-items: center;
                margin-bottom: 12px;
            }
            .subtle { color: #64708a; font-size: 13px; }
            .alert-list { display: grid; gap: 10px; margin-top: 12px; }
            .alert-item {
                border-left: 4px solid #dc2626;
                background: #fff7f7;
                padding: 10px 11px;
                border-radius: 6px;
            }
            .alert-title { font-weight: 800; }
            .alert-meta { color: #64708a; font-size: 12px; margin-top: 3px; }
            .alert-tags { color: #991b1b; font-size: 12px; font-weight: 700; margin-top: 7px; }
            .empty-alert { color: #047857; margin-top: 12px; font-weight: 700; }
            @media (max-width: 1100px) {
                .topbar, .main-grid, .chart-grid { grid-template-columns: 1fr; }
                .filters { grid-template-columns: 1fr; }
                .metric-row { grid-template-columns: repeat(2, minmax(140px, 1fr)); }
            }
            @media (max-width: 620px) {
                .app-shell { padding: 12px; }
                .metric-row { grid-template-columns: 1fr; }
                h1 { font-size: 24px; }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
