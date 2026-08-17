"""
Sales Performance Analysis Dashboard
=====================================
An interactive Streamlit + Plotly dashboard for exploring the cleaned sales
dataset produced by scripts/run_analysis.py (or notebooks/sales_analysis.ipynb).

Run locally:
    streamlit run dashboard/app.py

The app expects the cleaned dataset at ../outputs/cleaned_sales_data.csv
relative to this file (i.e. outputs/cleaned_sales_data.csv from the project
root). If it isn't there yet, run the analysis pipeline first:
    python scripts/run_analysis.py
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Sales Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY = "#2563EB"
PALETTE = ["#2563EB", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#06B6D4"]

CUSTOM_CSS = """
<style>
    .stMetric { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; color: #1E3A8A; }
    .block-container { padding-top: 1.5rem; }
    h1, h2, h3 { color: #1E293B; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "outputs", "cleaned_sales_data.csv"),
        os.path.join(here, "outputs", "cleaned_sales_data.csv"),
        "outputs/cleaned_sales_data.csv",
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if path is None:
        return None
    df = pd.read_csv(path, parse_dates=["OrderDate", "ShipDate"])
    return df


df = load_data()

if df is None:
    st.error(
        "Could not find `outputs/cleaned_sales_data.csv`.\n\n"
        "Run the analysis pipeline first from the project root:\n\n"
        "```bash\npython scripts/run_analysis.py\n```\n"
        "or execute `notebooks/sales_analysis.ipynb`, then relaunch the dashboard."
    )
    st.stop()

sales_df_full = df[~df["IsReturn"]].copy()

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.title("📊 Filters")
st.sidebar.caption("Refine the dashboard by date, region, category, and segment.")

min_date, max_date = sales_df_full["OrderDate"].min(), sales_df_full["OrderDate"].max()
date_range = st.sidebar.date_input(
    "Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

regions = sorted(sales_df_full["Region"].dropna().unique().tolist())
sel_regions = st.sidebar.multiselect("Region", regions, default=regions)

categories = sorted(sales_df_full["Category"].dropna().unique().tolist())
sel_categories = st.sidebar.multiselect("Category", categories, default=categories)

segments = sorted(sales_df_full["Segment"].dropna().unique().tolist())
sel_segments = st.sidebar.multiselect("Customer segment", segments, default=segments)

include_returns = st.sidebar.checkbox("Include returns/cancellations in revenue figures", value=False)

st.sidebar.divider()
st.sidebar.caption(
    "Data source: synthetic retail sales dataset generated for this project "
    "(see `scripts/generate_data.py`). Replace `data/sales_data_raw.csv` with "
    "your own data (matching the same columns) to analyze real sales."
)

base_df = df if include_returns else sales_df_full
mask = (
    (base_df["OrderDate"] >= pd.to_datetime(start_date))
    & (base_df["OrderDate"] <= pd.to_datetime(end_date))
    & (base_df["Region"].isin(sel_regions))
    & (base_df["Category"].isin(sel_categories))
    & (base_df["Segment"].isin(sel_segments))
)
fdf = base_df.loc[mask].copy()

if fdf.empty:
    st.warning("No data matches the selected filters. Try widening your filter selection.")
    st.stop()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("📊 Sales Performance Analysis Dashboard")
st.caption(
    f"Showing **{fdf['OrderID'].nunique():,}** orders from "
    f"**{fdf['OrderDate'].min().date()}** to **{fdf['OrderDate'].max().date()}**"
)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
total_revenue = fdf["Sales"].sum()
total_profit = fdf["Profit"].sum()
margin = (total_profit / total_revenue * 100) if total_revenue else 0
total_orders = fdf["OrderID"].nunique()
aov = fdf.groupby("OrderID")["Sales"].sum().mean() if total_orders else 0
total_customers = fdf["CustomerID"].nunique()

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Revenue", f"${total_revenue:,.0f}")
k2.metric("Total Profit", f"${total_profit:,.0f}")
k3.metric("Profit Margin", f"{margin:.1f}%")
k4.metric("Orders", f"{total_orders:,}")
k5.metric("Avg Order Value", f"${aov:,.0f}")
k6.metric("Customers", f"{total_customers:,}")

st.divider()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_trends, tab_products, tab_customers, tab_geo, tab_data = st.tabs(
    ["📈 Trends", "🏆 Products & Categories", "👥 Customers", "🌍 Regions", "🔎 Raw Data"]
)

# --- Trends -----------------------------------------------------------
with tab_trends:
    col1, col2 = st.columns([2, 1])

    monthly = (
        fdf.assign(OrderMonth=fdf["OrderDate"].dt.to_period("M").astype(str))
        .groupby("OrderMonth")
        .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("OrderID", "nunique"))
        .reset_index()
        .sort_values("OrderMonth")
    )
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly["OrderMonth"], y=monthly["Revenue"], name="Revenue",
                              mode="lines+markers", line=dict(color=PRIMARY, width=3)))
    fig.add_trace(go.Scatter(x=monthly["OrderMonth"], y=monthly["Profit"], name="Profit",
                              mode="lines+markers", line=dict(color=PALETTE[2], width=3)))
    fig.update_layout(title="Monthly Revenue & Profit Trend", xaxis_title="Month", yaxis_title="USD",
                       hovermode="x unified", legend=dict(orientation="h", y=1.1))
    col1.plotly_chart(fig, use_container_width=True)

    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow = fdf.groupby("DayOfWeek")["OrderID"].nunique().reindex(dow_order).reset_index()
    dow.columns = ["DayOfWeek", "Orders"]
    fig2 = px.bar(dow, x="DayOfWeek", y="Orders", title="Orders by Day of Week",
                   color_discrete_sequence=[PALETTE[4]])
    col2.plotly_chart(fig2, use_container_width=True)

    fig3 = px.bar(monthly, x="OrderMonth", y="Orders", title="Order Volume by Month",
                   color_discrete_sequence=[PALETTE[1]])
    st.plotly_chart(fig3, use_container_width=True)

