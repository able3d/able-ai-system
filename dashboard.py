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

.menu-card{
background:#1f1f1f;
border-radius:16px;
padding:12px;
border:1px solid #333;
text-align:center;
}

img{
border-radius:12px;
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HERO
# -------------------------------------------------

st.image("images/vegan combo.PNG",use_container_width=True)

st.markdown("""
# 🍽 Able AI Restaurant Intelligence  
Track **inventory, menu performance, competitor demand and restaurant trends**.
""")

# -------------------------------------------------
# DATABASE
# -------------------------------------------------

DATABASE_URL=os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("DATABASE_URL not set")
    st.stop()

engine=create_engine(DATABASE_URL)
# --------
# button 
# ------
# -------------------------------------------------
# DATA PIPELINE CONTROLS
# -------------------------------------------------

st.markdown("## ⚙️ Data Pipeline")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶ Run Pipeline", use_container_width=True):

        with st.spinner("Processing receipts and invoices..."):
            run_pipeline.run_pipeline()

        st.success("Pipeline completed!")

        st.cache_data.clear()
        st.rerun()

with col2:
    if st.button("🔄 Refresh Dashboard", use_container_width=True):

        st.cache_data.clear()
        st.rerun()

with col3:
    if st.button("🧹 Clear Cache", use_container_width=True):

        st.cache_data.clear()
        st.success("Cache cleared")

# -------------------------------------------------
# DATA LOADERS
# -------------------------------------------------

@st.cache_data(ttl=60)
def load_menu():

    query="""
    SELECT
    m.item_name,
    COALESCE(SUM(s.orders),0) orders,
    COALESCE(SUM(s.revenue),0) revenue
    FROM menu_items m
    LEFT JOIN menu_sales s
    ON m.item_id=s.item_id
    GROUP BY m.item_name
    ORDER BY revenue DESC
    """

    return pd.read_sql(query,engine)

@st.cache_data(ttl=60)
def load_inventory():

    query="""
    SELECT
    i.ingredient_name,
    GREATEST(inv.quantity,0) quantity
    FROM inventory inv
    JOIN ingredients i
    ON inv.ingredient_id=i.ingredient_id
    """

    df=pd.read_sql(query,engine)

    df["quantity"]=df["quantity"].clip(lower=0)

    return df

@st.cache_data(ttl=60)
def load_purchases():

    query="""
    SELECT
    ingredient_name,
    SUM(quantity) quantity,
    SUM(price) total_cost
    FROM purchases
    GROUP BY ingredient_name
    """

    return pd.read_sql(query,engine)

@st.cache_data(ttl=3600)
def load_competitors():

    data=scrape_google_reviews()

    restaurants=data["restaurants"]
    dishes=data["dishes"]

    coords={
    "Haile":(40.7216,-73.9803),
    "Awaze":(40.7487,-73.9857),
    "Addey Ababa":(40.7262,-73.9845)
    }

    for i,row in restaurants.iterrows():

        name=row["Restaurant"]

        if name in coords:

            restaurants.loc[i,"lat"]=coords[name][0]
            restaurants.loc[i,"lon"]=coords[name][1]

    return restaurants,dishes

# -------------------------------------------------
# MENU IMAGES
# -------------------------------------------------

menu_images={
"doro wat":"images/doro_wat.jpg",
"kitfo":"images/kitfo.jpg",
"shiro":"images/shiro.jpg",
"injera basket":"images/vegan combo.jpg"
}

# -------------------------------------------------
# TABS
# -------------------------------------------------

tabs=st.tabs([
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

    menu=load_menu()

    revenue=menu["revenue"].sum()
    orders=menu["orders"].sum()

    spend=pd.read_sql(
    "SELECT COALESCE(SUM(price),0) spend FROM purchases",
    engine
    ).iloc[0]["spend"]

    profit=revenue-spend

    c1,c2,c3,c4=st.columns(4)

    c1.metric("Revenue",f"${revenue:,.0f}")
    c2.metric("Ingredient Spend",f"${spend:,.0f}")
    c3.metric("Profit",f"${profit:,.0f}")
    c4.metric("Orders",int(orders))

    fig=px.bar(
    menu,
    x="item_name",
    y="revenue",
    color="revenue",
    text="revenue"
    )

    st.plotly_chart(fig,use_container_width=True)

# =================================================
# INVENTORY
# =================================================

with tabs[1]:

    inventory=load_inventory()

    fig=px.bar(
    inventory,
    x="ingredient_name",
    y="quantity",
    color="quantity"
    )

    st.plotly_chart(fig,use_container_width=True)

    # Inventory depletion alert

    low=inventory[inventory["quantity"]<5]

    if not low.empty:

        st.warning("⚠ Low Inventory Detected")

        st.dataframe(low)

# =================================================
# PURCHASES
# =================================================

with tabs[2]:

    purchases=load_purchases()

    st.dataframe(purchases,use_container_width=True)

# =================================================
# MENU SALES
# =================================================

with tabs[3]:

    menu=load_menu()

    st.markdown("## Menu Sales")

    cols=st.columns(3)

    for i,row in menu.iterrows():

        name=row["item_name"].lower()

        image=menu_images.get(name)

        with cols[i%3]:

            if image and os.path.exists(image):

                st.image(image,use_container_width=True)

            st.markdown(f"### {row['item_name']}")
            st.metric("Orders",int(row["orders"]))
            st.metric("Revenue",f"${row['revenue']:,.0f}")

# =================================================
# COMPETITION
# =================================================

with tabs[4]:

    st.markdown("## Competitor Intelligence")

    c1,c2=st.columns(2)

    with c1:

        if st.button("Run Competitor Scraper"):

            scrape_google_reviews()

            st.success("Scraper complete")

    with c2:

        if st.button("Refresh Competitor Data"):

            st.cache_data.clear()

            st.rerun()

    restaurants,dishes=load_competitors()

    fig=px.scatter_mapbox(
    restaurants,
    lat="lat",
    lon="lon",
    hover_name="Restaurant",
    hover_data=["Rating","demand"],
    color="Rating",
    zoom=13
    )

    fig.update_layout(mapbox_style="carto-darkmatter")

    st.plotly_chart(fig,use_container_width=True)

# =================================================
# AI INSIGHTS
# =================================================

with tabs[5]:

    st.markdown("## AI Restaurant Insights")

    menu=load_menu()

    top=menu.iloc[0]

    st.success(
    f"🔥 {top['item_name']} is currently the top performing dish generating ${top['revenue']:,.0f}"
    )

    trending=menu.sort_values("orders",ascending=False).head(3)

    st.markdown("### Dish Demand Prediction")

    st.dataframe(trending)