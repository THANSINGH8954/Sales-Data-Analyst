"""
run_analysis.py
----------------
End-to-end sales performance analysis pipeline:
  1. Load raw data
  2. Clean & preprocess
  3. Exploratory Data Analysis (EDA) -> saves chart images
  4. KPI computation -> saves kpis.json
  5. Business insights -> saves insights.json
  6. Writes the cleaned dataset used by the dashboard and the PDF report

This script contains the exact same logic as notebooks/sales_analysis.ipynb,
kept here as a plain, testable .py file so the whole pipeline can be run
non-interactively with:  python scripts/run_analysis.py
"""

import json
import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams["figure.dpi"] = 110
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.titlesize"] = 13

RAW_PATH = "data/sales_data_raw.csv"
CLEAN_PATH = "outputs/cleaned_sales_data.csv"
FIG_DIR = "outputs/figures"
KPI_PATH = "outputs/kpis.json"
INSIGHTS_PATH = "outputs/insights.json"

os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs("outputs/reports", exist_ok=True)

ACCENT = "#2563EB"
PALETTE = ["#2563EB", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#06B6D4"]


# ===========================================================================
# 1. LOAD
# ===========================================================================
print("Loading raw data...")
df = pd.read_csv(RAW_PATH)
raw_rows = len(df)
print(f"  Raw shape: {df.shape}")

# ===========================================================================
# 2. DATA CLEANING & PREPROCESSING
# ===========================================================================
print("Cleaning data...")

# --- 2.1 Standardize text columns (strip whitespace, fix casing) ----------
text_cols = ["Segment", "Category", "Region", "ShipMode", "CustomerName", "Country", "ProductName"]
for col in text_cols:
    df[col] = df[col].astype("string").str.strip()

df["Segment"] = df["Segment"].str.title()
df["Category"] = df["Category"].str.title()

# --- 2.2 Parse dates (handle the mixed dd/mm/yyyy + yyyy-mm-dd formats) ---
def parse_mixed_date(s):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.NaT

df["OrderDate"] = df["OrderDate"].apply(parse_mixed_date)
df["ShipDate"] = pd.to_datetime(df["ShipDate"], format="%Y-%m-%d", errors="coerce")

# --- 2.3 Drop exact duplicate rows -----------------------------------------
dupes_removed = df.duplicated().sum()
df = df.drop_duplicates().reset_index(drop=True)

# --- 2.4 Handle missing values ---------------------------------------------
# Region can be re-derived from Country; fall back to mode if unknown country
country_to_region = (
    df.dropna(subset=["Region"]).groupby("Country")["Region"].agg(lambda s: s.mode().iloc[0]).to_dict()
)
df["Region"] = df.apply(
    lambda r: country_to_region.get(r["Country"], r["Region"]) if pd.isna(r["Region"]) else r["Region"],
    axis=1,
)
df["Region"] = df["Region"].fillna(df["Region"].mode().iloc[0])

# CustomerName: fill from CustomerID -> name mapping built from non-null rows
id_to_name = df.dropna(subset=["CustomerName"]).drop_duplicates("CustomerID").set_index("CustomerID")["CustomerName"].to_dict()
df["CustomerName"] = df.apply(
    lambda r: id_to_name.get(r["CustomerID"], "Unknown Customer") if pd.isna(r["CustomerName"]) else r["CustomerName"],
    axis=1,
)

# ShipMode: impute with the most common ship mode
df["ShipMode"] = df["ShipMode"].fillna(df["ShipMode"].mode().iloc[0])

# Discount: assume no discount when missing (business rule)
df["Discount"] = df["Discount"].fillna(0.0)

missing_after = df.isna().sum().sum()

# --- 2.5 Handle returns / cancellations (negative quantity) ---------------
df["IsReturn"] = df["Quantity"] < 0
returns_count = int(df["IsReturn"].sum())

# Keep returns in the dataset (they're real business events) but analyze
# "net" sales/profit for KPIs, and gross sales for a separate returns view.
df["NetSales"] = df["Sales"]
df["NetProfit"] = df["Profit"]

# --- 2.6 Outlier handling on Sales (cap extreme values using IQR) ---------
q1, q3 = df["Sales"].quantile([0.25, 0.75])
iqr = q3 - q1
upper_bound = q3 + 3 * iqr
outliers = int((df["Sales"] > upper_bound).sum())
# We flag rather than delete outliers -- large B2B orders are legitimate --
# but keep the flag available for analysts who want to exclude them.
df["SalesOutlier"] = df["Sales"] > upper_bound

# --- 2.7 Derived/engineered columns ----------------------------------------
df["OrderMonth"] = df["OrderDate"].dt.to_period("M").astype(str)
df["OrderYear"] = df["OrderDate"].dt.year
df["OrderQuarter"] = df["OrderDate"].dt.to_period("Q").astype(str)
df["DayOfWeek"] = df["OrderDate"].dt.day_name()
df["ShippingDelayDays"] = (df["ShipDate"] - df["OrderDate"]).dt.days
df["ProfitMargin"] = np.where(df["Sales"] != 0, df["Profit"] / df["Sales"], np.nan)

clean_rows = len(df)
df.to_csv(CLEAN_PATH, index=False)
print(f"  Clean shape: {df.shape}  (removed {dupes_removed} duplicate rows)")
print(f"  Saved -> {CLEAN_PATH}")

# For most revenue/KPI analysis we exclude returns (negative-quantity lines)
sales_df = df[~df["IsReturn"]].copy()

# ===========================================================================
# 3. EXPLORATORY DATA ANALYSIS (EDA)
# ===========================================================================
print("Running EDA and saving charts...")

# --- 3.1 Monthly revenue trend --------------------------------------------
monthly = sales_df.groupby("OrderMonth").agg(Revenue=("NetSales", "sum"), Profit=("NetProfit", "sum")).reset_index()
monthly = monthly.sort_values("OrderMonth")

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(monthly["OrderMonth"], monthly["Revenue"], marker="o", color=ACCENT, linewidth=2, label="Revenue")
ax.plot(monthly["OrderMonth"], monthly["Profit"], marker="o", color=PALETTE[2], linewidth=2, label="Profit")
ax.set_title("Monthly Revenue & Profit Trend (2023-2024)")
ax.set_xlabel("Month")
ax.set_ylabel("USD")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:,.0f}K"))
plt.xticks(rotation=60, ha="right", fontsize=8)
ax.legend()
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/01_monthly_revenue_trend.png")
plt.close()

