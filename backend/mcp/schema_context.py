"""Compact static Customer360 schema context for the LLM.

Instead of calling list_tables/get_schema for every question, the agent embeds
this compact schema + relationships into the prompt. Schema discovery tools
remain available only as a fallback.
"""
from __future__ import annotations

# Tables with English names -> (purpose, primary key)
TABLES: dict[str, tuple[str, str]] = {
    "customers": ("customer master (no PII)", "Customer_ID"),
    "products": ("product master", "Product_ID"),
    "invoices": ("invoice header", "شماره فاکتور"),
    "sales": ("sales order lines (line-level)", "Sales_Line_ID"),
    "realized_costs": ("actual cost per sales line", "Cost_Record_ID"),
    "collections": ("collection / receivable events", "Collection_ID"),
    "complaints": ("customer complaints", "Complaint_ID"),
    "complaint_links": ("bridge complaint <-> sales line", "Complaint_ID + Sales_Line_ID"),
    "crm_interactions": ("CRM interactions (versioned)", "Interaction_ID + Record_Version"),
    "dev_requests": ("product development requests", "Request_ID"),
    "quality_labs": ("lab quality measurements per sales line", "Quality_Record_ID"),
    "hembaft_lots": ("hembaft <-> lot mapping", "Hembaft_Lot_Key"),
    "offers": ("commercial offers", "Offer_ID"),
    "wallet_share": ("customer wallet-share estimates per month", "Customer_ID + Month_Key"),
    "market_signals": ("market signals per week", "Week_ID"),
    "monthly_costs": ("estimated product-month cost (fallback)", "Estimate_ID"),
}

# Key columns per table (compact but enough to write correct SQL).
COLUMNS: dict[str, list[str]] = {
    "customers": ["Customer_ID", "Location_ID", "Customer_Segment", "Relationship_Start_Date",
                  "Credit_Limit", "Payment_Terms_Days", "Customer_Status", "Sales_Rep_ID"],
    "products": ["Product_ID", "Quality_Class_ID", "گروه کالا (product family)",
                 "دسته بندی براقیت (luster)", "گروه رنگ (color)", "زیرگروه کالا (denier)"],
    "invoices": ["شماره فاکتور (invoice no)", "تاریخ (date)", "Customer_ID", "ماه", "سال"],
    "sales": ["Sales_Line_ID", "شماره فاکتور (invoice no, FK)", "Customer_ID", "Product_ID",
              "تاریخ (date)", "نوع پرداخت (payment type)", "مقدار (quantity)",
              "قیمت فی فروش (unit price)", "مبلغ کل (total amount)", "گروه کالا (family)",
              "Lot_ID", "Hembaft_Lot_Key"],
    "realized_costs": ["Cost_Record_ID", "Sales_Line_ID", "Product_ID", "شماره فاکتور",
                       "هزینه کل به ازای واحد (actual unit cost)", "مقدار برگشتی", "مبلغ برگشتی"],
    "collections": ["Collection_ID", "Customer_ID", "شماره فاکتور", "تاریخ فاکتور",
                    "تاریخ سررسید (due)", "تاریخ رویداد وصول (collected)", "مبلغ وصول",
                    "روز تأخیر (delay days)", "چک برگشتی (bounced check)"],
    "complaints": ["Complaint_ID", "Customer_ID", "Product_ID", "گروه کالا", "Complaint_Title",
                   "Complaint_Text", "Severity", "Created_At", "Complaint_Status", "Resolved_At"],
    "complaint_links": ["Complaint_ID", "Sales_Line_ID", "Customer_ID", "Product_ID",
                        "Purchase_Date", "مقدار", "مقدار برگشتی", "Complaint_Result"],
    "crm_interactions": ["Interaction_ID", "Record_Version", "Customer_ID", "Product_ID",
                         "Event_Time", "Interaction_Type", "Summary_Text", "Next_Action",
                         "Record_Status", "Sales_Rep_ID"],
    "dev_requests": ["Request_ID", "Customer_ID", "Product_ID", "Created_At", "Request_Type",
                     "Requirement_Text", "Priority", "Status", "Outcome_Text"],
    "quality_labs": ["Quality_Record_ID", "Sales_Line_ID", "Lot_ID", "Product_ID",
                     "Production_Date", "Tensile_Strength_cN_dtex", "Elongation_Pct",
                     "Evenness_CV_Pct", "Oil_Pickup_Pct", "Sample_Count", "Lab_Result"],
    "hembaft_lots": ["Hembaft_Lot_Key", "Hembaft_ID", "Lot_ID", "Product_ID", "First_Observed_Date"],
    "offers": ["Offer_ID", "Customer_ID", "Product_ID", "Offer_Date", "گروه کالا",
               "Base_Price_per_unit", "Offered_Price_per_unit", "Offer_Discount_Pct",
               "Offer_Type", "Validity_Days", "Offer_Reason", "Result", "Decision_At"],
    "wallet_share": ["Customer_ID", "Month_Key", "Estimated_Total_Purchase", "Nafis_Purchase",
                     "Main_Competitor", "Estimate_Source"],
    "market_signals": ["Week_ID", "Report_Date", "Product_Market", "Customer_ID", "Competitor",
                       "Customer_Signal", "Price_Index", "Demand_Change", "Market_Trend"],
    "monthly_costs": ["Estimate_ID", "Product_ID", "Month_Key", "هزینه کل برآوردی به ازای واحد (estimated unit cost)"],
}

