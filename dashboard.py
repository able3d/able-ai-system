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
    layout="wide"
)

# -------------------------------------------------
# STYLE (IMPROVED UI)
# -------------------------------------------------

st.markdown("""
<style>
header, footer, #MainMenu {visibility:hidden;}

.block-container {
    padding-top: 1rem;
    max-width: 1200px;
}

.metric-card {
    background: linear-gradient(135deg,#1c1c1c,#2a2a2a);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid #333;
}

.menu-card {
    background:#1f1f1f;
    border-radius:16px;
    padding:15px;
    border:1px solid #333;
    text-align:center;
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HERO (FIXED IMAGE CUT)
# -------------------------------------------------

st.image("images/vegan combo.PNG", use_column_width=True)

st.markdown("""
# 🍽 Able AI Restaurant Intelligence  
AI-powered system for **inventory, revenue, and competitor intelligence**
""")

# -------------------------------------------------
# DATABASE
# -------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("DATABASE_URL not set")
    st.stop()

engine = create_engine(DATABASE_URL)

# -------------------------------------------------
# PIPELINE CONTROLS
# -------------------------------------------------

st.markdown("## ⚙️ Data Pipeline")

c1,c2,c3 = st.columns(3)

with c1:
    if st.button("▶ Run Pipeline"):
        with st.spinner("Running pipeline..."):
            run_pipeline.run_pipeline()
        st.success("Pipeline completed")
        st.cache_data.clear()
        st.rerun()

with c2:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

with c3:
    if st.button("🧹 Clear Cache"):
        st.cache_data.clear()
        st.success("Cache cleared")

# -------------------------------------------------
# LOADERS
# -------------------------------------------------

@st.cache_data(ttl=60)
def load_menu():
    query = """
    SELECT m.item_name,
           COALESCE(SUM(s.orders),0) orders,
           COALESCE(SUM(s.revenue),0) revenue
    FROM menu_items m
    LEFT JOIN menu_sales s
    ON m.item_id = s.item_id
    GROUP BY m.item_name
    ORDER BY revenue DESC
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=60)
def load_inventory():
    query = """
    SELECT i.ingredient_name,
           GREATEST(inv.quantity,0) quantity
    FROM inventory inv
    JOIN ingredients i
    ON inv.ingredient_id = i.ingredient_id
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=60)
def load_purchases():
    return pd.read_sql("""
    SELECT ingredient_name,
           SUM(quantity) quantity,
           SUM(price) total_cost
    FROM purchases
    GROUP BY ingredient_name
    """, engine)

@st.cache_data(ttl=300)
def load_competitors():
    data = scrape_google_reviews()
    return data["restaurants"], data["dishes"]

# -------------------------------------------------
# MENU IMAGES
# -------------------------------------------------

menu_images = {
"doro wat":"images/doro_wat.jpg",
"kitfo":"images/kitfo.jpg",
"shiro":"images/shiro.jpg",
"injera basket":"images/vegan combo.PNG"
}

# -------------------------------------------------
# TABS
# -------------------------------------------------

tabs = st.tabs([
"📊 Dashboard",
"📦 Inventory",
"🛒 Purchases",
"🍽 Menu Sales",
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

    spend = pd.read_sql(
        "SELECT COALESCE(SUM(price),0) spend FROM purchases",
        engine
    ).iloc[0]["spend"]

    profit = revenue - spend

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Revenue", f"${revenue:,.0f}")
    c2.metric("Spend", f"${spend:,.0f}")
    c3.metric("Profit", f"${profit:,.0f}")
    c4.metric("Orders", int(orders))

    fig = px.bar(menu, x="item_name", y="revenue", color="revenue")
    st.plotly_chart(fig, use_container_width=True)

# =================================================
# INVENTORY
# =================================================

with tabs[1]:

    inventory = load_inventory()

    fig = px.bar(inventory, x="ingredient_name", y="quantity")
    st.plotly_chart(fig, use_container_width=True)

    low = inventory[inventory["quantity"] < 5]

    if not low.empty:
        st.warning("⚠ Low Inventory")
        st.dataframe(low)

# =================================================
# PURCHASES
# =================================================

with tabs[2]:

    st.dataframe(load_purchases(), use_container_width=True)

# =================================================
# MENU SALES (IMPROVED UI + IMAGES)
# =================================================

with tabs[3]:

    menu = load_menu()

    st.markdown("## 🍽 Menu Performance")

    cols = st.columns(3)

    for i, row in menu.iterrows():

        name = row["item_name"].lower()
        image = menu_images.get(name)

        with cols[i % 3]:

            st.markdown('<div class="menu-card">', unsafe_allow_html=True)

            if image and os.path.exists(image):
                st.image(image, use_column_width=True)

            st.markdown(f"### {row['item_name']}")
            st.metric("Orders", int(row["orders"]))
            st.metric("Revenue", f"${row['revenue']:,.0f}")

            st.markdown('</div>', unsafe_allow_html=True)

# =================================================
# COMPETITION (UPGRADED)
# =================================================

with tabs[4]:

    st.markdown("## 🏆 Competitor Intelligence")

    # BUTTONS INSIDE TAB
    c1,c2 = st.columns(2)

    with c1:
        if st.button("▶ Run Scraper"):
            scrape_google_reviews()
            st.success("Scraper finished")
            st.cache_data.clear()
            st.rerun()

    with c2:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    restaurants, dishes = load_competitors()

    # MAP
    if not restaurants.empty:

        fig = px.scatter_mapbox(
            restaurants,
            lat="lat",
            lon="lon",
            hover_name="Restaurant",
            hover_data=["Rating","demand"],
            color="Rating",
            zoom=12
        )

        fig.update_layout(mapbox_style="carto-darkmatter")
        st.plotly_chart(fig, use_container_width=True)

        # TOP RESTAURANT
        top_rest = restaurants.sort_values("Rating", ascending=False).head(1)

        if not top_rest.empty:
            st.success(f"⭐ Top Rated: {top_rest.iloc[0]['Restaurant']} ({top_rest.iloc[0]['Rating']})")

    # TOP DISHES
    if not dishes.empty:

        st.markdown("### 🔥 Top Mentioned Dishes")

        top_dishes = dishes.sort_values("mentions", ascending=False).head(5)

        fig = px.bar(top_dishes, x="dish", y="mentions", color="mentions")
        st.plotly_chart(fig, use_container_width=True)

# =================================================
# AI INSIGHTS
# =================================================

with tabs[5]:

    menu = load_menu()
    inventory = load_inventory()

    st.markdown("## 🧠 AI Insights")

    if not menu.empty:
        top = menu.iloc[0]
        st.success(f"🔥 Top Dish: {top['item_name']} (${top['revenue']:,.0f})")

    low = inventory[inventory["quantity"] < 5]

    if not low.empty:
        st.warning("⚠ Inventory Risk: " + ", ".join(low["ingredient_name"]))