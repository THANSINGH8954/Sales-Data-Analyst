"""
generate_data.py
-----------------
Generates a synthetic but realistic retail sales dataset for the
Sales Performance Analysis Dashboard project.

The dataset intentionally contains common real-world data quality issues
(missing values, duplicate rows, inconsistent text casing, stray whitespace,
mixed date formats, a few negative quantities from returns) so that the
Data Cleaning & Preprocessing step in the notebook has real work to do.

Run:
    python scripts/generate_data.py
Output:
    data/sales_data_raw.csv
"""

import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

N_ORDERS = 6000  # base number of order line items before messiness is injected

# ---------------------------------------------------------------------------
# Reference / lookup data
# ---------------------------------------------------------------------------

REGIONS = {
    "North": ["USA", "Canada"],
    "South": ["Mexico", "Brazil", "Argentina"],
    "East": ["India", "China", "Japan", "South Korea"],
    "West": ["UK", "Germany", "France", "Spain"],
}

SEGMENTS = ["Consumer", "Corporate", "Home Office"]

SHIP_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]

CATEGORIES = {
    "Electronics": [
        ("Wireless Mouse", 15.99), ("Bluetooth Speaker", 39.99), ("USB-C Hub", 24.50),
        ("Noise Cancelling Headphones", 129.99), ("4K Webcam", 59.99),
        ("Smartwatch", 149.00), ("Portable SSD 1TB", 89.99), ("Mechanical Keyboard", 74.99),
        ("27-inch Monitor", 219.99), ("Power Bank 20000mAh", 34.99),
    ],
    "Office Supplies": [
        ("A4 Paper Ream", 4.50), ("Stapler", 6.25), ("Sticky Notes Pack", 3.10),
        ("Desk Organizer", 12.75), ("Whiteboard 3x2ft", 28.00), ("Printer Ink Cartridge", 21.99),
        ("Ballpoint Pen Box", 5.40), ("File Cabinet", 89.00), ("Ergonomic Chair", 159.99),
        ("Standing Desk", 249.00),
    ],
    "Furniture": [
        ("Bookshelf", 79.99), ("Office Desk", 189.99), ("Sofa 3-Seater", 499.00),
        ("Dining Table", 349.00), ("Bar Stool", 45.00), ("Coffee Table", 99.99),
        ("Bed Frame Queen", 259.00), ("Wardrobe", 329.00), ("Recliner Chair", 279.99),
        ("TV Stand", 119.99),
    ],
    "Clothing": [
        ("Men's T-Shirt", 12.99), ("Women's Jeans", 34.99), ("Running Shoes", 59.99),
        ("Winter Jacket", 89.99), ("Baseball Cap", 14.99), ("Formal Shirt", 29.99),
        ("Yoga Pants", 24.99), ("Wool Sweater", 44.99), ("Leather Belt", 19.99),
        ("Sneakers", 64.99),
    ],
    "Grocery": [
        ("Organic Coffee Beans 1kg", 13.50), ("Olive Oil 1L", 9.75), ("Almond Butter Jar", 7.99),
        ("Green Tea Box", 4.25), ("Protein Bar Pack", 11.50), ("Pasta 500g", 2.10),
        ("Honey Jar", 6.80), ("Granola Cereal", 5.30), ("Sparkling Water 12-pack", 8.40),
        ("Dark Chocolate Bar", 3.20),
    ],
}

FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
               "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
               "Thomas", "Sarah", "Charles", "Karen", "Amit", "Priya", "Wei", "Yuki", "Carlos",
               "Sofia", "Hans", "Marie", "Ahmed", "Fatima", "Liam", "Olivia", "Noah", "Emma"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Wilson", "Anderson", "Taylor", "Thomas", "Moore", "Jackson",
              "Sharma", "Patel", "Wang", "Tanaka", "Silva", "Muller", "Dubois", "Khan", "Kim", "Lee"]

N_CUSTOMERS = 850
CUSTOMER_IDS = [f"CUST-{i:05d}" for i in range(1, N_CUSTOMERS + 1)]
CUSTOMER_NAMES = {cid: f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}" for cid in CUSTOMER_IDS}
# give each customer a fixed segment & region for realistic repeat-purchase behavior
CUSTOMER_SEGMENT = {cid: random.choice(SEGMENTS) for cid in CUSTOMER_IDS}
CUSTOMER_REGION = {cid: random.choice(list(REGIONS.keys())) for cid in CUSTOMER_IDS}

START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2024, 12, 31)
DATE_RANGE_DAYS = (END_DATE - START_DATE).days

# ---------------------------------------------------------------------------
# Build product catalog with IDs
# ---------------------------------------------------------------------------
products = []
pid = 1000
for cat, items in CATEGORIES.items():
    for name, price in items:
        products.append({"ProductID": f"PRD-{pid}", "ProductName": name, "Category": cat, "UnitPrice": price})
        pid += 1
products_df = pd.DataFrame(products)


