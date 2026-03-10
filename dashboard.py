import streamlit as st
from streamlit_option_menu import option_menu
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px
import os
import subprocess

# optional scraper import
try:
    import google_reviews_scraper
    SCRAPER_AVAILABLE = True
except:
    SCRAPER_AVAILABLE = False

# optional pipeline import
try:
    from run_pipeline import run_pipeline
    PIPELINE_AVAILABLE = True
except:
    PIPELINE_AVAILABLE = False


# -----------------------------
# INSTALL PLAYWRIGHT BROWSER
# -----------------------------

def install_playwright():
    try:
        subprocess.run(
            ["playwright", "install", "chromium"],
            check=False
        )
    except:
        pass

install_playwright()


# -----------------------------
# PAGE CONFIG
# -----------------------------

st.set_page_config(
    page_title="Able AI Restaurant Intelligence",
    page_icon="🇪🇹",
    layout="wide"
)


# -----------------------------
# IPHONE APP META
# -----------------------------

st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
<meta name="apple-mobile-web-app-title" content="Abel AI">

<link rel="apple-touch-icon"
href="https://cdn-icons-png.flaticon.com/512/4712/4712109.png">

<style>
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# ETHIOPIAN THEME
# -----------------------------

st.markdown("""
<style>

body {
    background-color:#0E1117;
}

h1,h2,h3,h4{
color:#FCD116;
}

.metric-card{
background-color:#161B22;
padding:20px;
border-radius:12px;
border-left:6px solid #078930;
}

</style>
""", unsafe_allow_html=True)


# -----------------------------
# DATABASE
# -----------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)


