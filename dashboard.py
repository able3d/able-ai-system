import streamlit as st
from streamlit_option_menu import option_menu
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px
import os
import subprocess
from run_pipeline import run_pipeline
import run_pipeline

run_pipeline.run_pipeline()

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Abel AI Restaurant Intelligence",
    page_icon="🇪🇹",
    layout="wide"
)
# -----------------------------
# run pipeline
# ----------------------------

if st.button("Run Pipeline"):
    run_pipeline.run_pipeline()
    st.success("Pipeline executed")
# -----------------------------
# DATABASE CONNECTION
# -----------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("DATABASE_URL environment variable not set")
    st.stop()

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
# --------------------------

# -----------------------------
# CREATE TABLES
# -----------------------------
def initialize_database():

    with engine.begin() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS purchases(
            id SERIAL PRIMARY KEY,
            item_name TEXT,
            quantity INT,
            price FLOAT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS receipts(
            id SERIAL PRIMARY KEY,
            item_name TEXT,
            quantity INT,
            price FLOAT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ingredients(
            ingredient_id SERIAL PRIMARY KEY,
            ingredient_name TEXT,
            unit TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory(
            inventory_id SERIAL PRIMARY KEY,
            ingredient_id INT,
            quantity FLOAT
        )
        """))

initialize_database()


# -----------------------------
# SAFE DATA LOADER
# -----------------------------
def load_data():

    try:
        purchases = pd.read_sql("SELECT * FROM purchases", engine)
    except:
        purchases = pd.DataFrame(columns=["item_name","quantity","price"])

    try:
        receipts = pd.read_sql("SELECT * FROM receipts", engine)
    except:
        receipts = pd.DataFrame(columns=["item_name","quantity","price"])

    try:
        inventory = pd.read_sql("""
        SELECT i.ingredient_name, inv.quantity
        FROM inventory inv
        JOIN ingredients i
        ON inv.ingredient_id = i.ingredient_id
        """, engine)
    except:
        inventory = pd.DataFrame(columns=["ingredient_name","quantity"])

    return purchases, receipts, inventory


purchases, receipts, inventory = load_data()


# -----------------------------
# DATA PROCESSING
# -----------------------------
if not receipts.empty:
    receipts["revenue"] = receipts["price"] * receipts["quantity"]

if not purchases.empty:
    purchases["cost"] = purchases["price"] * purchases["quantity"]


# -----------------------------
# SIDEBAR
# -----------------------------
with st.sidebar:

    selected = option_menu(
        "🇪🇹 Abel AI",
        [
            "Overview",
            "Inventory",
            "Purchases",
            "Dish Analytics",
            "AI Insights"
        ],
        icons=[
            "bar-chart",
            "box",
            "receipt",
            "egg-fried",
            "robot"
        ],
        default_index=0
    )


# -----------------------------
# OVERVIEW
# -----------------------------
if selected == "Overview":

    st.title("🇪🇹 Abel AI Restaurant Intelligence")

    col1, col2, col3 = st.columns(3)

    col1.metric("Ingredients", len(inventory))
    col2.metric("Purchases", len(purchases))

    if not inventory.empty:
        low_stock = len(inventory[inventory["quantity"] < 5])
    else:
        low_stock = 0

    col3.metric("Low Stock", low_stock)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Menu Revenue")

        if not receipts.empty:
            chart = receipts.groupby("item_name")["revenue"].sum()
            st.bar_chart(chart)
        else:
            st.info("No sales data")

    with col2:

        st.subheader("Supplier Spending")

        if not purchases.empty:
            chart = purchases.groupby("item_name")["cost"].sum()
            st.bar_chart(chart)
        else:
            st.info("No purchase data")


# -----------------------------
# INVENTORY
# -----------------------------
elif selected == "Inventory":

    st.title("Inventory")

    if not inventory.empty:

        fig = px.bar(
            inventory,
            x="ingredient_name",
            y="quantity"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(inventory)

    else:

        st.info("No inventory data yet")


# -----------------------------
# PURCHASES
# -----------------------------
elif selected == "Purchases":

    st.title("Supplier Purchases")

    if not purchases.empty:

        st.dataframe(purchases)

        chart = purchases.groupby("item_name")["quantity"].sum()

        st.bar_chart(chart)

    else:

        st.info("No purchases recorded")


# -----------------------------
# DISH ANALYTICS
# -----------------------------
elif selected == "Dish Analytics":

    st.title("Dish Analytics")

    if not receipts.empty:

        revenue_chart = receipts.groupby("item_name")["revenue"].sum()

        fig = px.bar(revenue_chart)

        st.plotly_chart(fig)

    else:

        st.info("No sales data available")


# -----------------------------
# AI INSIGHTS
# -----------------------------
elif selected == "AI Insights":

    st.title("AI Restaurant Insights")

    if not receipts.empty:

        top_sales = receipts.groupby("item_name")["quantity"].sum().sort_values(ascending=False)

        best_dish = top_sales.index[0]

        st.success(f"Top selling dish: {best_dish}")

        st.bar_chart(top_sales)

    else:

        st.info("AI insights will appear after data is loaded")
