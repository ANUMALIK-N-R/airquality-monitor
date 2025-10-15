import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import plotly.express as px

# ==========================
# CONFIGURATION
# ==========================
st.set_page_config(layout="wide", page_title="Delhi NCR Air Quality", page_icon="💨")

API_TOKEN = "97a0e712f47007556b57ab4b14843e72b416c0f9"
DELHI_BOUNDS = "28.404,76.840,28.883,77.349"

# ==========================
# HELPER FUNCTIONS
# ==========================
def get_aqi_category(aqi):
    """Return AQI category, color, and health advice."""
    if aqi <= 50:
        return "Good", "rgb(0, 228, 0)", "No risk", "✅"
    elif aqi <= 100:
        return "Moderate", "rgb(255, 255, 0)", "Minor breathing discomfort", "🤔"
    elif aqi <= 150:
        return "Unhealthy for Sensitive", "rgb(255, 126, 0)", "Discomfort for sensitive groups", "😷"
    elif aqi <= 200:
        return "Unhealthy", "rgb(255, 0, 0)", "Discomfort for most people", "🔴"
    elif aqi <= 300:
        return "Very Unhealthy", "rgb(143, 63, 151)", "Respiratory illness on prolonged exposure", "⚠️"
    else:
        return "Hazardous", "rgb(126, 0, 35)", "Serious impacts even for healthy people", "☠️"

def rgb_to_list(rgb_str):
    """Convert 'rgb(R,G,B)' to [R,G,B] list."""
    rgb_str = rgb_str.replace("rgb(", "").replace(")", "")
    return [int(x) for x in rgb_str.split(",")]

# ==========================
# CUSTOM CSS
# ==========================
def local_css():
    st.markdown("""
    <style>
        body { font-family: 'Inter', sans-serif; }
        .main { background-color: #F0F2F6; }
        .card { background-color: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom:20px; }
        .card-title { font-size: 1.5em; font-weight: 600; color:#1E293B; margin-bottom:15px; }
        .metric-value { font-size: 2.5em; font-weight:700; color:#007BFF; }
        .metric-label { font-size:1em; color:#64748B; }
        .alert-card { border-left:5px solid; padding:15px; border-radius:8px; margin-bottom:10px; background-color:#FFF; box-shadow:0 2px 4px rgba(0,0,0,0.05); }
        .alert-hazardous { border-color:#7E0023; }
        .alert-very-unhealthy { border-color:#8F3F97; }
        .alert-unhealthy { border-color:#FF0000; }
        .station-name { font-weight:600; color:#334155; }
        .aqi-value { float:right; font-weight:bold; }
        [data-testid="stSidebar"] { background-color:#FFFFFF; border-right:1px solid #E2E8F0; }
        header, footer { visibility:hidden; }
    </style>
    """, unsafe_allow_html=True)

# ==========================
# DATA FETCHING
# ==========================
@st.cache_data(ttl=600)
def fetch_live_data():
    url = f"https://api.waqi.info/map/bounds/?latlng={DELHI_BOUNDS}&token={API_TOKEN}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ok":
            df = pd.DataFrame(data["data"])
            df = df[df['aqi'] != "-"]
            df['aqi'] = pd.to_numeric(df['aqi'])
            df['station_name'] = df['station'].apply(lambda x: x.get('name', 'N/A'))
            df['last_updated'] = df['station'].apply(lambda x: x.get('time', 'N/A'))
            df['category'], df['color_rgb'], df['action'], df['emoji'] = zip(*df['aqi'].map(get_aqi_category))
            df['lat'] = pd.to_numeric(df['lat'])
            df['lon'] = pd.to_numeric(df['lon'])
            df['color_list'] = df['color_rgb'].apply(rgb_to_list)
            return df
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return pd.DataFrame()