def initialize_database():

    with engine.connect() as conn:

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS purchases (
            id SERIAL PRIMARY KEY,
            item_name TEXT,
            quantity INTEGER,
            price FLOAT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS receipts (
            id SERIAL PRIMARY KEY,
            item_name TEXT,
            quantity INTEGER,
            price FLOAT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ingredients (
            ingredient_id SERIAL PRIMARY KEY,
            ingredient_name TEXT,
            unit TEXT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory (
            inventory_id SERIAL PRIMARY KEY,
            ingredient_id INTEGER,
            quantity FLOAT
        )
        """))

        conn.commit()


initialize_database()


# -----------------------------
# RUN PIPELINE
# -----------------------------

if PIPELINE_AVAILABLE:

    try:
        run_pipeline()
    except Exception as e:
        st.warning("Pipeline error: " + str(e))


# -----------------------------
# SCRAPER CACHE
# -----------------------------

@st.cache_data(ttl=3600)
def get_competitor_data():

    if not SCRAPER_AVAILABLE:
        return {"restaurants": pd.DataFrame(), "dishes": pd.DataFrame()}

    try:
        return google_reviews_scraper.scrape_google_reviews()
    except:
        return {"restaurants": pd.DataFrame(), "dishes": pd.DataFrame()}


# -----------------------------
# LOAD DATA SAFELY
# -----------------------------

@st.cache_data(ttl=60)
def load_data():

    try:
        invoices = pd.read_sql("""
        SELECT item_name as item, quantity, price
        FROM purchases
        """, engine)
    except:
        invoices = pd.DataFrame(columns=["item","quantity","price"])

    try:
        receipts = pd.read_sql("""
        SELECT item_name as item, quantity, price
        FROM receipts
        """, engine)
    except:
        receipts = pd.DataFrame(columns=["item","quantity","price"])

    try:
        inventory = pd.read_sql("""
        SELECT
        i.ingredient_name,
        inv.quantity,
        i.unit
        FROM inventory inv
        JOIN ingredients i
        ON inv.ingredient_id = i.ingredient_id
        """, engine)
    except:
        inventory = pd.DataFrame(columns=["ingredient_name","quantity","unit"])

    return invoices, receipts, inventory


invoices, receipts, inventory = load_data()


# -----------------------------
# SAFE CALCULATIONS
# -----------------------------

if not receipts.empty:
    receipts["revenue"] = receipts["price"] * receipts["quantity"]

if not invoices.empty:
    invoices["cost"] = invoices["price"] * invoices["quantity"]


# -----------------------------
# METRICS
# -----------------------------

total_ingredients = len(inventory)
total_purchases = len(invoices)

if not inventory.empty:
    low_stock = len(inventory[inventory["quantity"] < 5])
else:
    low_stock = 0


# -----------------------------
# SIDEBAR
# -----------------------------

with st.sidebar:

    selected = option_menu(
        "🇪🇹 Abel AI",
        ["Overview","Inventory","Purchases","Dish Analytics","Competitor Intelligence","AI Intelligence"],
        icons=["bar-chart","box","receipt","egg-fried","geo","robot"],
        default_index=0
    )


# -----------------------------
# RESET INDEX
# -----------------------------

def reset_index(df):

    df = df.copy()
    df.index = df.index + 1
    return df


# -----------------------------
# OVERVIEW
# -----------------------------

if selected == "Overview":

    st.title("🇪🇹 Abel AI Restaurant Intelligence")

    col1,col2,col3 = st.columns(3)

    col1.metric("Ingredients", total_ingredients)
    col2.metric("Purchases", total_purchases)
    col3.metric("Low Stock Items", low_stock)

    st.divider()

    col1,col2 = st.columns(2)

    with col1:

        st.subheader("Top Menu Revenue")

        if not receipts.empty:

            chart = receipts.groupby("item")["revenue"].sum()

            st.bar_chart(chart)

        else:

            st.info("No sales data yet")

    with col2:

        st.subheader("Supplier Spending")

        if not invoices.empty:

            chart = invoices.groupby("item")["cost"].sum()

            st.bar_chart(chart)

        else:

            st.info("No purchase data yet")

    st.divider()

    st.subheader("Recent Sales")

    if not receipts.empty:

        st.dataframe(reset_index(receipts.tail(10)), use_container_width=True)

    else:

        st.info("No receipts yet")


# -----------------------------
# INVENTORY
# -----------------------------

elif selected == "Inventory":

    st.title("Inventory Intelligence")

    if not inventory.empty:

        fig = px.bar(
            inventory,
            x="ingredient_name",
            y="quantity"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(reset_index(inventory), use_container_width=True)

    else:

        st.info("Inventory data not available yet")


# -----------------------------
# PURCHASES
# -----------------------------

elif selected == "Purchases":

    st.title("Supplier Purchases")

    if not invoices.empty:

        chart = invoices.groupby("item")["quantity"].sum()

        st.bar_chart(chart)

        st.dataframe(reset_index(invoices), use_container_width=True)

    else:

        st.info("No purchases recorded")


# -----------------------------
# DISH ANALYTICS
# -----------------------------

elif selected == "Dish Analytics":

    st.title("Menu Performance")

    if not receipts.empty:

        revenue_chart = receipts.groupby("item")["revenue"].sum()

        fig = px.bar(revenue_chart)

        st.plotly_chart(fig)

    else:

        st.info("No menu sales data")


# -----------------------------
# COMPETITOR INTELLIGENCE
# -----------------------------

elif selected == "Competitor Intelligence":

    st.header("Competitor Restaurant Intelligence")

    results = get_competitor_data()

    restaurants = results["restaurants"]
    dishes = results["dishes"]

    if not restaurants.empty:

        st.dataframe(reset_index(restaurants), use_container_width=True)

    else:

        st.info("Competitor data unavailable")


# -----------------------------
# AI INSIGHTS
# -----------------------------

elif selected == "AI Intelligence":

    st.header("🤖 AI Restaurant Insights")

    if not receipts.empty:

        top_sales = receipts.groupby("item")["quantity"].sum().sort_values(ascending=False)

        best_dish = top_sales.index[0]

        st.success(f"🔥 Top Selling Dish: {best_dish}")

        st.bar_chart(top_sales)

    else:

        st.info("AI insights will appear once sales data is available")
