#!/usr/bin/env python3
"""Rebuild data/processed/customer_360.duckdb from data/raw/DATASET.xlsx.

Each sheet becomes one table (named in English). Also stores a _meta table with
per-table purpose and primary-key notes.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "data" / "raw" / "DATASET.xlsx"
DB_PATH = REPO / "data" / "processed" / "customer_360.duckdb"

TABLES = {
    "customers": "مشتریان",
    "products": "محصولات",
    "invoices": "فاکتورها",
    "sales": "فروش",
    "realized_costs": "اجزای_هزینه_تحقق",
    "collections": "وصول",
    "complaints": "شکایات",
    "complaint_links": "اتصال_شکایت",
    "crm_interactions": "تعاملات_CRM",
    "dev_requests": "درخواست_توسعه",
    "quality_labs": "کیفیت_لات",
    "hembaft_lots": "همبافت_لات",
    "offers": "آفرها",
    "wallet_share": "سهم_سبد",
    "market_signals": "سیگنال_بازار",
    "monthly_costs": "برآورد_هزینه_ماهانه",
}

PK = {
    "customers": "Customer_ID",
    "products": "Product_ID",
    "invoices": "شماره فاکتور",
    "sales": "Sales_Line_ID",
    "realized_costs": "Cost_Record_ID",
    "collections": "Collection_ID",
    "complaints": "Complaint_ID",
    "complaint_links": "Complaint_ID+Sales_Line_ID",
    "crm_interactions": "Interaction_ID+Record_Version",
    "dev_requests": "Request_ID",
    "quality_labs": "Quality_Record_ID",
    "hembaft_lots": "Hembaft_Lot_Key",
    "offers": "Offer_ID",
    "wallet_share": "Customer_ID+Month_Key",
    "market_signals": "Week_ID",
    "monthly_costs": "Estimate_ID",
}

PURPOSE = {
    "customers": "Customer master",
    "products": "Product master",
    "invoices": "Invoice header",
    "sales": "Sales lines",
    "realized_costs": "Realized cost per sales line",
    "collections": "Collection events",
    "complaints": "Complaints",
    "complaint_links": "Complaint <-> Sales bridge",
    "crm_interactions": "CRM interactions (versioned)",
    "dev_requests": "Product development requests",
    "quality_labs": "Lab quality measurements",
    "hembaft_lots": "Hembaft <-> Lot mapping",
    "offers": "Commercial offers",
    "wallet_share": "Customer wallet-share estimates",
    "market_signals": "Market signals",
    "monthly_costs": "Monthly estimated cost",
}


def main() -> None:
    xl = pd.ExcelFile(SRC)
    con = duckdb.connect(str(DB_PATH))
    for table, sheet in TABLES.items():
        df = xl.parse(sheet)
        con.register("tmp_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM tmp_df")
        con.unregister("tmp_df")
    con.execute("CREATE OR REPLACE TABLE _meta (table_name VARCHAR, purpose VARCHAR, pk VARCHAR)")
    for t, purpose, pk in zip(TABLES, PURPOSE.values(), PK.values()):
        con.execute("INSERT INTO _meta VALUES (?,?,?)", [t, purpose, pk])
    con.close()
    print(f"Rebuilt {DB_PATH} ({DB_PATH.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
