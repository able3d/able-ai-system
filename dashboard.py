import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine
from google_reviews_scraper import scrape_google_reviews
import run_pipeline


# -------------------------------------------------
# RUN PIPELINE ONCE
# -------------------------------------------------

if "pipeline_ran" not in st.session_state:

    with st.spinner("Updating restaurant data..."):

        run_pipeline.run_pipeline()

    st.session_state["pipeline_ran"] = True


# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------

st.set_page_config(
    page_title="Able AI Restaurant Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------
# CLEAN UI
# -------------------------------------------------

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
# DATABASE CONNECTION
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

    try:

        df = pd.read_sql(query, engine)
        df.columns = df.columns.str.lower()

        return df

    except:

        return pd.DataFrame(
            columns=["item_name","orders","revenue"]
        )


# -------------------------------------------------
# INVENTORY
# -------------------------------------------------

@st.cache_data(ttl=60)
def load_inventory():

    query = """
    SELECT
        i.ingredient_name,
        inv.quantity AS remaining,
        i.unit
    FROM inventory inv
    JOIN ingredients i
    ON inv.ingredient_id = i.ingredient_id
    """

    try:

        df = pd.read_sql(query, engine)
        df.columns = df.columns.str.lower()

        return df

    except Exception as e:

        print("Inventory load error:", e)

        return pd.DataFrame(
            columns=["ingredient_name","remaining","unit"]
        )


@st.cache_data(ttl=60)
def load_purchases():

    try:

        df = pd.read_sql("SELECT * FROM purchases", engine)

        df.columns = df.columns.str.lower()

        return df

    except:

        return pd.DataFrame()


# -------------------------------------------------
# INGREDIENT USAGE (FROM BOM)
# -------------------------------------------------

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

    try:

        df = pd.read_sql(query, engine)

        df.columns = df.columns.str.lower()

        return df

    except:

        return pd.DataFrame(
            columns=["ingredient_name","quantity_used"]
        )


# -------------------------------------------------
# NAVIGATION
# -------------------------------------------------

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
    col2.metric("Total Orders", int(menu["orders"].sum()))
    col3.metric("Menu Items", menu["item_name"].nunique())

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

    st.subheader("Inventory Status")

    inventory = load_inventory()

    if inventory.empty:

        st.info("No inventory data available")

    else:

        fig = px.bar(
            inventory,
            x="ingredient_name",
            y="remaining",
            title="Remaining Inventory"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(inventory, use_container_width=True)

        # LOW STOCK ALERT

        low_stock = inventory[inventory["remaining"] < 500]

        if not low_stock.empty:

            st.warning("⚠ Low Stock Ingredients")

            st.dataframe(low_stock)

    # INGREDIENT CONSUMPTION

    usage = load_usage()

    if not usage.empty:

        st.subheader("Ingredient Consumption")

        fig = px.bar(
            usage,
            x="ingredient_name",
            y="quantity_used",
            title="Ingredient Usage From Dish Sales"
        )

        st.plotly_chart(fig, use_container_width=True)


# =====================================================
# PURCHASES
# =====================================================

with tabs[2]:

    st.subheader("Purchases")

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

        st.plotly_chart(fig, use_container_width=True)

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

        # MAP

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

        # DEMAND HEATMAP

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

        # RESTAURANT TABLE

        st.subheader("Competitor Restaurants")

        st.dataframe(restaurants, use_container_width=True)

        # POPULAR DISHES

        st.subheader("Popular Dishes")

        if not dishes.empty:

            fig = px.bar(
                dishes,
                x="dish",
                y="mentions",
                title="Dish Mentions in Reviews"
            )

            st.plotly_chart(fig, use_container_width=True)

        # AI RECOMMENDATION

        st.subheader("AI Menu Opportunity")

        if not dishes.empty:

            top = dishes.sort_values(
                "mentions",
                ascending=False
            ).iloc[0]["dish"]

            st.success(
                f"High demand detected for **{top.title()}** nearby."
            )
