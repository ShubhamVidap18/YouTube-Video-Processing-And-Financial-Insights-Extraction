import pymongo
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import re
from dateutil import parser
import plotly.express as px
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import plotly.graph_objects as go

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ Establish MongoDB Connection with Error Handling
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    db = client["youtube_data"]
    collection = db["videos"]
    client.server_info()  # ✅ Test connection
    logging.info("✅ Successfully connected to MongoDB")
except Exception as e:
    logging.error(f"❌ Error connecting to MongoDB: {e}")
    exit()

# ✅ Fetch Trade Types Safely from MongoDB
def get_trade_types():
    try:
        trade_types = collection.distinct("Financial Insights.direction")  # Fetch unique trade directions
        return [t.upper() for t in trade_types if isinstance(t, str)]  # Ensure all are uppercase strings
    except Exception as e:
        logging.error(f"❌ Error fetching trade types: {e}")
        return []

trade_types = get_trade_types()

# ✅ FastAPI Setup
app_api = FastAPI()

class QueryRequest(BaseModel):
    query: str

# ✅ Load and preprocess data from MongoDB
def load_data():
    """Fetch data from MongoDB, convert 'Upload Date' to ISO format, and handle missing fields."""
    try:
        data = list(collection.find({}, {"_id": 0, "Upload Date": 1, "Financial Insights": 1, "Stock Name": 1}))
        if not data:
            logging.warning("⚠ No data found in MongoDB.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        logging.info(f"✅ Successfully fetched {len(df)} records from MongoDB.")

        if "Upload Date" in df.columns:
            df["Upload Date"] = pd.to_datetime(df["Upload Date"], format="%m/%d/%Y", errors="coerce")
            df.dropna(subset=["Upload Date"], inplace=True)
            df.sort_values("Upload Date", inplace=True)

        if "Stock Name" not in df.columns:
            df["Stock Name"] = None

        return df

    except Exception as e:
        logging.error(f"❌ Error fetching data: {e}")
        return pd.DataFrame()

# ✅ Extract relevant information from user query
def parse_query(query):
    """Extract date range, trade type, and stock name from user query using MongoDB data."""
    try:
        date_matches = re.findall(r'\b(\w+ \d{1,2}, \d{4})\b', query)
        stock_match = re.search(r"\b[A-Z]{2,}\b", query)
        stock_name = stock_match.group(0) if stock_match else None

        trade_type = next((t for t in trade_types if t in query.upper()), None)

        if len(date_matches) >= 2:
            start_date, end_date = map(parser.parse, date_matches[:2])
        else:
            start_date, end_date = pd.to_datetime("2024-05-01"), pd.to_datetime("2024-12-31")

        logging.info(f"✅ Query Parsed: Start = {start_date}, End = {end_date}, Trade Type = {trade_type}, Stock = {stock_name}")
        return start_date, end_date, trade_type, stock_name

    except Exception as e:
        logging.error(f"❌ Error parsing query: {e}")
        return None, None, None, None

# ✅ Query function based on extracted details
def query_data(start_date, end_date, trade_type, stock_name):
    """Filter data based on user query."""
    df = load_data()
    if df.empty or not trade_type:
        logging.warning("⚠ No data available after filtering.")
        return pd.DataFrame()

    filtered_data = df[(df["Upload Date"] >= start_date) & (df["Upload Date"] <= end_date)]

    if stock_name:
        filtered_data = filtered_data[filtered_data["Stock Name"] == stock_name]

    extracted_data = []
    for _, row in filtered_data.iterrows():
        insights = row.get("Financial Insights", {})
        direction = insights.get("direction", "").upper()

        if trade_type == "LONG" and direction == "LONG":
            buy_area = insights.get("Buy_Area", [])
            if buy_area:
                highest_buy = max(buy_area, key=lambda x: x[0])[0]
                extracted_data.append((row["Upload Date"], highest_buy))

        elif trade_type == "SHORT" and direction == "SHORT":
            sell_area = insights.get("Sell_Area", [])
            if sell_area:
                lowest_sell = min(sell_area, key=lambda x: x[0])[0]
                extracted_data.append((row["Upload Date"], lowest_sell))

    df_result = pd.DataFrame(extracted_data, columns=["Date", f"{trade_type} Price"])
    logging.info(f"✅ Query Result: {len(df_result)} records found.")
    return df_result

# ✅ Dash App UI (Professional Look)
dash_app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
dash_app.layout = dbc.Container([
    html.H1("RAG-Based Query System for Financial Insights", className="text-center mt-4"),
    dbc.Row([
        dbc.Col(dcc.Input(id="query-input", type="text", placeholder="Enter query...", value="", className="form-control"), width=8),
        dbc.Col(dbc.Button("Run Query", id="query-button", n_clicks=0, color="primary"), width=4)
    ], className="my-3"),
    dbc.Row([
        dbc.Col(html.Div(id="query-output", className="text-warning")),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id="query-graph"), width=12)
    ])
], fluid=True)

# ✅ Dash Callback
@dash_app.callback(
    [Output("query-output", "children"), Output("query-graph", "figure")],
    [Input("query-button", "n_clicks")],
    [dash.dependencies.State("query-input", "value")]
)
def update_output(n_clicks, query):
    if not query:
        return "Please enter a query.", go.Figure()

    start_date, end_date, trade_type, stock_name = parse_query(query)
    if not all([start_date, end_date, trade_type]):
        return "Invalid query format.", go.Figure()

    results = query_data(start_date, end_date, trade_type, stock_name)
    if results.empty:
        return "No data found.", go.Figure()

    fig = px.line(results, x="Date", y=f"{trade_type} Price", title=f"{trade_type} Trade Prices")
    return f"{len(results)} records found.", fig

if __name__ == "__main__":
    dash_app.run_server(debug=True)