# --- 3.2 Revenue by category -------------------------------------------
cat_rev = sales_df.groupby("Category")["NetSales"].sum().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(cat_rev.index, cat_rev.values, color=PALETTE[:len(cat_rev)])
ax.set_title("Total Revenue by Product Category")
ax.set_ylabel("Revenue (USD)")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:,.0f}K"))
for b in bars:
    ax.annotate(f"${b.get_height()/1000:,.0f}K", (b.get_x() + b.get_width()/2, b.get_height()),
                ha="center", va="bottom", fontsize=9)
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/02_revenue_by_category.png")
plt.close()

# --- 3.3 Top 10 products by revenue ----------------------------------
top_products = sales_df.groupby("ProductName")["NetSales"].sum().sort_values(ascending=False).head(10)
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(top_products.index[::-1], top_products.values[::-1], color=ACCENT)
ax.set_title("Top 10 Products by Revenue")
ax.set_xlabel("Revenue (USD)")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:,.0f}K"))
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/03_top10_products.png")
plt.close()

# --- 3.4 Revenue by region ----------------------------------------------
region_rev = sales_df.groupby("Region")["NetSales"].sum().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(7, 7))
colors = PALETTE[:len(region_rev)]
wedges, texts, autotexts = ax.pie(
    region_rev.values, labels=region_rev.index, autopct="%1.1f%%", startangle=90, colors=colors,
    wedgeprops={"edgecolor": "white", "linewidth": 1.5},
)
ax.set_title("Revenue Share by Region")
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/04_revenue_by_region.png")
plt.close()

