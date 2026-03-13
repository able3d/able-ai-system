import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine
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
# HERO IMAGE
# -------------------------------------------------

st.image(
    "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d",
    use_container_width=True
)

st.markdown("""
# 🍽 Able AI Restaurant Intelligence  
Track **inventory, menu performance, competitor demand, and restaurant trends** in real time.
""")

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
# MODERN MOBILE UI
# -------------------------------------------------

st.markdown("""
<style>

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

.block-container{
padding-top:1rem;
max-width:850px;
}

[data-testid="metric-container"]{
background:linear-gradient(135deg,#1c1c1c,#2a2a2a);
border-radius:15px;
padding:20px;
border:1px solid #333;
}

img{
border-radius:12px;
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# DATABASE CONNECTION
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

    return pd.read_sql(query, engine)


# -------------------------------------------------
# GOOGLE REVIEWS SCRAPER
# -------------------------------------------------

@st.cache_data(ttl=3600)
def load_competitors():

    data = scrape_google_reviews()

    restaurants = data["restaurants"]
    dishes = data["dishes"]

    # Add coordinates so map works
    coords = {
        "Haile": (40.7216, -73.9803),
        "Awaze": (40.7487, -73.9857),
        "Addey Ababa": (40.7262, -73.9845)
    }

    for i, row in restaurants.iterrows():

        name = row["Restaurant"]

        if name in coords:

            restaurants.loc[i, "lat"] = coords[name][0]
            restaurants.loc[i, "lon"] = coords[name][1]

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

    st.markdown("## Restaurant Performance")

    col1, col2, col3 = st.columns(3)

    col1.metric("💰 Revenue", f"${revenue:,.0f}")
    col2.metric("🍽 Orders", int(orders))
    col3.metric("📋 Menu Items", menu["item_name"].nunique())

    st.markdown("---")

    fig = px.bar(
        menu,
        x="item_name",
        y="revenue",
        title="Revenue by Dish"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Popular dishes images

    st.markdown("## Popular Ethiopian Dishes")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.image(
            "https://images.unsplash.com/photo-1617196038435-6c7d1e4a2b2c",
            caption="Doro Wat"
        )

    with c2:
        st.image(
            "https://images.unsplash.com/photo-1604909053196-7b6c6d7d3a8f",
            caption="Kitfo"
        )

    with c3:
        st.image(
            "https://images.unsplash.com/photo-1617191517000-2f6b7d7b9e43",
            caption="Shiro"
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
            y="quantity",
            title="Remaining Inventory"
        )

        st.plotly_chart(fig, use_container_width=True)

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

        st.plotly_chart(fig, use_container_width=True)

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

    st.plotly_chart(fig, use_container_width=True)


# =================================================
# COMPETITION INTELLIGENCE
# =================================================

with tabs[4]:

    st.subheader("🏆 Ethiopian Restaurant Intelligence")

    restaurants, dishes = load_competitors()

    if restaurants.empty:

        st.info("No competitor data available")

    else:

        fig = px.bar(
            restaurants,
            x="Restaurant",
            y="Rating",
            title="Top Ethiopian Restaurants in NYC"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(restaurants)

        st.subheader("Restaurant Locations")

        map_df = restaurants.dropna(subset=["lat", "lon"])

        if not map_df.empty:

            fig_map = px.scatter_mapbox(
                map_df,
                lat="lat",
                lon="lon",
                hover_name="Restaurant",
                hover_data=["Rating"],
                zoom=12,
                height=450
            )

            fig_map.update_layout(
                mapbox_style="open-street-map",
                margin={"r":0,"t":0,"l":0,"b":0}
            )

            st.plotly_chart(fig_map, use_container_width=True)

    if not dishes.empty:

        st.subheader("Most Mentioned Ethiopian Dishes")

        fig2 = px.bar(
            dishes,
            x="dish",
            y="mentions",
            title="Dish Popularity From Reviews"
        )

        st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(dishes)


# =================================================
# AI INSIGHTS
# =================================================

with tabs[5]:

    st.subheader("AI Restaurant Insights")

    menu = load_menu()

    if not menu.empty:

        top = menu.sort_values("orders", ascending=False).iloc[0]

        st.success(
            f"🔥 {top['item_name']} is your most popular dish"
        )

        revenue = menu["revenue"].sum()

        if revenue > 5000:

            st.info("💰 Your restaurant is performing strongly this week.")

        else:

            st.warning("📈 Consider promoting your top dishes to increase revenue.")