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
# PWA / IPHONE FULLSCREEN SUPPORT
# -------------------------------------------------

st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Able AI">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/1046/1046784.png">
""", unsafe_allow_html=True)

# -------------------------------------------------
# UI STYLING
# -------------------------------------------------

st.markdown("""
<style>

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container{
    padding-top:1rem;
    max-width:700px;
}

[data-testid="metric-container"]{
    background-color:#111;
    border-radius:12px;
    padding:15px;
    border:1px solid #222;
}

button[kind="primary"]{
    width:100%;
    height:50px;
}

</style>
""", unsafe_allow_html=True)


# -------------------------------------------------
# RUN DATA PIPELINE
# -------------------------------------------------

if "pipeline_ran" not in st.session_state:

    with st.spinner("Updating restaurant data..."):

        run_pipeline.run_pipeline()

    st.session_state["pipeline_ran"] = True


# -------------------------------------------------
# DATABASE
# -------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


# -------------------------------------------------
# DATA LOADERS
# -------------------------------------------------

@st.cache_data(ttl=60)
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


@st.cache_data(ttl=60)
def load_inventory():

    query = """
    SELECT
        i.ingredient_name,
        inv.quantity AS remaining
    FROM inventory inv
    JOIN ingredients i
    ON inv.ingredient_id = i.ingredient_id
    """

    return pd.read_sql(query, engine)


@st.cache_data(ttl=60)
def load_purchases():

    return pd.read_sql("SELECT * FROM purchases", engine)


@st.cache_data(ttl=60)
def load_usage():

    query = """
    SELECT
        i.ingredient_name,
        SUM(b.quantity * s.orders) AS quantity_used
    FROM dish_bom b
    JOIN menu_sales s
    ON b.item_id = s.item_id
    JOIN ingredients i
    ON b.ingredient_id = i.ingredient_id
    GROUP BY i.ingredient_name
    """

    return pd.read_sql(query, engine)


@st.cache_data(ttl=3600)
def get_competitor_data():

    return scrape_google_reviews()


# -------------------------------------------------
# HEADER
# -------------------------------------------------

st.markdown(
"""
<h2 style='text-align:center;'>
🍽 Able AI Restaurant Intelligence
</h2>
""",
unsafe_allow_html=True
)


# -------------------------------------------------
# NAVIGATION
# -------------------------------------------------

tabs = st.tabs([
    "📊 Dashboard",
    "📦 Inventory",
    "🛒 Purchases",
    "🍽 Menu Analytics",
    "🧠 AI Insights",
    "🌍 Competitor Intelligence"
])


# =====================================================
# DASHBOARD
# =====================================================

with tabs[0]:

    menu = load_menu()

    col1, col2 = st.columns(2)

    col1.metric("Revenue", f"${menu['revenue'].sum():,.0f}")
    col2.metric("Orders", int(menu["orders"].sum()))

    st.metric("Menu Items", menu["item_name"].nunique())

    fig = px.bar(menu, x="item_name", y="revenue", title="Menu Revenue")

    st.plotly_chart(fig, use_container_width=True, key="dashboard_revenue")


# =====================================================
# INVENTORY
# =====================================================

with tabs[1]:

    inventory = load_inventory()

    if inventory.empty:

        st.info("No inventory data")

    else:

        fig = px.bar(
            inventory,
            x="ingredient_name",
            y="remaining",
            title="Remaining Inventory"
        )

        st.plotly_chart(fig, use_container_width=True, key="inventory_chart")

        low_stock = inventory[inventory["remaining"] < 500]

        if not low_stock.empty:

            st.warning("⚠ Low stock detected")

            st.dataframe(low_stock)

    usage = load_usage()

    if not usage.empty:

        fig = px.bar(
            usage,
            x="ingredient_name",
            y="quantity_used",
            title="Ingredient Usage"
        )

        st.plotly_chart(fig, use_container_width=True, key="usage_chart")


# =====================================================
# PURCHASES
# =====================================================

with tabs[2]:

    purchases = load_purchases()

    if purchases.empty:

        st.warning("No purchases found")

    else:

        fig = px.bar(
            purchases,
            x="ingredient_name",
            y="quantity",
            title="Purchased Ingredients"
        )

        st.plotly_chart(fig, use_container_width=True, key="purchases_chart")

        st.dataframe(purchases)


# =====================================================
# MENU ANALYTICS
# =====================================================

with tabs[3]:

    menu = load_menu()

    fig = px.bar(
        menu,
        x="item_name",
        y="orders",
        title="Most Popular Dishes"
    )

    st.plotly_chart(fig, use_container_width=True, key="menu_orders_chart")

    fig2 = px.bar(
        menu,
        x="item_name",
        y="revenue",
        title="Revenue by Dish"
    )

    st.plotly_chart(fig2, use_container_width=True, key="menu_revenue_chart")


# =====================================================
# AI INSIGHTS
# =====================================================

with tabs[4]:

    st.subheader("AI Restaurant Insights")

    menu = load_menu()
    inventory = load_inventory()

    if not menu.empty:

        top = menu.sort_values("orders", ascending=False).iloc[0]

        st.success(f"🔥 {top['item_name']} is your most popular dish")

    if not inventory.empty:

        low = inventory[inventory["remaining"] < 300]

        if not low.empty:

            st.error(
                f"⚠ {low.iloc[0]['ingredient_name']} may run out soon"
            )

    revenue = menu["revenue"].sum()

    if revenue < 1000:

        st.info(
            "💡 Consider combo meals to increase average order value"
        )

    if not menu.empty:

        predicted = menu["revenue"].mean() * 30

        st.metric(
            "Predicted Monthly Revenue",
            f"${predicted:,.0f}"
        )


# =====================================================
# COMPETITOR INTELLIGENCE
# =====================================================

with tabs[5]:

    st.subheader("Nearby Ethiopian Restaurants")

    if st.button("Run Market Analysis"):

        with st.spinner("Analyzing market..."):

            data = get_competitor_data()

        restaurants = data["restaurants"]
        dishes = data["dishes"]

        if not restaurants.empty:

            fig = px.scatter_mapbox(
                restaurants,
                lat="lat",
                lon="lon",
                hover_name="Restaurant",
                hover_data=["Rating"],
                size="Rating",
                zoom=12
            )

            fig.update_layout(mapbox_style="open-street-map")

            st.plotly_chart(fig, use_container_width=True, key="competitor_map")

        st.subheader("Top Rated Restaurants")

        top_rest = restaurants.sort_values(
            "Rating",
            ascending=False
        ).head(5)

        st.dataframe(top_rest)

        st.subheader("Trending Dishes Nearby")

        top_dishes = dishes.sort_values(
            "mentions",
            ascending=False
        ).head(5)

        fig = px.bar(
            top_dishes,
            x="dish",
            y="mentions"
        )

        st.plotly_chart(fig, use_container_width=True, key="competitor_dishes")

        if not top_dishes.empty:

            st.success(
                f"Opportunity: {top_dishes.iloc[0]['dish']} is trending nearby"
            )