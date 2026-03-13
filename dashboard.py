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
# MOBILE / UI STYLE
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
border-radius:14px;
box-shadow:0 6px 16px rgba(0,0,0,0.4);
}

</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# DATABASE
# -------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    st.error("DATABASE_URL environment variable not set")
    st.stop()

engine = create_engine(DATABASE_URL)

# -------------------------------------------------
# RUN PIPELINE
# -------------------------------------------------

st.markdown("### Data Pipeline")

if st.button("▶ Run Data Pipeline"):

    with st.spinner("Processing invoices, receipts, and competitor data..."):
        run_pipeline.run_pipeline()

    st.success("Pipeline completed!")

if st.button("🔄 Refresh Dashboard"):
    st.cache_data.clear()
    st.rerun()

# -------------------------------------------------
# REFRESH BUTTON
# -------------------------------------------------

if st.button("🔄 Refresh Dashboard"):
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

    # Hard-coded coordinates for stable map
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

    st.markdown("## Restaurant Performance")

    c1,c2,c3 = st.columns(3)

    c1.metric("💰 Revenue",f"${revenue:,.0f}")
    c2.metric("🍽 Orders",int(orders))
    c3.metric("📋 Menu Items",menu["item_name"].nunique())

    fig = px.bar(
        menu,
        x="item_name",
        y="revenue",
        text="revenue",
        title="Revenue by Dish"
    )

    fig.update_layout(xaxis_tickangle=-30)

    st.plotly_chart(fig,use_container_width=True)


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

        st.plotly_chart(fig,use_container_width=True)

        low = inventory[inventory["quantity"] < 200]

        if not low.empty:

            st.error("⚠ Low Inventory")

            st.dataframe(low)


# =================================================
# PURCHASES
# =================================================

with tabs[2]:

    purchases = load_purchases()

    if purchases.empty:
        st.info("No purchase data")

    else:

        fig = px.bar(
            purchases,
            x="ingredient_name",
            y="quantity",
            title="Purchased Ingredients"
        )

        st.plotly_chart(fig,use_container_width=True)

        st.dataframe(purchases)


# =================================================
# MENU
# =================================================

with tabs[3]:

    st.markdown("## 🍽 Popular Ethiopian Dishes")

    menu = load_menu()

    dish_images = {
        "Doro Wat":"https://upload.wikimedia.org/wikipedia/commons/3/33/Doro_Wat.jpg",
        "Kitfo":"https://upload.wikimedia.org/wikipedia/commons/4/4f/Kitfo_Ethiopian.jpg",
        "Shiro":"https://upload.wikimedia.org/wikipedia/commons/0/05/Shiro_Wat.jpg"
    }

    cols = st.columns(3)

    for i,(dish,img) in enumerate(dish_images.items()):

        with cols[i]:

            st.image(img,caption=dish,use_container_width=True)

            if dish in menu["item_name"].values:

                data = menu[menu["item_name"]==dish].iloc[0]

                st.metric("Orders",int(data["orders"]))
                st.metric("Revenue",f"${data['revenue']:,.0f}")


# =================================================
# COMPETITION
# =================================================
# =================================================
# COMPETITION
# =================================================

with tabs[4]:

    st.markdown("## 🏆 Nearby Ethiopian Restaurants")

    # -----------------------------------------------
    # SESSION STATE
    # -----------------------------------------------

    if "restaurants" not in st.session_state:
        st.session_state.restaurants = None

    if "dishes" not in st.session_state:
        st.session_state.dishes = None


    # -----------------------------------------------
    # CONTROL BUTTONS
    # -----------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        if st.button("▶ Run Competitor Scraper"):

            with st.spinner("Collecting competitor intelligence..."):

                restaurants, dishes = load_competitors()

                # ensure coordinates are numeric
                if not restaurants.empty:
                    restaurants["lat"] = pd.to_numeric(restaurants["lat"], errors="coerce")
                    restaurants["lon"] = pd.to_numeric(restaurants["lon"], errors="coerce")

                st.session_state.restaurants = restaurants
                st.session_state.dishes = dishes

            st.success("Competitor data loaded!")

    with col2:

        if st.button("🔄 Refresh Dashboard"):

            st.cache_data.clear()
            st.rerun()

    st.markdown("---")


    # -----------------------------------------------
    # LOAD DATA FROM SESSION
    # -----------------------------------------------

    restaurants = st.session_state.restaurants
    dishes = st.session_state.dishes


    # -----------------------------------------------
    # RESTAURANT DATA
    # -----------------------------------------------

    if restaurants is None or restaurants.empty:

        st.info("Click **Run Competitor Scraper** to load competitor data.")

    else:

        fig = px.bar(
            restaurants,
            x="Restaurant",
            y="Rating",
            title="Top Ethiopian Restaurants in NYC"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(restaurants)

        # -----------------------------------------------
        # MAP
        # -----------------------------------------------

        st.markdown("### Restaurant Locations")

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

        else:

            st.warning("Map coordinates missing.")


    # -----------------------------------------------
    # POPULAR DISHES
    # -----------------------------------------------

    if dishes is not None and not dishes.empty:

        st.markdown("### Popular Dishes in Reviews")

        fig2 = px.bar(
            dishes,
            x="dish",
            y="mentions",
            title="Dish Mentions from Google Reviews"
        )

        st.plotly_chart(fig2, use_container_width=True)


# =================================================
# AI INSIGHTS
# =================================================

with tabs[5]:

    st.markdown("## 🧠 AI Insights")

    menu = load_menu()
    inventory = load_inventory()
    purchases = load_purchases()
    restaurants,dishes = load_competitors()

    insights=[]

    if not menu.empty:

        best = menu.sort_values("orders",ascending=False).iloc[0]
        insights.append(f"🔥 **{best['item_name']}** is your best selling dish ({int(best['orders'])} orders).")

        worst = menu.sort_values("orders").iloc[0]
        insights.append(f"⚠ **{worst['item_name']}** is underperforming ({int(worst['orders'])} orders).")

    if not inventory.empty:

        low = inventory[inventory["quantity"]<200]

        if not low.empty:

            item = low.iloc[0]

            insights.append(f"📦 Low inventory alert: **{item['ingredient_name']}** only {int(item['quantity'])} left.")

    if not purchases.empty:

        cost = purchases.sort_values("total_cost",ascending=False).iloc[0]

        insights.append(f"💰 Highest spending ingredient: **{cost['ingredient_name']}** (${cost['total_cost']:.2f}).")

    if not dishes.empty:

        pop = dishes.sort_values("mentions",ascending=False).iloc[0]

        insights.append(f"🏆 Competitors receive many reviews mentioning **{pop['dish']}** ({pop['mentions']} mentions).")

    if insights:

        for i in insights:

            st.success(i)

    else:

        st.info("Not enough data yet to generate insights.")