# --- Products & Categories ---------------------------------------------
with tab_products:
    col1, col2 = st.columns(2)

    cat_rev = fdf.groupby("Category")["Sales"].sum().sort_values(ascending=False).reset_index()
    fig4 = px.bar(cat_rev, x="Category", y="Sales", title="Revenue by Category",
                   color="Category", color_discrete_sequence=PALETTE, text_auto=".2s")
    fig4.update_layout(showlegend=False)
    col1.plotly_chart(fig4, use_container_width=True)

    top_products = fdf.groupby("ProductName")["Sales"].sum().sort_values(ascending=False).head(10).reset_index()
    fig5 = px.bar(top_products, x="Sales", y="ProductName", orientation="h", title="Top 10 Products by Revenue",
                   color_discrete_sequence=[PRIMARY])
    fig5.update_layout(yaxis=dict(autorange="reversed"))
    col2.plotly_chart(fig5, use_container_width=True)

    st.subheader("Discount vs. Profit Margin")
    scatter_df = fdf.copy()
    scatter_df["ProfitMargin"] = scatter_df["Profit"] / scatter_df["Sales"].replace(0, pd.NA)
    fig6 = px.scatter(
        scatter_df.sample(min(2000, len(scatter_df)), random_state=42),
        x="Discount", y="ProfitMargin", color="Category", opacity=0.6,
        color_discrete_sequence=PALETTE,
        title="Higher discounts tend to compress profit margin",
    )
    st.plotly_chart(fig6, use_container_width=True)

# --- Customers ------------------------------------------------------------
with tab_customers:
    col1, col2 = st.columns(2)

    seg = fdf.groupby("Segment").agg(Revenue=("Sales", "sum"), Orders=("OrderID", "nunique")).reset_index()
    fig7 = px.pie(seg, names="Segment", values="Revenue", title="Revenue Share by Segment",
                   color_discrete_sequence=PALETTE, hole=0.4)
    col1.plotly_chart(fig7, use_container_width=True)

    cust_freq = fdf.groupby("CustomerID")["OrderID"].nunique().reset_index(name="Orders")
    fig8 = px.histogram(cust_freq, x="Orders", nbins=cust_freq["Orders"].max() or 1,
                          title="Orders per Customer (Loyalty Distribution)",
                          color_discrete_sequence=[PRIMARY])
    col2.plotly_chart(fig8, use_container_width=True)

    st.subheader("Top 10 Customers by Revenue")
    top_cust = (
        fdf.groupby(["CustomerID", "CustomerName"])["Sales"].sum()
        .sort_values(ascending=False).head(10).reset_index()
    )
    top_cust["Sales"] = top_cust["Sales"].map(lambda v: f"${v:,.0f}")
    st.dataframe(top_cust, use_container_width=True, hide_index=True)

# --- Regions ----------------------------------------------------------
with tab_geo:
    col1, col2 = st.columns(2)

    region_rev = fdf.groupby("Region")["Sales"].sum().sort_values(ascending=False).reset_index()
    fig9 = px.pie(region_rev, names="Region", values="Sales", title="Revenue Share by Region",
                   color_discrete_sequence=PALETTE, hole=0.4)
    col1.plotly_chart(fig9, use_container_width=True)

    country_rev = fdf.groupby("Country")["Sales"].sum().sort_values(ascending=False).reset_index()
    fig10 = px.bar(country_rev, x="Country", y="Sales", title="Revenue by Country",
                    color_discrete_sequence=[PALETTE[3]])
    col2.plotly_chart(fig10, use_container_width=True)

    ship_mode_rev = fdf.groupby("ShipMode")["Sales"].sum().sort_values(ascending=False).reset_index()
    fig11 = px.bar(ship_mode_rev, x="ShipMode", y="Sales", title="Revenue by Shipping Mode",
                    color_discrete_sequence=[PALETTE[5]])
    st.plotly_chart(fig11, use_container_width=True)

# --- Raw data / export -------------------------------------------------
with tab_data:
    st.subheader("Filtered dataset")
    st.dataframe(fdf, use_container_width=True, height=420)
    st.download_button(
        "⬇️ Download filtered data as CSV",
        data=fdf.to_csv(index=False).encode("utf-8"),
        file_name="filtered_sales_data.csv",
        mime="text/csv",
    )

st.divider()
st.caption(
    "Built with Streamlit + Plotly · Sales Performance Analysis Dashboard project · "
    "Data is synthetic and generated for demonstration purposes."
)