# ==========================
# UI COMPONENTS
# ==========================
def render_map_tab(df):
    st.markdown("<p class='card-title'>📍 Live Air Quality Map</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='card'><p class='metric-label'>Average AQI</p><p class='metric-value'>{df['aqi'].mean():.1f}</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='card'><p class='metric-label'>Min AQI</p><p class='metric-value'>{df['aqi'].min():.0f}</p><p class='metric-label'>{df.loc[df['aqi'].idxmin()]['station_name']}</p></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='card'><p class='metric-label'>Max AQI</p><p class='metric-value'>{df['aqi'].max():.0f}</p><p class='metric-label'>{df.loc[df['aqi'].idxmax()]['station_name']}</p></div>", unsafe_allow_html=True)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_fill_color="color_list",
        get_radius=400,
        pickable=True,
        opacity=0.8,
        stroked=True,
        get_line_color=[0, 0, 0],
        line_width_min_pixels=1,
    )

    tooltip = {
        "html": "<b>{station_name}</b><br/>AQI: {aqi}<br/>Category: {category}<br/>Last Updated: {last_updated}",
        "style": {"backgroundColor":"steelblue","color":"white","borderRadius":"5px","padding":"10px"}
    }

    st.pydeck_chart(pdk.Deck(
        map_style="open-street-map",
        initial_view_state=pdk.ViewState(
            latitude=28.6139,
            longitude=77.2090,
            zoom=10,
            pitch=0
        ),
        layers=[layer],
        tooltip=tooltip
    ))

def render_alerts_tab(df):
    st.markdown("<p class='card-title'>🔔 Health Alerts & Recommendations</p>", unsafe_allow_html=True)
    alert_levels = {
        "Hazardous": df[df['aqi'] > 300],
        "Very Unhealthy": df[(df['aqi'] > 200) & (df['aqi'] <= 300)],
        "Unhealthy": df[(df['aqi'] > 150) & (df['aqi'] <= 200)]
    }
    has_alerts = False
    for level, subset in alert_levels.items():
        if not subset.empty:
            has_alerts = True
            st.markdown(f"### {subset.iloc[0]['emoji']} {level} (AQI > {subset['aqi'].min():.0f})")
            st.info(f"**Health Implication:** {subset.iloc[0]['action']}")
            for _, row in subset.sort_values('aqi', ascending=False).iterrows():
                alert_class = f"alert-{level.lower().replace(' ', '-')}"
                st.markdown(f"<div class='alert-card {alert_class}'><span class='aqi-value'>{row['aqi']:.0f}</span><span class='station-name'>{row['station_name']}</span></div>", unsafe_allow_html=True)
    if not has_alerts:
        st.success("✅ No major health alerts. Air quality is within acceptable limits.")

def render_analytics_tab(df):
    st.markdown("<p class='card-title'>📈 Data Analytics</p>", unsafe_allow_html=True)
    category_counts = df['category'].value_counts()
    fig = px.pie(
        values=category_counts.values,
        names=category_counts.index,
        hole=.3,
        color=category_counts.index,
        color_discrete_map={
            "Good":"green",
            "Moderate":"yellow",
            "Unhealthy for Sensitive":"orange",
            "Unhealthy":"red",
            "Very Unhealthy":"purple",
            "Hazardous":"maroon"
        }
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.bar_chart(df.set_index('station_name')['aqi'].sort_values(ascending=False))

# ==========================
# MAIN APP
# ==========================
def main():
    local_css()
    st.sidebar.title("🌬️ Delhi Air Quality")
    st.sidebar.markdown("Monitor Air Quality Index (AQI) across Delhi NCR in real-time.")
    page = st.sidebar.radio("Navigate", ["Dashboard", "Alerts", "Analytics"], label_visibility="hidden")
    st.sidebar.markdown("---")
    st.sidebar.info("Data is updated every 10 minutes from the World Air Quality Index Project.")

    df = fetch_live_data()
    if df.empty:
        st.warning("⚠️ Could not fetch live AQI data. Please try again later.")
    else:
        if page == "Dashboard":
            render_map_tab(df)
        elif page == "Alerts":
            render_alerts_tab(df)
        elif page == "Analytics":
            render_analytics_tab(df)

if __name__ == "__main__":
    main()
