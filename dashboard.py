import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine
import run_pipeline

from google_reviews_scraper import scrape_google_reviews


# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------

st.set_page_config(
    page_title="Able AI Restaurant Intelligence",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# IPHONE FULLSCREEN SUPPORT
# -------------------------------------------------

st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black">
<meta name="apple-mobile-web-app-title" content="Able AI">
<meta name="viewport" content="width=device-width, initial-scale=1">
""", unsafe_allow_html=True)

# -------------------------------------------------
# MOBILE UI
# -------------------------------------------------

st.markdown("""
<style>

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

.block-container{
padding-top:1rem;
max-width:650px;
}

[data-testid="metric-container"]{
background-color:#111;
border-radius:12px;
padding:15px;
border:1px solid #333;
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# RUN PIPELINE
# -------------------------------------------------

if "pipeline_ran" not in st.session_state:

    with st.spinner("Updating restaurant data..."):
        run_pipeline.run_pipeline()

    st.session_state.pipeline_ran = True


# -------------------------------------------------
# DATABASE
# -------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

# -------------------------------------------------
# DATA LOADERS
# -------------------------------------------------

@st.cache_data(ttl=120)
def load_menu():

    query = """
    SELECT
        m.item_name,
        SUM(s.orders) orders,
        SUM(s.revenue) revenue
    FROM menu_sales s
    JOIN menu_items m
    ON s.item_id = m.item_id
    GROUP BY m.item_name
    """

    return pd.read_sql(query, engine)


@st.cache_data(ttl=120)
def load_inventory():

    query = """
    SELECT
        i.ingredient_name,
        inv.quantity
    FROM inventory inv
    JOIN ingredients i
    ON inv.ingredient_id = i.ingredient_id
    """

    df = pd.read_sql(query, engine)

    # prevent negative display
    df["quantity"] = df["quantity"].clip(lower=0)

    return df


@st.cache_data(ttl=120)
def load_purchases():

    query = """
    SELECT
        ingredient_name,
        SUM(quantity) AS quantity,
        SUM(price) AS total_cost
    FROM purchases
    GROUP BY ingredient_name
    ORDER BY quantity DESC
    """

    df = pd.read_sql(query, engine)

    return df


# -------------------------------------------------
# COMPETITOR SCRAPER
# -------------------------------------------------

@st.cache_data(ttl=3600)

def load_competitors():

    restaurants = pd.read_sql(
        "SELECT * FROM competitors",
        engine
    )

    dishes = pd.read_sql(
        "SELECT * FROM competitor_dishes",
        engine
    )

    return restaurants, dishes
# -------------------------------------------------
# HEADER
# -------------------------------------------------

st.markdown("# 🍽 Able AI Restaurant Intelligence")

# -------------------------------------------------
# TABS
# -------------------------------------------------

tabs = st.tabs([
    "📊 Dashboard",
    "📦 Inventory",
    "🛒 Purchases",
    "🍽 Menu",
    "🏆 Competition",
    "🧠 AI Insights"
])

# =================================================
# DASHBOARD
# =================================================

with tabs[0]:

    menu = load_menu()

    revenue = menu["revenue"].sum()
    orders = menu["orders"].sum()

    col1, col2 = st.columns(2)

    col1.metric("Revenue", f"${revenue:,.0f}")
    col2.metric("Orders", int(orders))

    st.metric("Menu Items", menu["item_name"].nunique())

    fig = px.bar(
        menu,
        x="item_name",
        y="revenue",
        title="Revenue by Dish"
    )

    st.plotly_chart(fig, use_container_width=True, key="revenue_chart")


# =================================================
# INVENTORY
# =================================================

with tabs[1]:

    inventory = load_inventory()

    if inventory.empty:

        st.warning("No inventory data available")

    else:

        fig = px.bar(
            inventory,
            x="ingredient_name",
            y="quantity",
            title="Remaining Inventory"
        )

        st.plotly_chart(fig, use_container_width=True, key="inventory_chart")

        low_stock = inventory[inventory["quantity"] < 200]

        if not low_stock.empty:

            st.error("⚠ Low Inventory Warning")

            st.dataframe(low_stock)


# =================================================
# PURCHASES
# =================================================

with tabs[2]:

    purchases = load_purchases()

    if purchases.empty:

        st.info("No purchases found")

    else:

        fig = px.bar(
            purchases,
            x="ingredient_name",
            y="quantity",
            title="Purchased Ingredients"
        )

        st.plotly_chart(fig, use_container_width=True, key="purchases_chart")

        st.dataframe(purchases)


# =================================================
# MENU ANALYTICS
# =================================================

with tabs[3]:

    menu = load_menu()

    fig = px.bar(
        menu,
        x="item_name",
        y="orders",
        title="Most Popular Dishes"
    )

    st.plotly_chart(fig, use_container_width=True, key="menu_orders")


# =================================================
# COMPETITION INTELLIGENCE
# =================================================

with tabs[4]:

    st.subheader("Nearby Ethiopian Restaurant Intelligence")

    restaurants, dishes = load_competitors()

    if restaurants.empty:

        st.info("No competitor data available")

    else:

        st.markdown("### Competitor Ratings")

        fig = px.bar(
            restaurants,
            x="Restaurant",
            y="Rating",
            title="Top Rated Ethiopian Restaurants"
        )

        st.plotly_chart(fig, use_container_width=True, key="competitor_chart")

        st.dataframe(restaurants)

    if not dishes.empty:

        st.markdown("### Most Mentioned Ethiopian Dishes")

        fig2 = px.bar(
            dishes,
            x="dish",
            y="mentions",
            title="Dish Popularity From Reviews"
        )

        st.plotly_chart(fig2, use_container_width=True, key="dish_mentions")

        st.dataframe(dishes)

    if not restaurants.empty:

        st.markdown("### Restaurant Locations")

        map_df = restaurants.rename(
            columns={
                "lat": "latitude",
                "lon": "longitude"
            }
        )

        st.map(map_df)


# =================================================
# AI INSIGHTS
# =================================================

with tabs[5]:

    st.subheader("AI Restaurant Insights")

    menu = load_menu()
    inventory = load_inventory()
    restaurants, dishes = load_competitors()

    if not menu.empty:

        top = menu.sort_values("orders", ascending=False).iloc[0]

        st.success(
            f"🔥 {top['item_name']} is your most popular dish"
        )

    if not inventory.empty:

        low = inventory[inventory["quantity"] < 200]

        if not low.empty:

            st.warning(
                f"⚠ {low.iloc[0]['ingredient_name']} inventory running low"
            )

    if not dishes.empty:

        top_dish = dishes.sort_values(
            "mentions",
            ascending=False
        ).iloc[0]

        st.info(
            f"📈 Market demand: {top_dish['dish']} trending in competitor reviews"
        )

    revenue = menu["revenue"].sum()

    predicted = revenue * 1.12

    st.metric(
        "Predicted Revenue Next Month",
        f"${predicted:,.0f}"
    )