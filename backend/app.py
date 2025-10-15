import streamlit as st
import pandas as pd
import requests
import pydeck as pdk

# ==========================
# CONFIGURATION
# ==========================
API_TOKEN = "97a0e712f47007556b57ab4b14843e72b416c0f9"
DELHI_BOUNDS = "28.404,76.840,28.883,77.349"

# ==========================
# HELPER FUNCTIONS
# ==========================
def get_aqi_category(aqi):
    if aqi <= 50:
        return "Good", [0, 228, 0], "No risk", "✅"
    elif aqi <= 100:
        return "Moderate", [255, 255, 0], "Minor breathing discomfort for sensitive people", "🤔"
    elif aqi <= 150:
        return "Unhealthy for Sensitive", [255, 126, 0], "Breathing discomfort for sensitive groups", "😷"
    elif aqi <= 200:
        return "Unhealthy", [255, 0, 0], "Breathing discomfort for most people", "🔴"
    elif aqi <= 300:
        return "Very Unhealthy", [143, 63, 151], "Respiratory illness on prolonged exposure", "🟣"
    else:
        return "Hazardous", [126, 0, 35], "Serious respiratory impacts", "☠️"

# ==========================
# FETCH LIVE DATA
# ==========================
@st.cache_data(ttl=600)
def fetch_live_data():
    url = "https://api.waqi.info/map/bounds/"
    params = {"latlng": DELHI_BOUNDS, "token": API_TOKEN}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("status") == "ok":
            df = pd.DataFrame(data["data"])
            df = df[df['aqi'] != "-"]
            df['aqi'] = df['aqi'].astype(float)
            df['station_name'] = df['station'].apply(lambda x: x.get('name', 'N/A'))
            df['last_updated'] = df['station'].apply(lambda x: x.get('time', 'N/A'))
            df['category'], df['color'], df['action'], df['emoji'] = zip(*df['aqi'].map(get_aqi_category))
            df['lat'] = df['lat'].astype(float)
            df['lon'] = df['lon'].astype(float)
            return df
        else:
            return pd.DataFrame()
    except:
        return pd.DataFrame()

# ==========================
# CUSTOM CSS
# ==========================
def local_css():
    st.markdown("""
        <style>
        .card {
            background-color: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 15px;
            transition: all 0.2s;
        }
        .card:hover {
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
            transform: translateY(-3px);
        }
        .metric-label { color: #64748B; font-size: 0.9rem; }
        .metric-value { font-size: 2rem; font-weight: 700; color: #1E40AF; }
        .alert-card { border-left: 5px solid; padding: 10px; border-radius: 8px; margin-bottom: 10px; background-color: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
        .alert-hazardous { border-color: #7E0023; }
        .alert-very-unhealthy { border-color: #8F3F97; }
        .alert-unhealthy { border-color: #FF0000; }
        .station-name { font-weight: 600; color: #334155; }
        .aqi-value { float: right; font-weight: bold; }
        header, footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

# ==========================
# UI COMPONENTS
# ==========================
def render_map_tab(df):
    st.subheader("📍 Live Air Quality Map")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='card'><p class='metric-label'>Average AQI</p><p class='metric-value'>{df['aqi'].mean():.1f}</p></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='card'><p class='metric-label'>Min AQI</p><p class='metric-value'>{df['aqi'].min():.0f}</p><p class='metric-label'>{df.loc[df['aqi'].idxmin()]['station_name']}</p></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='card'><p class='metric-label'>Max AQI</p><p class='metric-value'>{df['aqi'].max():.0f}</p><p class='metric-label'>{df.loc[df['aqi'].idxmax()]['station_name']}</p></div>", unsafe_allow_html=True)

    # Pydeck ScatterplotLayer for pins
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_fill_color='color',
        get_radius=400,
        pickable=True,
        opacity=0.8,
        stroked=True,
        get_line_color=[0,0,0],
        line_width_min_pixels=1
    )

    tooltip = {
        "html": "<b>{station_name}</b><br/>AQI: {aqi}<br/>Category: {category}<br/>Last Updated: {last_updated}",
        "style": {"backgroundColor": "steelblue", "color": "white", "borderRadius": "5px", "padding": "10px"}
    }

    st.pydeck_chart(pdk.Deck(
        map_style="open-street-map",
        initial_view_state=pdk.ViewState(
            latitude=28.6139,
            longitude=77.2090,
            zoom=10,
            pitch=0,
        ),
        layers=[layer],
        tooltip=tooltip
    ))

def render_alerts_tab(df):
    st.subheader("🔔 Health Alerts & Recommendations")
    alert_levels = {
        "Hazardous": df[df['aqi'] > 300],
        "Very Unhealthy": df[(df['aqi'] > 200) & (df['aqi'] <= 300)],
        "Unhealthy": df[(df['aqi'] > 150) & (df['aqi'] <= 200)]
    }
    has_alerts = False
    for level, subset in alert_levels.items():
        if not subset.empty:
            has_alerts = True
            st.markdown(f"### {subset.iloc[0]['emoji']} {level}")
            for _, row in subset.sort_values('aqi', ascending=False).iterrows():
                alert_class = f"alert-{level.lower().replace(' ', '-')}"
                st.markdown(f"<div class='alert-card {alert_class}'><span class='aqi-value'>{row['aqi']:.0f}</span><span class='station-name'>{row['station_name']}</span></div>", unsafe_allow_html=True)
    if not has_alerts:
        st.success("✅ No major health alerts.")

def render_analytics_tab(df):
    st.subheader("📈 Analytics")
    avg_aqi = df['aqi'].mean()
    st.metric("Average AQI", f"{avg_aqi:.1f}")
    st.bar_chart(df.set_index('station_name')['aqi'].sort_values(ascending=False))

# ==========================
# MAIN APP
# ==========================
def main():
    local_css()
    st.sidebar.title("🌬️ Delhi Air Quality")
    st.sidebar.markdown("Monitor real-time AQI across Delhi NCR.")
    page = st.sidebar.radio("Navigate", ["Dashboard", "Alerts", "Analytics"], label_visibility="hidden")
    df = fetch_live_data()
    if df.empty:
        st.warning("⚠️ Could not fetch live AQI data.")
    else:
        if page == "Dashboard":
            render_map_tab(df)
        elif page == "Alerts":
            render_alerts_tab(df)
        elif page == "Analytics":
            render_analytics_tab(df)

if __name__ == "__main__":
    main()
