import streamlit as st
from streamlit_option_menu import option_menu
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px
import google_reviews_scraper
import os

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Able AI Restaurant Intelligence",
    page_icon="🇪🇹",
    layout="wide"
)

# -----------------
# for iphone app
# ---------------
st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" 
content="black">
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
# ETHIOPIAN THEME CSS
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
box-shadow:0px 0px 10px rgba(0,0,0,0.3);
}

.block-container{
padding-top:2rem;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# DATABASE
# -----------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS purchases (
            id SERIAL PRIMARY KEY,
            item_name TEXT,
            quantity INTEGER,
            price FLOAT,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.commit()
# -----------------------------
# SCRAPER CACHE
# -----------------------------

@st.cache_data(ttl=3600)
def get_competitor_data():
    return google_reviews_scraper.scrape_google_reviews()

# -----------------------------
# LOAD DATA
# -----------------------------

@st.cache_data(ttl=60)
def load_data():

    invoices = pd.read_sql("""
        SELECT item_name as item, quantity, price
        FROM purchases
    """, engine)

    receipts = pd.read_sql("""
        SELECT item_name as item, quantity, price
        FROM receipts
    """, engine)

    inventory = pd.read_sql("""
        SELECT
        i.ingredient_name,
        inv.quantity,
        i.unit
        FROM inventory inv
        JOIN ingredients i
        ON inv.ingredient_id = i.ingredient_id
    """, engine)

    return invoices, receipts, inventory


invoices, receipts, inventory = load_data()

# calculations
receipts["revenue"] = receipts["price"] * receipts["quantity"]
invoices["cost"] = invoices["price"] * invoices["quantity"]

# -----------------------------
# METRICS
# -----------------------------

total_ingredients = len(inventory)
total_purchases = len(invoices)
low_stock = len(inventory[inventory["quantity"] < 5])

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
# INDEX START FROM 1
# -----------------------------

def reset_index(df):
    df = df.copy()
    df.index = df.index + 1
    return df

# -----------------------------
# OVERVIEW TAB
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

        chart = receipts.groupby("item")["revenue"].sum().sort_values()

        st.bar_chart(chart)

    with col2:

        st.subheader("Supplier Spending")

        chart = invoices.groupby("item")["cost"].sum().sort_values()

        st.bar_chart(chart)

    st.divider()

    st.subheader("Recent Sales")

    st.dataframe(reset_index(receipts.tail(10)), use_container_width=True)

    st.divider()

    # -----------------------------
    # ETHIOPIAN RESTAURANT MAP
    # -----------------------------

    st.subheader("🌍 Ethiopian Restaurant Intelligence Map")

    results = get_competitor_data()

    restaurants = results["restaurants"]

    if "lat" in restaurants.columns:

        fig = px.scatter_mapbox(
            restaurants,
            lat="lat",
            lon="lng",
            hover_name="name",
            hover_data=["rating"],
            zoom=12,
            height=500
        )

        fig.update_layout(mapbox_style="open-street-map")

        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# INVENTORY TAB
# -----------------------------

elif selected == "Inventory":

    st.title("Inventory Intelligence")

    st.subheader("Ingredient Stock Levels")

    fig = px.bar(
        inventory,
        x="ingredient_name",
        y="quantity",
        color="quantity"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Inventory Table")

    st.dataframe(reset_index(inventory), use_container_width=True)

# -----------------------------
# PURCHASE TAB
# -----------------------------

elif selected == "Purchases":

    st.title("Supplier Purchases")

    st.subheader("Purchase Volume")

    chart = invoices.groupby("item")["quantity"].sum()

    st.bar_chart(chart)

    st.divider()

    st.subheader("Invoices Table")

    st.dataframe(reset_index(invoices), use_container_width=True)

# -----------------------------
# DISH ANALYTICS
# -----------------------------

elif selected == "Dish Analytics":

    st.title("Menu Performance")

    revenue_chart = receipts.groupby("item")["revenue"].sum()

    fig = px.bar(
        revenue_chart,
        title="Menu Revenue"
    )

    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# COMPETITOR INTELLIGENCE
# -----------------------------

elif selected == "Competitor Intelligence":

    st.header("Competitor Restaurant Intelligence")

    with st.spinner("Collecting Google restaurant intelligence..."):

        results = get_competitor_data()

    restaurants = results["restaurants"]
    dishes = results["dishes"]

    st.subheader("Top Ethiopian Restaurants")

    st.dataframe(reset_index(restaurants), use_container_width=True)

    st.subheader("Most Mentioned Dishes")

    st.bar_chart(dishes.set_index("dish"))

# -----------------------------
# AI INTELLIGENCE
# -----------------------------

elif selected == "AI Intelligence":

    st.header("🤖 AI Restaurant Insights")

    # AI TEXT INSIGHTS FIRST

    st.subheader("Key Insights")

    top_sales = receipts.groupby("item")["quantity"].sum().sort_values(ascending=False)

    best_dish = top_sales.index[0]

    st.success(f"🔥 Top Selling Dish: **{best_dish}**")

    low_stock_items = inventory[inventory["quantity"] < 5]

    if len(low_stock_items) > 0:

        st.warning("⚠ Some ingredients require reordering")

        st.write(low_stock_items["ingredient_name"].tolist())

    else:

        st.success("Inventory levels healthy")

    st.divider()

    # GRAPH AT BOTTOM

    st.subheader("Dish Sales Intelligence")

    st.bar_chart(top_sales)
