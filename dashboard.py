import streamlit as st
from streamlit_option_menu import option_menu
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px
import os
import run_pipeline

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Abel AI Restaurant Intelligence",
    page_icon="🇪🇹",
    layout="wide"
)

# -----------------------------
# MODERN STYLING
# -----------------------------
st.markdown("""
<style>

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.block-container {
    padding-top: 1rem;
}

[data-testid="stMetricValue"] {
    font-size: 28px;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# TOP NAVIGATION BAR
# -----------------------------
selected = option_menu(
    menu_title="🇪🇹 Able AI",
    options=[
        "Overview",
        "Inventory",
        "Purchases",
        "Dish Analytics",
        "Competitor Intelligence",
        "AI Insights"
    ],
    icons=[
        "bar-chart",
        "box",
        "cart",
        "egg-fried",
        "globe",
        "robot"
    ],
    orientation="horizontal"
)

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

# -----------------------------
# DATABASE TABLES
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
            ingredient_name TEXT UNIQUE,
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
# LOAD DATA (CACHED FOR SPEED)
# -----------------------------
@st.cache_data(ttl=600)
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
# PIPELINE BUTTON
# -----------------------------
col1, col2 = st.columns([6,1])

with col2:
    if st.button("Run Pipeline"):
        run_pipeline.run_pipeline()
        st.success("Pipeline executed")

# =========================================================
# OVERVIEW
# =========================================================
if selected == "Overview":

    st.title("🇪🇹 Abel AI Restaurant Intelligence")
    st.caption("AI-Powered Inventory, Menu Analytics & Market Intelligence")

    st.divider()

    col1, col2, col3 = st.columns(3)

    col1.metric("📦 Ingredients", len(inventory))
    col2.metric("🧾 Purchases", len(purchases))

    if not inventory.empty:
        low_stock = len(inventory[inventory["quantity"] < 5])
    else:
        low_stock = 0

    col3.metric("⚠️ Low Stock", low_stock)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("📊 Menu Revenue")

        if not receipts.empty:

            chart = receipts.groupby("item_name")["revenue"].sum().reset_index()

            fig = px.bar(
                chart,
                x="item_name",
                y="revenue"
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("No sales data")

    with col2:

        st.subheader("💰 Supplier Spending")

        if not purchases.empty:

            chart = purchases.groupby("item_name")["cost"].sum().reset_index()

            fig = px.bar(
                chart,
                x="item_name",
                y="cost"
            )

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("No purchase data")

# =========================================================
# INVENTORY
# =========================================================
elif selected == "Inventory":

    st.title("📦 Inventory")

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

# =========================================================
# PURCHASES
# =========================================================
elif selected == "Purchases":

    st.title("🧾 Supplier Purchases")

    if not purchases.empty:

        chart = purchases.groupby("item_name")["quantity"].sum().reset_index()

        fig = px.bar(
            chart,
            x="item_name",
            y="quantity",
            title="Purchase Volume by Ingredient"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(purchases)

    else:
        st.info("No purchases recorded")

# =========================================================
# DISH ANALYTICS
# =========================================================
elif selected == "Dish Analytics":

    st.title("🍽 Dish Analytics")

    if not receipts.empty:

        df = receipts.groupby("item_name")["revenue"].sum().reset_index()

        fig = px.bar(
            df,
            x="item_name",
            y="revenue",
            title="Revenue by Dish"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df)

    else:
        st.info("No sales data available")

# =========================================================
# COMPETITOR INTELLIGENCE
# =========================================================
elif selected == "Competitor Intelligence":

    import plotly.express as px
    from google_reviews_scraper import scrape_google_reviews

    st.title("🌍 Competitor Intelligence")

    st.caption(
        "Market intelligence based on nearby Ethiopian restaurants"
    )

    st.divider()

    if st.button("Run Market Analysis"):

        with st.spinner("Collecting competitor data..."):

            data = scrape_google_reviews()

        restaurants = data["restaurants"]
        dishes = data["dishes"]

        # ------------------------------------------------
        # COMPETITOR MAP
        # ------------------------------------------------

        st.subheader("📍 Competitor Map")

        if not restaurants.empty:

            fig = px.scatter_mapbox(
                restaurants,
                lat="lat",
                lon="lon",
                hover_name="Restaurant",
                hover_data=["Rating"],
                size="Rating",
                zoom=12,
                height=500,
            )

            fig.update_layout(mapbox_style="open-street-map")

            st.plotly_chart(fig, use_container_width=True)

        else:

            st.warning("No competitor location data found")

        st.divider()

        # ------------------------------------------------
        # DEMAND HEATMAP
        # ------------------------------------------------

        st.subheader("🔥 Ethiopian Food Demand Heatmap")

        if not restaurants.empty:

            heatmap = px.density_mapbox(
                restaurants,
                lat="lat",
                lon="lon",
                z="demand",
                radius=30,
                zoom=11,
                height=500,
            )

            heatmap.update_layout(mapbox_style="open-street-map")

            st.plotly_chart(heatmap, use_container_width=True)

        else:

            st.warning("No demand data available")

        st.divider()

        # ------------------------------------------------
        # RESTAURANT TABLE
        # ------------------------------------------------

        st.subheader("🏪 Competitor Restaurants")

        st.dataframe(restaurants, use_container_width=True)

        st.divider()

        # ------------------------------------------------
        # POPULAR DISHES
        # ------------------------------------------------

        st.subheader("🍽 Popular Dishes in Reviews")

        if not dishes.empty:

            fig = px.bar(
                dishes,
                x="dish",
                y="mentions",
                title="Dish Mentions in Reviews",
            )

            st.plotly_chart(fig, use_container_width=True)

        else:

            st.info("No dish mentions detected")

        st.divider()

        # ------------------------------------------------
        # AI MENU OPPORTUNITY
        # ------------------------------------------------

        st.subheader("🤖 AI Menu Opportunity")

        if not dishes.empty:

            top_dish = dishes.sort_values(
                "mentions", ascending=False
            ).iloc[0]["dish"]

            st.success(
                f"High demand detected for **{top_dish.title()}** nearby. "
                f"Consider adding it to your menu."
            )

        else:

            st.info("Not enough data for recommendations")


# =========================================================
# AI INSIGHTS
# =========================================================
elif selected == "AI Insights":

    st.title("🤖 AI Restaurant Insights")

    if not receipts.empty:

        top_sales = receipts.groupby("item_name")["quantity"].sum().sort_values(ascending=False)

        best_dish = top_sales.index[0]

        st.success(f"Top selling dish: {best_dish}")

        st.bar_chart(top_sales)

    else:

        st.info("AI insights will appear after data is loaded")
