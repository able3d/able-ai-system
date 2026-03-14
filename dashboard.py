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
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# PWA META TAGS
# -------------------------------------------------

st.markdown("""
<link rel="manifest" href="/manifest.json">

<meta name="theme-color" content="#000000">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Able AI">

<link rel="apple-touch-icon" href="https://raw.githubusercontent.com/able-ai-system/able-ai/main/images/app_icon.png">
""", unsafe_allow_html=True)

# -------------------------------------------------
# UI STYLE
# -------------------------------------------------

st.markdown("""
<style>

header {visibility: hidden;}
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}

.block-container{
padding-top:1rem;
max-width:1000px;
}

[data-testid="metric-container"]{
background:linear-gradient(135deg,#1c1c1c,#2a2a2a);
border-radius:15px;
padding:20px;
border:1px solid #333;
}

img{
border-radius:14px;
box-shadow:0 6px 16px rgba(0,0,0,0.4);
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HERO IMAGE
# -------------------------------------------------

st.image(
    "images/vegan combo.PNG",
    use_container_width=True
)

st.markdown("""
# 🍽 Able AI Restaurant Intelligence  
Track **inventory, menu performance, competitor demand, and restaurant trends** in real time.
""")

# -------------------------------------------------
# DATABASE
# -------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("DATABASE_URL environment variable not set")
    st.stop()

engine = create_engine(DATABASE_URL)

# -------------------------------------------------
# DATA PIPELINE
# -------------------------------------------------

st.markdown("## ⚙️ Data Pipeline")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶ Run Pipeline"):

        with st.spinner("Processing invoices, receipts, and competitor data..."):
            run_pipeline.run_pipeline()

        st.success("Pipeline completed!")

with col2:
    if st.button("🔄 Refresh Dashboard"):

        st.cache_data.clear()
        st.rerun()

with col3:
    if st.button("🧹 Clear Cache"):

        st.cache_data.clear()
        st.success("Cache cleared!")

# -------------------------------------------------
# DATA LOADERS
# -------------------------------------------------

@st.cache_data(ttl=60)
def load_menu():

    query = """
    SELECT
        m.item_name,
        COALESCE(SUM(s.orders),0) AS orders,
        COALESCE(SUM(s.revenue),0) AS revenue
    FROM menu_items m
    LEFT JOIN menu_sales s
        ON s.item_id = m.item_id
    GROUP BY m.item_name
    ORDER BY revenue DESC
    """

    df = pd.read_sql(query, engine)

    df.index = range(1, len(df) + 1)

    return df


@st.cache_data(ttl=60)
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

    df["quantity"] = df["quantity"].clip(lower=0)

    return df


@st.cache_data(ttl=60)
def load_purchases():

    query = """
    SELECT
        ingredient_name,
        SUM(quantity) quantity,
        SUM(price) total_cost
    FROM purchases
    GROUP BY ingredient_name
    ORDER BY quantity DESC
    """

    return pd.read_sql(query, engine)

# -------------------------------------------------
# GOOGLE REVIEWS
# -------------------------------------------------

@st.cache_data(ttl=3600)
def load_competitors():

    data = scrape_google_reviews()

    restaurants = data["restaurants"]
    dishes = data["dishes"]

    coords = {
        "Haile": (40.7216, -73.9803),
        "Awaze": (40.7487, -73.9857),
        "Addey Ababa": (40.7262, -73.9845)
    }

    for i,row in restaurants.iterrows():

        name = row["Restaurant"]

        if name in coords:

            restaurants.loc[i,"lat"] = coords[name][0]
            restaurants.loc[i,"lon"] = coords[name][1]

    return restaurants, dishes


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

    spend_query = """
    SELECT COALESCE(SUM(price),0) AS total_spend
    FROM purchases
    """

    spend = pd.read_sql(spend_query, engine).iloc[0]["total_spend"]

    profit = revenue - spend

    st.markdown("## Restaurant Performance")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("💰 Revenue", f"${revenue:,.0f}")
    c2.metric("💸 Ingredient Spend", f"${spend:,.0f}")
    c3.metric("📈 Estimated Profit", f"${profit:,.0f}")
    c4.metric("🍽 Orders", int(orders))

    fig = px.bar(
        menu,
        x="item_name",
        y="revenue",
        text="revenue",
        title="Revenue by Dish"
    )

    fig.update_layout(xaxis_tickangle=-30)

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Menu Performance")

    st.dataframe(menu, use_container_width=True)

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
            title="Inventory Levels"
        )

        fig.update_layout(xaxis_tickangle=-30)

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(inventory, use_container_width=True)

# =================================================
# PURCHASES
# =================================================

with tabs[2]:

    purchases = load_purchases()

    if purchases.empty:

        st.warning("No purchase data")

    else:

        fig = px.bar(
            purchases,
            x="ingredient_name",
            y="quantity",
            title="Ingredient Purchases"
        )

        fig.update_layout(xaxis_tickangle=-30)

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(purchases, use_container_width=True)

# =================================================
# MENU
# =================================================

with tabs[3]:

    menu = load_menu()

    st.markdown("### Menu Sales")

    st.dataframe(menu, use_container_width=True)

# =================================================
# COMPETITION
# =================================================

with tabs[4]:

    restaurants, dishes = load_competitors()

    if not restaurants.empty:

        st.map(restaurants)

        st.dataframe(restaurants)

    if not dishes.empty:

        st.markdown("### Popular Dishes")

        st.dataframe(dishes)

# =================================================
# AI INSIGHTS
# =================================================

with tabs[5]:

    st.markdown("### AI Insights")

    menu = load_menu()

    if not menu.empty:

        top = menu.iloc[0]

        st.success(f"🔥 Top Dish: **{top['item_name']}** generating ${top['revenue']:,.0f}")

        low = menu.iloc[-1]

        st.warning(f"⚠️ Lowest Performer: **{low['item_name']}**")