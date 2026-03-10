import pandas as pd
import psycopg2


def calculate_inventory():

    conn = psycopg2.connect(
        dbname="inventory_ai",
        user="postgres",
        password="postgres123",
        host="localhost",
        port="5432"
    )

    purchases = pd.read_sql("SELECT item_name, quantity, price FROM purchases", conn)
    receipts = pd.read_sql("SELECT item_name, quantity, created_at, price FROM receipts", conn)

    conn.close()

    purchase_summary = purchases.groupby("item_name").agg({
        "quantity":"sum",
        "price":"mean"
    }).reset_index()

    receipt_summary = receipts.groupby("item_name").agg({
        "quantity":"sum",
        "price":"mean"
    }).reset_index()

    inventory = pd.merge(
        purchase_summary,
        receipt_summary,
        on="item_name",
        how="outer",
        suffixes=("_purchase","_sale")
    ).fillna(0)

    inventory["inventory"] = inventory["quantity_purchase"] - inventory["quantity_sale"]

    inventory["revenue"] = inventory["quantity_sale"] * inventory["price_sale"]

    inventory["cost"] = inventory["quantity_purchase"] * inventory["price_purchase"]

    inventory["profit"] = inventory["revenue"] - inventory["cost"]

    return inventory
