"""
build_report.py
----------------
Generates outputs/reports/Business_Insights_Report.pdf: a polished,
stakeholder-ready PDF summarizing KPIs, charts, and business insights from
the sales performance analysis.

Run from the project root (after scripts/run_analysis.py or the notebook
has produced outputs/kpis.json, outputs/insights.json, and outputs/figures/):
    python scripts/build_report.py
"""

import json
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable, Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle,
)

KPI_PATH = "outputs/kpis.json"
INSIGHTS_PATH = "outputs/insights.json"
FIG_DIR = "outputs/figures"
OUT_PATH = "outputs/reports/Business_Insights_Report.pdf"

NAVY = colors.HexColor("#1E3A8A")
BLUE = colors.HexColor("#2563EB")
SLATE = colors.HexColor("#334155")
LIGHT_BG = colors.HexColor("#F1F5F9")
BORDER = colors.HexColor("#CBD5E1")

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

with open(KPI_PATH) as f:
    kpis = json.load(f)
with open(INSIGHTS_PATH) as f:
    insights = json.load(f)

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
styles = getSampleStyleSheet()
styles.add(ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=26, textColor=NAVY,
                           spaceAfter=6, leading=30))
styles.add(ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=12, textColor=SLATE,
                           spaceAfter=4))
styles.add(ParagraphStyle("SectionHeading", parent=styles["Heading1"], fontSize=16, textColor=NAVY,
                           spaceBefore=18, spaceAfter=10, borderPadding=0))
styles.add(ParagraphStyle("SubHeading", parent=styles["Heading2"], fontSize=12.5, textColor=BLUE,
                           spaceBefore=12, spaceAfter=6))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=10.3, textColor=SLATE, leading=15))
styles.add(ParagraphStyle("InsightNum", parent=styles["Normal"], fontSize=10.3, textColor=colors.white,
                           alignment=1, leading=14))
styles.add(ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#64748B"),
                           alignment=1, spaceBefore=4, spaceAfter=14))
styles.add(ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#94A3B8")))

story = []

# ---------------------------------------------------------------------------
# Cover / header
# ---------------------------------------------------------------------------
story.append(Spacer(1, 10))
story.append(Paragraph("Sales Performance Analysis", styles["ReportTitle"]))
story.append(Paragraph("Business Insights Report", styles["Subtitle"]))
story.append(Paragraph(f"Prepared {date.today().strftime('%B %d, %Y')}  ·  Analysis period covers all orders in the dataset",
                        styles["Subtitle"]))
story.append(HRFlowable(width="100%", thickness=1.4, color=BLUE, spaceBefore=10, spaceAfter=18))

# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------
story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
exec_summary = (
    f"This report summarizes findings from an end-to-end analysis of the company's sales data, covering "
    f"data cleaning, exploratory analysis, KPI computation, and business recommendations. The business "
    f"generated <b>${kpis['total_revenue']:,.0f}</b> in total revenue and <b>${kpis['total_profit']:,.0f}</b> "
    f"in profit, a <b>{kpis['profit_margin_pct']:.1f}%</b> margin, across <b>{kpis['total_orders']:,}</b> orders "
    f"from <b>{kpis['total_customers']:,}</b> customers. <b>{kpis['top_category']}</b> is the leading product "
    f"category and <b>{kpis['top_region']}</b> is the strongest region. The sections below detail the KPIs, "
    f"supporting charts, and concrete recommendations for revenue growth and margin improvement."
)
story.append(Paragraph(exec_summary, styles["Body"]))
story.append(Spacer(1, 14))

# ---------------------------------------------------------------------------
# KPI grid (as a table styled like cards)
# ---------------------------------------------------------------------------
story.append(Paragraph("Key Performance Indicators", styles["SectionHeading"]))


def kpi_cell(label, value):
    return [
        Paragraph(f"<font size=8 color='#64748B'>{label}</font>", styles["Body"]),
        Paragraph(f"<font size=15 color='#1E3A8A'><b>{value}</b></font>", styles["Body"]),
    ]


kpi_items = [
    ("TOTAL REVENUE", f"${kpis['total_revenue']:,.0f}"),
    ("TOTAL PROFIT", f"${kpis['total_profit']:,.0f}"),
    ("PROFIT MARGIN", f"{kpis['profit_margin_pct']:.1f}%"),
    ("TOTAL ORDERS", f"{kpis['total_orders']:,}"),
    ("TOTAL CUSTOMERS", f"{kpis['total_customers']:,}"),
    ("AVG ORDER VALUE", f"${kpis['avg_order_value']:,.2f}"),
    ("UNITS SOLD", f"{kpis['total_units_sold']:,}"),
    ("REPEAT CUSTOMER RATE", f"{kpis['repeat_customer_rate_pct']:.1f}%"),
    ("RETURN RATE", f"{kpis['return_rate_pct']:.2f}%"),
    ("YoY REVENUE GROWTH", f"{kpis['yoy_revenue_growth_pct']:+.1f}%" if kpis.get("yoy_revenue_growth_pct") is not None else "n/a"),
    ("TOP CATEGORY", kpis["top_category"]),
    ("TOP REGION", kpis["top_region"]),
]

rows = [kpi_items[i:i + 3] for i in range(0, len(kpi_items), 3)]
table_data = []
for row in rows:
    table_data.append([kpi_cell(lbl, val) for lbl, val in row])

kpi_table = Table(table_data, colWidths=[2.15 * inch] * 3, rowHeights=[0.62 * inch] * len(table_data))
kpi_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
    ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
    ("INNERGRID", (0, 0), (-1, -1), 0.6, BORDER),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
]))
story.append(kpi_table)
story.append(Spacer(1, 6))
story.append(Paragraph(
    "Best order day of week: <b>%s</b>  ·  Top product: <b>%s</b>  ·  Month-over-month revenue growth: <b>%s</b>" % (
        kpis["best_day_of_week"], kpis["top_product"],
        f"{kpis['mom_revenue_growth_pct']:+.1f}%" if kpis.get("mom_revenue_growth_pct") is not None else "n/a",
    ), styles["Body"]))