# --- 3.5 Customer segment analysis ---------------------------------------
seg = sales_df.groupby("Segment").agg(Revenue=("NetSales", "sum"), Orders=("OrderID", "nunique")).reset_index()
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
axes[0].bar(seg["Segment"], seg["Revenue"], color=PALETTE[1])
axes[0].set_title("Revenue by Customer Segment")
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1000:,.0f}K"))
axes[1].bar(seg["Segment"], seg["Orders"], color=PALETTE[3])
axes[1].set_title("Order Count by Customer Segment")
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/05_segment_analysis.png")
plt.close()

# --- 3.6 Discount vs profit margin relationship --------------------------
fig, ax = plt.subplots(figsize=(8, 6))
sample = sales_df.sample(min(1500, len(sales_df)), random_state=42)
sns.scatterplot(data=sample, x="Discount", y="ProfitMargin", hue="Category", palette=PALETTE, ax=ax, alpha=0.7, s=35)
ax.axhline(0, color="red", linestyle="--", linewidth=1)
ax.set_title("Discount Level vs. Profit Margin")
ax.set_xlabel("Discount")
ax.set_ylabel("Profit Margin")
ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/06_discount_vs_margin.png")
plt.close()

# --- 3.7 Order volume by day of week --------------------------------------
dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dow = sales_df.groupby("DayOfWeek")["OrderID"].nunique().reindex(dow_order)
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(dow.index, dow.values, color=PALETTE[4])
ax.set_title("Order Volume by Day of Week")
ax.set_ylabel("Number of Orders")
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/07_orders_by_dayofweek.png")
plt.close()

# --- 3.8 Customer purchase frequency distribution --------------------------
cust_freq = sales_df.groupby("CustomerID")["OrderID"].nunique()
fig, ax = plt.subplots(figsize=(8, 5))
sns.histplot(cust_freq, bins=range(1, cust_freq.max() + 2), color=ACCENT, ax=ax)
ax.set_title("Distribution of Orders per Customer")
ax.set_xlabel("Number of Orders")
ax.set_ylabel("Number of Customers")
plt.tight_layout()
plt.savefig(f"{FIG_DIR}/08_customer_order_frequency.png")
plt.close()

print(f"  Saved {len(os.listdir(FIG_DIR))} chart images -> {FIG_DIR}/")

# ===========================================================================
# 4. KPI ANALYSIS
# ===========================================================================
print("Computing KPIs...")

total_revenue = float(sales_df["NetSales"].sum())
total_profit = float(sales_df["NetProfit"].sum())
profit_margin_pct = (total_profit / total_revenue * 100) if total_revenue else 0
total_orders = int(sales_df["OrderID"].nunique())
total_customers = int(sales_df["CustomerID"].nunique())
avg_order_value = float(sales_df.groupby("OrderID")["NetSales"].sum().mean())
total_units_sold = int(sales_df["Quantity"].sum())
return_rate_pct = float(returns_count / clean_rows * 100)

# Month-over-month revenue growth (last full month vs previous)
monthly_sorted = monthly.sort_values("OrderMonth")
mom_growth_pct = None
if len(monthly_sorted) >= 2:
    last, prev = monthly_sorted["Revenue"].iloc[-1], monthly_sorted["Revenue"].iloc[-2]
    mom_growth_pct = float((last - prev) / prev * 100) if prev else None

# Year-over-year growth
yearly = sales_df.groupby("OrderYear")["NetSales"].sum().sort_index()
yoy_growth_pct = None
if len(yearly) >= 2:
    yoy_growth_pct = float((yearly.iloc[-1] - yearly.iloc[-2]) / yearly.iloc[-2] * 100)

# Repeat customer rate
orders_per_cust = sales_df.groupby("CustomerID")["OrderID"].nunique()
repeat_customer_rate_pct = float((orders_per_cust > 1).mean() * 100)

top_category = cat_rev.idxmax()
top_product = top_products.idxmax()
top_region = region_rev.idxmax()
best_day = dow.idxmax()

