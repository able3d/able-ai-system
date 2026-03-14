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

<link rel="apple-touch-icon" href="images/app_icon.png">
""", unsafe_allow_html=True)

# -------------------------------------------------
# STYLE
# -------------------------------------------------

st.markdown("""
<style>

header {visibility:hidden;}
footer {visibility:hidden;}
#MainMenu {visibility:hidden;}

.block-container{
padding-top:1rem;
max-width:1200px;
}

[data-testid="metric-container"]{
background:linear-gradient(135deg,#1c1c1c,#2a2a2a);
border-radius:16px;
padding:20px;
border:1px solid #333;
}

img{
border-radius:14px;
box-shadow:0 10px 25px rgba(0,0,0,0.45);
}

.menu-card{
background:#1f1f1f;
border-radius:16px;
padding:15px;
border:1px solid #333;
text-align:center;
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HERO
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
    st.error("DATABASE_URL not set")
    st.stop()

engine = create_engine(DATABASE_URL)

# -------------------------------------------------
# PIPELINE
# -------------------------------------------------

st.markdown("## ⚙️ Data Pipeline")

c1,c2,c3 = st.columns(3)

with c1:

    if st.button("▶ Run Full Pipeline"):

        with st.spinner("Running pipeline..."):
            run_pipeline.run_pipeline()

        st.success("Pipeline completed!")

with c2:

    if st.button("🔄 Refresh Dashboard"):
        st.cache_data.clear()
        st.rerun()

with c3:

    if st.button("🧹 Clear Cache"):
        st.cache_data.clear()
        st.success("Cache cleared")

# -------------------------------------------------
# COMPETITOR SCRAPER
# -------------------------------------------------

st.markdown("## 🌍 Competitor Intelligence")

c1,c2 = st.columns(2)

with c1:

    if st.button("▶ Run Competitor Scraper"):

        with st.spinner("Scraping competitor reviews..."):
            scrape_google_reviews()

        st.success("Competitor data updated!")

with c2:

    if st.button("🔄 Refresh Competitor Data"):
        st.cache_data.clear()
        st.rerun()

# -------------------------------------------------
# DATA LOADERS
# -------------------------------------------------

@st.cache_data(ttl=60)
def load_menu():

    query = """
    SELECT
        m.item_name,
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
    SELECT
    i.ingredient_name,
    inv.quantity
    FROM inventory inv
    JOIN ingredients i
    ON inv.ingredient_id = i.ingredient_id
    """

    return pd.read_sql(query, engine)


@st.cache_data(ttl=60)
def load_purchases():

    query = """
    SELECT
    ingredient_name,
    SUM(quantity) quantity,
    SUM(price) total_cost
    FROM purchases
    GROUP BY ingredient_name
    """

    return pd.read_sql(query, engine)


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

    return restaurants,dishes

# -------------------------------------------------
# MENU IMAGES
# -------------------------------------------------

menu_images = {
"Doro Wat":"images/doro_wat.jpg",
"Kitfo":"images/kitfo.jpg",
"Shiro":"images/shiro.jpg",
"Injera Basket":"images/vegan combo.jpg"
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

    st.markdown("## Restaurant Performance")

    m1,m2,m3,m4 = st.columns(4)

    m1.metric("💰 Revenue",f"${revenue:,.0f}")
    m2.metric("💸 Ingredient Spend",f"${spend:,.0f}")
    m3.metric("📈 Profit",f"${profit:,.0f}")
    m4.metric("🍽 Orders",int(orders))

    fig = px.bar(
        menu,
        x="item_name",
        y="revenue",
        text="revenue",
        color="revenue",
        color_continuous_scale="reds"
    )

    fig.update_layout(
        title="Revenue by Dish",
        xaxis_tickangle=-25
    )

    st.plotly_chart(fig,use_container_width=True)

# =================================================
# INVENTORY
# =================================================

with tabs[1]:

    inventory = load_inventory()

    st.markdown("## Ingredient Inventory")

    fig = px.bar(
        inventory,
        x="ingredient_name",
        y="quantity",
        color="quantity",
        color_continuous_scale="greens"
    )

    st.plotly_chart(fig,use_container_width=True)

    st.dataframe(inventory,use_container_width=True)

# =================================================
# PURCHASES
# =================================================

with tabs[2]:

    purchases = load_purchases()

    st.markdown("## Ingredient Purchases")

    fig = px.bar(
        purchases,
        x="ingredient_name",
        y="total_cost",
        color="total_cost",
        color_continuous_scale="blues"
    )

    st.plotly_chart(fig,use_container_width=True)

    st.dataframe(purchases,use_container_width=True)

# =================================================
# MENU SALES
# =================================================

with tabs[3]:

    menu = load_menu()

    st.markdown("## Menu Sales Performance")

    cols = st.columns(3)

    i = 0

    for index,row in menu.iterrows():

        name = row["item_name"]
        revenue = row["revenue"]
        orders = row["orders"]

        image = menu_images.get(name,None)

        with cols[i % 3]:

            st.markdown('<div class="menu-card">',unsafe_allow_html=True)

            if image and os.path.exists(image):
                st.image(image)

            st.markdown(f"### {name}")
            st.write(f"Orders: {orders}")
            st.write(f"Revenue: ${revenue:,.0f}")

            st.markdown('</div>',unsafe_allow_html=True)

        i += 1

# =================================================
# COMPETITION
# =================================================

with tabs[4]:

    restaurants,dishes = load_competitors()

    st.markdown("## Competitor Map")

    fig = px.scatter_mapbox(
        restaurants,
        lat="lat",
        lon="lon",
        hover_name="Restaurant",
        hover_data=["Rating","Reviews"],
        zoom=13,
        height=500
    )

    fig.update_layout(
        mapbox_style="carto-darkmatter",
        margin={"r":0,"t":0,"l":0,"b":0}
    )

    st.plotly_chart(fig,use_container_width=True)

    st.markdown("### Competitor Ratings")

    st.dataframe(restaurants,use_container_width=True)

    st.markdown("### Trending Dishes")

    fig2 = px.bar(
        dishes,
        x="Dish",
        y="Mentions",
        color="Mentions",
        color_continuous_scale="reds"
    )

    st.plotly_chart(fig2,use_container_width=True)

# =================================================
# AI INSIGHTS
# =================================================

with tabs[5]:

    st.markdown("## 🤖 AI Insights")

    st.info("AI insights will analyze menu demand, competitor trends, and inventory risk.")

    st.markdown("""
    Example insights:

    🔥 Kitfo demand increasing in competitor reviews  
    ⚠ Beef inventory projected to run out in 3 days  
    📉 Injera sales declining this week
    """)