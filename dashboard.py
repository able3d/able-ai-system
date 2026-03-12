import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine, text
from google_reviews_scraper import scrape_google_reviews
from run_pipeline import run_pipeline

# Run pipeline only once
if "pipeline_ran" not in st.session_state:
    run_pipeline()
    st.session_state["pipeline_ran"] = True
# -------------------------------
# PAGE CONFIG
# -------------------------------

st.set_page_config(
    page_title="Able AI Restaurant Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------
# CLEAN UI
# -------------------------------

st.markdown("""
<style>

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.block-container{
    padding-top:1rem;
}

.metric-card {
    background-color:#111;
    padding:15px;
    border-radius:10px;
}

</style>
""", unsafe_allow_html=True)

# -------------------------------
# HEADER
# -------------------------------

st.markdown(
"""
<h2 style='text-align:center;'>
🍽 Able AI Restaurant Intelligence
</h2>
""",
unsafe_allow_html=True
)

# -------------------------------
# DATABASE
# -------------------------------


from sqlalchemy import create_engine, text
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


@st.cache_data
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

    try:

        df = pd.read_sql(query, engine)

        df.columns = df.columns.str.lower()

        return df

    except Exception as e:

        print("Menu load failed:", e)

        return pd.DataFrame(
            columns=["item_name","orders","revenue"]
        )



def ensure_tables():

    with engine.connect() as conn:

        # ----------------------------
        # MENU ITEMS
        # ----------------------------

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS menu_items (
            item_id SERIAL PRIMARY KEY,
            item_name TEXT UNIQUE
        )
        """))

        # ----------------------------
        # MENU SALES
        # ----------------------------

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS menu_sales (
            sale_id SERIAL PRIMARY KEY,
            item_id INTEGER,
            orders INTEGER DEFAULT 0,
            revenue FLOAT DEFAULT 0
        )
        """))

        # ----------------------------
        # INVENTORY
        # ----------------------------

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory (
            ingredient_id SERIAL PRIMARY KEY,
            ingredient_name TEXT,
            quantity FLOAT,
            unit TEXT
        )
        """))

        # ----------------------------
        # PURCHASES
        # ----------------------------

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS purchases (
            purchase_id SERIAL PRIMARY KEY,
            ingredient_name TEXT,
            quantity FLOAT,
            unit TEXT,
            price FLOAT,
            purchase_date DATE
        )
        """))

        conn.commit()

ensure_tables()
# -------------------------------
# DATA LOADERS
# -------------------------------


@st.cache_data
def load_inventory():

    try:

        df = pd.read_sql("SELECT * FROM inventory", engine)

        # Normalize column names
        df.columns = df.columns.str.lower()

        if "ingredient" in df.columns:
            df = df.rename(columns={"ingredient":"ingredient_name"})

        if "qty" in df.columns:
            df = df.rename(columns={"qty":"quantity"})

        return df

    except Exception as e:

        print("Inventory load failed:", e)

        return pd.DataFrame(
            columns=["ingredient_name","quantity","unit"]
        )




@st.cache_data
def load_purchases():

    try:

        df = pd.read_sql("SELECT * FROM purchases", engine)

        df.columns = df.columns.str.lower()

        if "item_name" in df.columns:
            df["ingredient_name"] = df["item_name"]

        return df

    except Exception as e:

        print("Purchases load failed:", e)

        return pd.DataFrame()


# -------------------------------
# NAVIGATION
# -------------------------------

tabs = st.tabs([
    "📊 Dashboard",
    "📦 Inventory",
    "🛒 Purchases",
    "🍽 Menu Analytics",
    "🌍 Competitor Intelligence"
])

# =====================================================
# DASHBOARD
# =====================================================

with tabs[0]:

    st.subheader("Restaurant Overview")

    menu = load_menu()

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Revenue", f"${menu['revenue'].sum():,.0f}")
    col2.metric("Total Orders", menu['orders'].sum())
    col3.metric("Menu Items", menu['item_name'].nunique())

    st.divider()

    fig = px.bar(
        menu,
        x="item_name",
        y="revenue",
        title="Menu Revenue"
    )

    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# INVENTORY
# =====================================================

with tabs[1]:

    st.subheader("Inventory")

    inventory = load_inventory()

    if inventory.empty:

        st.info("No Inventory data available. Add ingredients to database.")

    else:

        fig = px.bar(
            inventory,
            x="ingredient_name",
            y="quantity",
            title="Inventory Levels"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(inventory, use_container_width=True)

# =====================================================
# PURCHASES
# =====================================================

with tabs[2]:

    st.subheader("Purchases")

    purchases = load_purchases()

    if purchases.empty:

        st.warning("No purchases found")

    else:

        # GRAPH FIRST

        fig = px.bar(
            purchases,
            x="item_name",
            y="quantity",
            title="Purchased Ingredients"
        )

        st.plotly_chart(fig, use_container_width=True)

        # TABLE BELOW

        st.dataframe(purchases, use_container_width=True)

# =====================================================
# MENU ANALYTICS
# =====================================================

with tabs[3]:

    st.subheader("Menu Performance")

    menu = load_menu()

    if menu.empty:

        st.warning("No menu data")

    else:

        fig = px.bar(
            menu,
            x="item_name",
            y="orders",
            title="Most Popular Dishes"
        )

        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.bar(
            menu,
            x="item_name",
            y="revenue",
            title="Revenue by Dish"
        )

        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(menu, use_container_width=True)

# =====================================================
# COMPETITOR INTELLIGENCE
# =====================================================

with tabs[4]:

    st.subheader("Competitor Intelligence")

    st.caption("Market insights from nearby Ethiopian restaurants")

    if st.button("Run Market Analysis"):

        with st.spinner("Collecting competitor data..."):

            data = scrape_google_reviews()

        restaurants = data["restaurants"]
        dishes = data["dishes"]

        # ----------------------------
        # MAP
        # ----------------------------

        st.subheader("Competitor Map")

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

            st.plotly_chart(fig, use_container_width=True)

        # ----------------------------
        # DEMAND HEATMAP
        # ----------------------------

        st.subheader("Demand Heatmap")

        if not restaurants.empty:

            heatmap = px.density_mapbox(
                restaurants,
                lat="lat",
                lon="lon",
                z="demand",
                radius=25,
                zoom=11
            )

            heatmap.update_layout(mapbox_style="open-street-map")

            st.plotly_chart(heatmap, use_container_width=True)

        # ----------------------------
        # COMPETITOR TABLE
        # ----------------------------

        st.subheader("Competitor Restaurants")

        st.dataframe(restaurants, use_container_width=True)

        # ----------------------------
        # POPULAR DISHES
        # ----------------------------

        st.subheader("Popular Dishes")

        if not dishes.empty:

            fig = px.bar(
                dishes,
                x="dish",
                y="mentions",
                title="Dish Mentions in Reviews"
            )

            st.plotly_chart(fig, use_container_width=True)

        # ----------------------------
        # AI RECOMMENDATION
        # ----------------------------

        st.subheader("AI Menu Opportunity")

        if not dishes.empty:

            top = dishes.sort_values(
                "mentions",
                ascending=False
            ).iloc[0]["dish"]

            st.success(
                f"High demand detected for **{top.title()}** nearby."
            )