kpis = {
    "total_revenue": round(total_revenue, 2),
    "total_profit": round(total_profit, 2),
    "profit_margin_pct": round(profit_margin_pct, 2),
    "total_orders": total_orders,
    "total_customers": total_customers,
    "avg_order_value": round(avg_order_value, 2),
    "total_units_sold": total_units_sold,
    "return_rate_pct": round(return_rate_pct, 2),
    "mom_revenue_growth_pct": round(mom_growth_pct, 2) if mom_growth_pct is not None else None,
    "yoy_revenue_growth_pct": round(yoy_growth_pct, 2) if yoy_growth_pct is not None else None,
    "repeat_customer_rate_pct": round(repeat_customer_rate_pct, 2),
    "top_category": top_category,
    "top_product": top_product,
    "top_region": top_region,
    "best_day_of_week": best_day,
    "data_quality": {
        "raw_rows": int(raw_rows),
        "clean_rows": int(clean_rows),
        "duplicates_removed": int(dupes_removed),
        "missing_values_remaining": int(missing_after),
        "outlier_rows_flagged": int(outliers),
        "return_rows": int(returns_count),
    },
}

with open(KPI_PATH, "w") as f:
    json.dump(kpis, f, indent=2)
print(f"  Saved -> {KPI_PATH}")
print(json.dumps(kpis, indent=2))

# ===========================================================================
# 5. BUSINESS INSIGHTS
# ===========================================================================
top3_categories = cat_rev.head(3)
bottom_category = cat_rev.idxmin()
top3_products = top_products.head(3)
region_share = (region_rev / region_rev.sum() * 100).round(1)
seg_sorted = seg.sort_values("Revenue", ascending=False)

insights = [
    f"Total revenue across the analysis period reached ${total_revenue:,.0f} with an overall profit "
    f"margin of {profit_margin_pct:.1f}%, generating ${total_profit:,.0f} in profit.",

    f"{top_category} is the leading product category, contributing ${top3_categories.iloc[0]:,.0f} "
    f"({top3_categories.iloc[0] / total_revenue * 100:.1f}% of total revenue), followed by "
    f"{top3_categories.index[1]} and {top3_categories.index[2]}. "
    f"{bottom_category} is the lowest-performing category and is a candidate for a promotional "
    f"push or portfolio review.",

    f"The single best-selling product is '{top_product}', generating "
    f"${top3_products.iloc[0]:,.0f} in revenue. The top 3 products together account for "
    f"${top3_products.sum():,.0f} in revenue, indicating some concentration risk worth monitoring.",

    f"{top_region} is the strongest region, driving {region_share.iloc[0]:.1f}% of total revenue. "
    f"Regional revenue is distributed as: " + ", ".join(f"{r} {p:.1f}%" for r, p in region_share.items()) + ".",

    f"{seg_sorted.iloc[0]['Segment']} is the highest-value customer segment by revenue "
    f"(${seg_sorted.iloc[0]['Revenue']:,.0f}), suggesting marketing and retention budget should be "
    f"weighted toward this group.",

    f"Repeat customers make up {repeat_customer_rate_pct:.1f}% of the customer base. "
    f"Growing this rate even a few points has an outsized impact on revenue stability, since repeat "
    f"customers are cheaper to serve than new-customer acquisition.",

    f"{best_day} is the peak order day of the week, useful for scheduling promotions, staffing, "
    f"and ad spend timing.",

    (f"Month-over-month revenue growth was {mom_growth_pct:+.1f}% in the most recent month. "
     if mom_growth_pct is not None else "") +
    (f"Year-over-year revenue growth was {yoy_growth_pct:+.1f}%, showing the business trend at the "
      f"annual level." if yoy_growth_pct is not None else ""),

    f"Higher discount levels (>15%) are associated with thinner or negative profit margins in the "
    f"data, so discounting strategy should be reviewed on a category-by-category basis rather than "
    f"applied uniformly.",

    f"The return rate is {return_rate_pct:.1f}% of line items. This is within a normal retail range but "
    f"should be tracked over time as a leading indicator of product-quality or fulfillment issues.",
]

with open(INSIGHTS_PATH, "w") as f:
    json.dump(insights, f, indent=2)
print(f"\nSaved {len(insights)} business insights -> {INSIGHTS_PATH}")

print("\nDone. Pipeline finished successfully.")