# Relationships (table.column -> referenced table.column)
RELATIONSHIPS: list[tuple[str, str]] = [
    ("sales.Customer_ID", "customers.Customer_ID"),
    ("invoices.Customer_ID", "customers.Customer_ID"),
    ("collections.Customer_ID", "customers.Customer_ID"),
    ("complaints.Customer_ID", "customers.Customer_ID"),
    ("crm_interactions.Customer_ID", "customers.Customer_ID"),
    ("dev_requests.Customer_ID", "customers.Customer_ID"),
    ("offers.Customer_ID", "customers.Customer_ID"),
    ("wallet_share.Customer_ID", "customers.Customer_ID"),
    ("market_signals.Customer_ID", "customers.Customer_ID"),
    ("sales.Product_ID", "products.Product_ID"),
    ("complaints.Product_ID", "products.Product_ID"),
    ("quality_labs.Product_ID", "products.Product_ID"),
    ("offers.Product_ID", "products.Product_ID"),
    ("sales.شماره فاکتور", "invoices.شماره فاکتور"),
    ("collections.شماره فاکتور", "invoices.شماره فاکتور"),
    ("realized_costs.Sales_Line_ID", "sales.Sales_Line_ID"),
    ("quality_labs.Sales_Line_ID", "sales.Sales_Line_ID"),
    ("complaint_links.Sales_Line_ID", "sales.Sales_Line_ID"),
    ("complaint_links.Complaint_ID", "complaints.Complaint_ID"),
    ("sales.Hembaft_Lot_Key", "hembaft_lots.Hembaft_Lot_Key"),
    ("quality_labs.Hembaft_Lot_Key", "hembaft_lots.Hembaft_Lot_Key"),
]

BUSINESS_RULES = """RULES:
- Actual cost > estimated cost (realized_costs vs monthly_costs).
- Customer_ID links all customer tables. CRM: use latest Record_Version per Interaction_ID.
- Hembaft_ID != Lot_ID; link via Hembaft_Lot_Key only. As-of: usable from Available_At.
- ORDERS vs LINES vs UNITS: COUNT(DISTINCT "شماره فاکتور")=orders, COUNT(*)=lines, SUM("مقدار")=units. Never double-count orders from multi-line/joins.
- DATES are TEXT ('YYYY-MM-DD') -> CAST(col AS DATE) for date math; 'ماه'/'سال' are labels (M01..SY06), not dates.
- DuckDB: use strftime(x,'%Y-%m') (NOT to_char); single quotes for strings, double for identifiers.
- Persian YES/NO columns are VARCHAR, NOT integers. E.g. 'چک برگشتی' (collections) holds 'بله'/'خیر' — filter as WHERE "چک برگشتی" = 'بله'. Never cast a text column to INT or compare it to a number.
"""


def build_schema_context() -> str:
    """Render a compact static schema description for the LLM prompt."""
    lines = ["## Customer360 schema (static)", ""]
    for table, (purpose, pk) in TABLES.items():
        cols = ", ".join(COLUMNS.get(table, []))
        lines.append(f"- {table} | PK {pk} | {purpose} | {cols}")
    lines.append("")
    lines.append("## Links")
    for a, b in RELATIONSHIPS:
        lines.append(f"- {a} -> {b}")
    lines.append("")
    lines.append(BUSINESS_RULES.strip())
    return "\n".join(lines)


CUSTOMER360_SCHEMA = build_schema_context()
CUSTOMER360_RELATIONSHIPS = "\n".join(f"- {a} -> {b}" for a, b in RELATIONSHIPS)
