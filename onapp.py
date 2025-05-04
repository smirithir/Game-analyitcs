import streamlit as st
import pandas as pd
import mysql.connector
import seaborn as sns
import matplotlib.pyplot as plt
from streamlit_option_menu import option_menu

# ---------- SETUP ----------
st.set_page_config(page_title="Tennis Competitor Analytics", layout="wide")

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="MySql@123",
        database="gamedata_db"
    )

def fetch_query(query, params=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params or ())
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return pd.DataFrame(results)

# ---------- SIDEBAR MENU ----------
with st.sidebar:
    selected = option_menu(
        menu_title="📂 Navigation Menu",
        options=["Overview", "Filter Competitors", "Competitor Details", "Country Analysis"],
        icons=["bar-chart", "funnel-fill", "person-lines-fill", "globe2"],
        menu_icon="list",
        default_index=0,
    )

# ---------- OVERVIEW PAGE ----------
if selected == "Overview":
    st.title("🎾 Tennis Competitor Analytics")

    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        total = fetch_query("SELECT COUNT(*) AS total FROM Competitors")
        st.metric("Total Competitors", total['total'][0] if not total.empty else 0)

    with col2:
        countries = fetch_query("SELECT COUNT(DISTINCT country) AS countries FROM Competitors")
        st.metric("Countries Represented", countries['countries'][0] if not countries.empty else 0)

    with col3:
        highest = fetch_query("""
            SELECT name, points FROM Competitors c 
            JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id 
            ORDER BY points DESC LIMIT 1
        """)
        if not highest.empty:
            st.metric("Highest Points", highest['points'][0], highest['name'][0])
        else:
            st.metric("Highest Points", 0)

    # Rankings Table
    st.subheader("📋 Full Competitor Rankings")
    rankings = fetch_query("""
        SELECT c.name, c.country, cr.rank, cr.points, cr.competitions_played, cr.movement
        FROM Competitors c
        JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
        ORDER BY cr.rank ASC
    """)
    st.dataframe(rankings, use_container_width=True)

    # Leaderboard Chart
    st.subheader("🏅 Leaderboard (Top 10 by Points)")
    top_points = fetch_query("""
        SELECT c.name, cr.points FROM Competitors c
        JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
        ORDER BY cr.points DESC LIMIT 10
    """)
    if not top_points.empty:
        st.bar_chart(top_points.set_index("name"))

    st.subheader("📈 Top 5 Rank Movers")
    movers = fetch_query("""
            SELECT c.name, cr.movement 
            FROM Competitors c
            JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
            WHERE cr.movement > 0
            ORDER BY cr.movement DESC LIMIT 5
        """)
    st.table(movers if not movers.empty else pd.DataFrame({"No Movers": []}))

# ---------- FILTER COMPETITORS ----------
elif selected == "Filter Competitors":
    st.title("🔍 Filter Competitors")

    name_input = st.text_input("Search by name")
    min_rank = st.slider("Rank Range", 1, 100, (1, 50))
    min_points = st.number_input("Minimum Points", 0, 10000, 0)

    countries_list = fetch_query("SELECT DISTINCT country FROM Competitors")['country']
    country = st.selectbox("Filter by Country", options=["All"] + list(countries_list))

    query = """
    SELECT c.name, c.country, cr.rank, cr.points
    FROM Competitors c
    JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
    WHERE c.name LIKE %s AND cr.rank BETWEEN %s AND %s AND cr.points >= %s
    """
    params = (f"%{name_input}%", min_rank[0], min_rank[1], min_points)

    if country != "All":
        query += " AND c.country = %s"
        params += (country,)

    filtered_df = fetch_query(query, params)

    st.dataframe(filtered_df if not filtered_df.empty else pd.DataFrame({"No Data": []}), use_container_width=True)

# ---------- COMPETITOR DETAILS ----------
elif selected == "Competitor Details":
    st.title("👤 Competitor Details")

    competitors = fetch_query("SELECT DISTINCT name FROM Competitors")
    if not competitors.empty:
        selected_name = st.selectbox("Select a Competitor", competitors['name'])
        details = fetch_query("""
            SELECT c.name, c.country, cr.rank, cr.points, cr.movement, cr.competitions_played
            FROM Competitors c
            JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
            WHERE c.name = %s
        """, (selected_name,))
        st.write(details.T)
    else:
        st.warning("No competitors found.")

# ---------- COUNTRY ANALYSIS ----------
elif selected == "Country Analysis":
    st.title("🌍 Country-Wise Analysis")

    country_stats = fetch_query("""
        SELECT c.country, COUNT(*) AS total_competitors, AVG(cr.points) AS avg_points
        FROM Competitors c
        JOIN Competitor_Rankings cr ON c.competitor_id = cr.competitor_id
        GROUP BY c.country
        ORDER BY avg_points DESC
    """)
    if not country_stats.empty:
        st.dataframe(country_stats, use_container_width=True)
        st.bar_chart(country_stats.set_index("country")["avg_points"])

        # Box Plot Here
        df = fetch_query("""
            SELECT c.country, cr.points 
            FROM Competitor_Rankings cr 
            JOIN Competitors c ON c.competitor_id = cr.competitor_id
        """)
        if not df.empty:
            st.subheader("📦 Points Distribution by Country (Box Plot)")
            fig, ax = plt.subplots(figsize=(12, 6))
            sns.boxplot(x="country", y="points", data=df, ax=ax)
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
            st.pyplot(fig)
    else:
        st.warning("No country data available.")