def random_date_with_seasonality():
    """Skew order volume upward in Nov/Dec (holiday season) for realism."""
    day_offset = np.random.randint(0, DATE_RANGE_DAYS + 1)
    d = START_DATE + timedelta(days=day_offset)
    # 35% chance to nudge the date into a holiday month to create a seasonal spike
    if random.random() < 0.15:
        year = random.choice([2023, 2024])
        month = random.choice([11, 12])
        day = random.randint(1, 28)
        d = datetime(year, month, day)
    return d


def random_growth_weight(order_date):
    """Slight upward revenue trend over time (~1.5% per month) for a believable growth story."""
    months_since_start = (order_date.year - START_DATE.year) * 12 + (order_date.month - START_DATE.month)
    return 1 + (months_since_start * 0.012)


rows = []
order_id_counter = 100000

for _ in range(N_ORDERS):
    order_id_counter += 1
    order_date = random_date_with_seasonality()
    cust_id = random.choice(CUSTOMER_IDS)
    region = CUSTOMER_REGION[cust_id]
    country = random.choice(REGIONS[region])
    segment = CUSTOMER_SEGMENT[cust_id]

    # each order has 1-4 line items (different products)
    n_items = np.random.choice([1, 2, 3, 4], p=[0.55, 0.25, 0.13, 0.07])
    chosen_products = products_df.sample(n=n_items, replace=False)

    for _, prod in chosen_products.iterrows():
        quantity = int(np.random.choice([1, 2, 3, 4, 5, 6], p=[0.35, 0.25, 0.15, 0.12, 0.08, 0.05]))
        # returns / cancellations show up as negative quantity ~1.5% of the time
        if random.random() < 0.015:
            quantity = -abs(quantity)

        discount = float(np.random.choice([0, 0, 0, 0.05, 0.1, 0.15, 0.2], p=[0.5, 0.1, 0.1, 0.1, 0.1, 0.05, 0.05]))
        growth = random_growth_weight(order_date)
        unit_price = round(prod["UnitPrice"] * growth * np.random.uniform(0.97, 1.03), 2)
        sales = round(unit_price * quantity * (1 - discount), 2)
        cost_ratio = np.random.uniform(0.55, 0.75)  # cost as % of unit price
        profit = round(sales - (unit_price * quantity * cost_ratio), 2)

        ship_mode = random.choice(SHIP_MODES)
        ship_days = {"Same Day": 0, "First Class": 2, "Second Class": 4, "Standard Class": 6}[ship_mode]
        ship_date = order_date + timedelta(days=ship_days + random.randint(0, 2))

        rows.append({
            "OrderID": f"ORD-{order_id_counter}",
            "OrderDate": order_date.strftime("%Y-%m-%d"),
            "ShipDate": ship_date.strftime("%Y-%m-%d"),
            "ShipMode": ship_mode,
            "CustomerID": cust_id,
            "CustomerName": CUSTOMER_NAMES[cust_id],
            "Segment": segment,
            "Region": region,
            "Country": country,
            "ProductID": prod["ProductID"],
            "ProductName": prod["ProductName"],
            "Category": prod["Category"],
            "Quantity": quantity,
            "UnitPrice": unit_price,
            "Discount": discount,
            "Sales": sales,
            "Profit": profit,
        })

df = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Inject realistic messiness for the cleaning exercise
# ---------------------------------------------------------------------------

# 1. Duplicate ~1.5% of rows exactly
dupe_idx = df.sample(frac=0.015, random_state=RANDOM_SEED).index
df = pd.concat([df, df.loc[dupe_idx]], ignore_index=True)

# 2. Missing values scattered across several columns
for col, frac in [("CustomerName", 0.01), ("Discount", 0.02), ("ShipMode", 0.015), ("Region", 0.008)]:
    idx = df.sample(frac=frac, random_state=RANDOM_SEED + 1).index
    df.loc[idx, col] = np.nan

# 3. Inconsistent text casing / stray whitespace on category & segment
inconsistent_idx = df.sample(frac=0.05, random_state=RANDOM_SEED + 2).index
df.loc[inconsistent_idx, "Category"] = df.loc[inconsistent_idx, "Category"].str.upper()
inconsistent_idx2 = df.sample(frac=0.05, random_state=RANDOM_SEED + 3).index
df.loc[inconsistent_idx2, "Segment"] = df.loc[inconsistent_idx2, "Segment"].apply(lambda x: f"  {x.lower()}  ")

# 4. A few mixed date formats (stringly typed) to force explicit parsing
mixed_date_idx = df.sample(frac=0.01, random_state=RANDOM_SEED + 4).index
def to_alt_format(d):
    dt = datetime.strptime(d, "%Y-%m-%d")
    return dt.strftime("%d/%m/%Y")
df.loc[mixed_date_idx, "OrderDate"] = df.loc[mixed_date_idx, "OrderDate"].apply(to_alt_format)

# 5. Shuffle row order so it doesn't look "too clean" chronologically
df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

# Save
import os
os.makedirs("data", exist_ok=True)
df.to_csv("data/sales_data_raw.csv", index=False)
print(f"Generated {len(df):,} rows -> data/sales_data_raw.csv")
print(df.head())
