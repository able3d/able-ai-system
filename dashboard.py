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
    page_title="Able AI",
    layout="wide"
)

# -------------------------------------------------
# MODERN UI STYLE
# -------------------------------------------------

st.markdown("""
<style>

header, footer, #MainMenu {visibility:hidden;}

.block-container {
    padding-top: 1.5rem;
    max-width: 1200px;
}

/* METRIC CARDS */
.metric-card {
    background: #1f1f1f;
    border-radius: 14px;
    padding: 18px;
    text-align:center;
    border: 1px solid #2c2c2c;
}

/* MENU CARD */
.menu-card {
    background: #1f1f1f;
    border-radius: 16px;
    padding: 12px;
    border: 1px solid #2c2c2c;
    text-align:center;
    transition: 0.2s;
}

.menu-card:hover {
    transform: scale(1.02);
}

/* BUTTON BAR */
.button-bar button {
    border-radius: 10px !important;
}

/* TITLE */
h1, h2, h3 {
    font-weight:600;
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HERO (CLEAN + NOT CUT)
# -------------------------------------------------

st.image("images/vegan combo.PNG", use_column_width=True)

st.markdown("## 🍽 Able AI Restaurant Intelligence")

st.caption("Simple AI system for revenue, inventory, and competitor insights")

# -------------------------------------------------
# DATABASE
# -------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("DATABASE_URL not set")
    st.stop()

engine = create_engine(DATABASE_URL)

# -------------------------------------------------
# ACTION BAR (CLEAN)
# -------------------------------------------------

st.markdown("### ⚙️ Actions")

a1, a2, a3 = st.columns(3)

with a1:
    if st.button("▶ Run Pipeline", use_container_width=True):
        with st.spinner("Running..."):
            run_pipeline.run_pipeline()
        st.success("Done")
        st.cache_data.clear()
        st.rerun()

with a2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with a3:
    if st.button("🧹 Clear Cache", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache cleared")

# -------------------------------------------------
# LOADERS
# -------------------------------------------------

@st.cache_data(ttl=60)
def load_menu():
    return pd.read_sql("""
    SELECT m.item_name,
           COALESCE(SUM(s.orders),0) orders,
           COALESCE(SUM(s.revenue),0) revenue
    FROM menu_items m
    LEFT JOIN menu_sales s
    ON m.item_id = s.item_id
    GROUP BY m.item_name
    ORDER BY revenue DESC
    """, engine)

@st.cache_data(ttl=60)
def load_inventory():
    return pd.read_sql("""
    SELECT i.ingredient_name,
           GREATEST(inv.quantity,0) quantity
    FROM inventory inv
    JOIN ingredients i
    ON inv.ingredient_id = i.ingredient_id
    """, engine)

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
"Overview",
"Inventory",
"Purchases",
"Menu",
"Competition",
"Insights"
])

# =================================================
# OVERVIEW
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

    with c1:
        st.markdown('<div class="metric-card">💰<br><b>Revenue</b><br>$%s</div>' % f"{revenue:,.0f}", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="metric-card">📦<br><b>Spend</b><br>$%s</div>' % f"{spend:,.0f}", unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="metric-card">📈<br><b>Profit</b><br>$%s</div>' % f"{profit:,.0f}", unsafe_allow_html=True)

    with c4:
        st.markdown('<div class="metric-card">🧾<br><b>Orders</b><br>%s</div>' % int(orders), unsafe_allow_html=True)

    st.markdown("### Revenue by Dish")

    fig = px.bar(menu, x="item_name", y="revenue")
    st.plotly_chart(fig, use_container_width=True)

# =================================================
# INVENTORY
# =================================================

with tabs[1]:

    inventory = load_inventory()

    st.markdown("### Inventory Levels")

    fig = px.bar(inventory, x="ingredient_name", y="quantity")
    st.plotly_chart(fig, use_container_width=True)

    low = inventory[inventory["quantity"] < 5]

    if not low.empty:
        st.warning("⚠ Low inventory items")
        st.dataframe(low)

# =================================================
# MENU (CLEAN CARDS)
# =================================================

with tabs[3]:

    menu = load_menu()

    st.markdown("### 🍽 Menu Performance")

    cols = st.columns(3)

    for i, row in menu.iterrows():

        name = row["item_name"].lower()
        image = menu_images.get(name)

        with cols[i % 3]:

            st.markdown('<div class="menu-card">', unsafe_allow_html=True)

            if image and os.path.exists(image):
                st.image(image, use_column_width=True)

            st.markdown(f"**{row['item_name']}**")
            st.caption(f"{int(row['orders'])} orders")
            st.markdown(f"**${row['revenue']:,.0f}**")

            st.markdown('</div>', unsafe_allow_html=True)

# =================================================
# COMPETITION
# =================================================

with tabs[4]:

    st.markdown("### 🏆 Competitor Insights")

    if st.button("Run Scraper"):
        scrape_google_reviews()
        st.success("Updated")
        st.cache_data.clear()
        st.rerun()

    restaurants, dishes = load_competitors()

    if not restaurants.empty:

        top = restaurants.sort_values("Rating", ascending=False).iloc[0]

        st.success(f"⭐ Top: {top['Restaurant']} ({top['Rating']})")

        fig = px.scatter_mapbox(
            restaurants,
            lat="lat",
            lon="lon",
            hover_name="Restaurant",
            zoom=12
        )

        fig.update_layout(mapbox_style="carto-darkmatter")
        st.plotly_chart(fig, use_container_width=True)

# =================================================
# INSIGHTS
# =================================================

with tabs[5]:

    menu = load_menu()

    if not menu.empty:
        top = menu.iloc[0]
        st.success(f"🔥 Best dish: {top['item_name']} (${top['revenue']:,.0f})")