import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine
import run_pipeline


# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------

st.set_page_config(
    page_title="Able AI Restaurant Intelligence",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# PWA SUPPORT (IPHONE FULLSCREEN)
# -------------------------------------------------

st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Able AI">
<meta name="viewport" content="width=device-width, initial-scale=1">
""", unsafe_allow_html=True)


# -------------------------------------------------
# MOBILE UI STYLE
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

h1,h2,h3{
    text-align:center;
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
# RUN PIPELINE ONLY ONCE
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


# -------------------------------------------------
# HEADER
# -------------------------------------------------

st.markdown("""
# 🍽 Able AI Restaurant Intelligence
""")


# -------------------------------------------------
# TABS
# -------------------------------------------------

tabs = st.tabs([
    "📊 Dashboard",
    "📦 Inventory",
    "🛒 Purchases",
    "🍽 Menu",
    "🧠 AI Insights"
])


# =================================================
# DASHBOARD
# =================================================

with tabs[0]:

    menu = load_menu()

    col1, col2 = st.columns(2)

    col1.metric("Revenue", f"${menu['revenue'].sum():,.0f}")
    col2.metric("Orders", int(menu["orders"].sum()))

    st.metric("Menu Items", menu["item_name"].nunique())

    fig = px.bar(
        menu,
        x="item_name",
        y="revenue",
        title="Revenue by Dish"
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
        key="revenue_chart"
    )


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
            y="remaining",
            title="Remaining Inventory"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False},
            key="inventory_chart"
        )

        low_stock = inventory[inventory["remaining"] < 300]

        if not low_stock.empty:

            st.error("⚠ Low Inventory Warning")

            st.dataframe(low_stock)


# =================================================
# PURCHASES
# =================================================

with tabs[2]:

    purchases = load_purchases()

    if purchases.empty:

        st.info("No purchases found yet")

    else:

        fig = px.bar(
            purchases,
            x="ingredient_name",
            y="quantity",
            title="Purchased Ingredients"
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False},
            key="purchases_chart"
        )

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

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False},
        key="menu_orders"
    )

    fig2 = px.bar(
        menu,
        x="item_name",
        y="revenue",
        title="Revenue by Dish"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True,
        config={"displayModeBar": False},
        key="menu_revenue"
    )


# =================================================
# AI INSIGHTS
# =================================================

with tabs[4]:

    st.subheader("AI Restaurant Insights")

    menu = load_menu()
    inventory = load_inventory()

    if not menu.empty:

        top = menu.sort_values(
            "orders",
            ascending=False
        ).iloc[0]

        st.success(f"🔥 {top['item_name']} is your most popular dish")

    if not inventory.empty:

        low = inventory[inventory["remaining"] < 300]

        if not low.empty:

            st.warning(
                f"⚠ {low.iloc[0]['ingredient_name']} inventory running low"
            )

    revenue = menu["revenue"].sum()

    predicted = revenue * 1.1

    st.metric(
        "Predicted Revenue Next Period",
        f"${predicted:,.0f}"
    )