story.append(PageBreak())

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
story.append(Paragraph("Visual Analysis", styles["SectionHeading"]))

chart_specs = [
    ("01_monthly_revenue_trend.png", "Figure 1. Monthly revenue and profit trend, showing a clear holiday-season spike and an upward year-over-year trajectory."),
    ("02_revenue_by_category.png", "Figure 2. Total revenue by product category."),
    ("03_top10_products.png", "Figure 3. Top 10 individual products by revenue."),
    ("04_revenue_by_region.png", "Figure 4. Revenue share by region."),
    ("05_segment_analysis.png", "Figure 5. Revenue and order count by customer segment."),
    ("06_discount_vs_margin.png", "Figure 6. Relationship between discount level and profit margin, by category."),
    ("07_orders_by_dayofweek.png", "Figure 7. Order volume by day of week."),
    ("08_customer_order_frequency.png", "Figure 8. Distribution of orders per customer (loyalty / repeat-purchase behavior)."),
]

MAX_W = 6.6 * inch
for i, (fname, caption) in enumerate(chart_specs):
    path = os.path.join(FIG_DIR, fname)
    if not os.path.exists(path):
        continue
    img = Image(path)
    ratio = img.imageHeight / float(img.imageWidth)
    img.drawWidth = MAX_W
    img.drawHeight = MAX_W * ratio
    story.append(img)
    story.append(Paragraph(caption, styles["Caption"]))
    if i % 2 == 1 and i != len(chart_specs) - 1:
        story.append(PageBreak())

story.append(PageBreak())

# ---------------------------------------------------------------------------
# Business insights
# ---------------------------------------------------------------------------
story.append(Paragraph("Business Insights", styles["SectionHeading"]))
story.append(Paragraph(
    "The following insights translate the KPIs and charts above into decision-ready takeaways.",
    styles["Body"]))
story.append(Spacer(1, 8))

for i, text in enumerate(insights, 1):
    row = Table(
        [[Paragraph(str(i), styles["InsightNum"]), Paragraph(text, styles["Body"])]],
        colWidths=[0.34 * inch, 6.1 * inch],
    )
    row.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), BLUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    story.append(row)
    story.append(Spacer(1, 4))

story.append(PageBreak())

# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
story.append(Paragraph("Recommendations", styles["SectionHeading"]))

recommendations = [
    ("Rebalance the discount strategy",
     f"Review discounts above 15% category-by-category -- the data shows they frequently erode margin "
     f"below a healthy threshold. Consider capping deep discounts on low-margin categories while "
     f"preserving them where they clearly drive incremental volume."),
    ("Double down on the top category and region",
     f"{kpis['top_category']} and {kpis['top_region']} are outperforming -- prioritize inventory, "
     f"marketing spend, and supplier negototiations there, while running a focused promotional "
     f"campaign for underperforming categories to lift their contribution."),
    ("Invest in customer retention",
     "Repeat customers are cheaper to serve and already make up a large share of revenue. "
     "A loyalty program, targeted win-back email campaigns for lapsed customers, and better "
     "post-purchase follow-up can further increase repeat-purchase rate."),
    ("Plan staffing and promotions around demand patterns",
     f"Order volume peaks on {kpis['best_day_of_week']}s and during the holiday season. Align "
     f"staffing, ad spend, and inventory replenishment schedules with these predictable demand "
     f"patterns to avoid stockouts and improve fulfillment speed."),
    ("Monitor the return rate as a quality signal",
     f"The current return rate ({kpis['return_rate_pct']:.2f}%) is healthy, but should be tracked "
     f"monthly by category/product -- a rising trend is often an early indicator of a quality or "
     f"listing-accuracy problem worth investigating before it affects customer trust."),
    ("Watch product concentration risk",
     "A small number of products account for a disproportionate share of revenue. Diversifying "
     "the catalog's revenue base (via bundling, cross-sell, or expanding adjacent product lines) "
     "would reduce reliance on any single SKU."),
]

for title, text in recommendations:
    story.append(Paragraph(title, styles["SubHeading"]))
    story.append(Paragraph(text, styles["Body"]))
    story.append(Spacer(1, 4))

story.append(Spacer(1, 16))
story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER, spaceBefore=6, spaceAfter=8))
story.append(Paragraph(
    "Generated as part of the Sales Performance Analysis Dashboard project. "
    "Full source code, the interactive dashboard, and this report's underlying data are available "
    "in the project's GitHub repository. Data used in this report is synthetic and was generated "
    "for demonstration purposes.",
    styles["Footer"]))

# ---------------------------------------------------------------------------
# Header/footer on every page
# ---------------------------------------------------------------------------

def draw_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.75 * inch, 0.5 * inch, "Sales Performance Analysis -- Business Insights Report")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(BORDER)
    canvas.line(0.75 * inch, 0.65 * inch, letter[0] - 0.75 * inch, 0.65 * inch)
    canvas.restoreState()


doc = SimpleDocTemplate(
    OUT_PATH, pagesize=letter,
    topMargin=0.75 * inch, bottomMargin=0.85 * inch,
    leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    title="Sales Performance Analysis - Business Insights Report",
    author="Sales Performance Analysis Dashboard Project",
)
doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
print(f"Saved -> {OUT_PATH}")
