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
# CUSTOM CSS
# ==========================
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 50%, #90CAF9 100%);
    }
    
    /* Main Container */
    .main {
        padding: 2rem;
    }
    
    /* Header */
    .header-container {
        background: transparent;
        padding: 1.5rem 0;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-title {
        font-size: 3.5rem;
        font-weight: 900;
        color: #0D47A1;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(13, 71, 161, 0.2);
        letter-spacing: -1px;
    }
    
    .subtitle {
        color: #1565C0;
        font-size: 1.2rem;
        font-weight: 500;
    }
    
    /* Navigation Tabs */
    .stRadio > div {
        background: transparent;
        padding: 0;
        border-radius: 0;
        box-shadow: none;
        margin-bottom: 2.5rem;
        border: none;
    }
    
    .stRadio > div > label {
        display: flex;
        gap: 1.5rem;
        justify-content: center;
        flex-wrap: wrap;
    }
    
    .stRadio > div > label > div {
        background: white !important;
        color: #1565C0 !important;
        padding: 1rem 2.5rem !important;
        border-radius: 50px !important;
        transition: all 0.3s ease;
        cursor: pointer;
        font-weight: 600;
        font-size: 1.1rem;
        box-shadow: 0 4px 15px rgba(33, 150, 243, 0.2);
        border: 2px solid #BBDEFB !important;
    }
    
    .stRadio > div > label > div:hover {
        background: #E3F2FD !important;
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(33, 150, 243, 0.3);
    }
    
    /* Content Cards */
    .content-card {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(33, 150, 243, 0.2);
        margin-bottom: 1.5rem;
        border: 2px solid #BBDEFB;
    }
    
    .section-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1565C0;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Map Container */
    .map-container {
        background: white;
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(33, 150, 243, 0.2);
        border: 2px solid #BBDEFB;
    }
    
    /* Alert Cards */
    .alert-card {
        background: linear-gradient(135deg, #EF5350 0%, #E53935 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        box-shadow: 0 5px 20px rgba(239, 83, 80, 0.3);
    }
    
    .alert-card-warning {
        background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
    }
    
    .alert-card-caution {
        background: linear-gradient(135deg, #FFA726 0%, #FB8C00 100%);
    }
    
    .alert-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: white;
    }
    
    .alert-item {
        background: rgba(255,255,255,0.25);
        padding: 0.75rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        backdrop-filter: blur(10px);
        color: white;
    }
    
    /* Metrics */
    .metric-container {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        color: white;
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(33, 150, 243, 0.3);
    }
    
    .metric-label {
        font-size: 1rem;
        opacity: 0.95;
        margin-bottom: 0.5rem;
        color: white;
    }
    
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
        color: white;
    }
    
    /* Charts */
    div[data-testid="stMetric"] {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(33, 150, 243, 0.15);
        border: 2px solid #E3F2FD;
    }
    
    div[data-testid="stMetric"] label {
        color: #1565C0 !important;
        font-weight: 600;
    }
    
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #1976D2 !important;
    }
    
    /* Markdown Headers in Cards */
    .content-card h3 {
        color: #1565C0;
        font-weight: 700;
    }
    
    /* Warning Messages */
    .stWarning {
        background: white;
        border-left: 5px solid #FF9800;
        border-radius: 10px;
        padding: 1.5rem;
        color: #E65100;
    }
    
    .stSuccess {
        background: white;
        border-left: 5px solid #4CAF50;
        border-radius: 10px;
        padding: 1.5rem;
        color: #2E7D32;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================
# HELPER FUNCTIONS
# ==========================
def get_aqi_category(aqi):
    if aqi <= 50:
        return "Good", [0, 228, 0]
    elif aqi <= 100:
        return "Moderate", [255, 255, 0]
    elif aqi <= 150:
        return "Unhealthy for Sensitive", [255, 126, 0]
    elif aqi <= 200:
        return "Unhealthy", [255, 0, 0]
    elif aqi <= 300:
        return "Very Unhealthy", [143, 63, 151]
    else:
        return "Hazardous", [126, 0, 35]

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
            df['category'], df['color'] = zip(*df['aqi'].map(get_aqi_category))
            df['lat'] = df['lat'].astype(float)
            df['lon'] = df['lon'].astype(float)
            return df
        else:
            return pd.DataFrame()
    except:
        return pd.DataFrame()

# ==========================
# STREAMLIT UI
# ==========================
st.set_page_config(layout="wide", page_title="Delhi NCR Air Quality", page_icon="🌍")

# Header
st.markdown("""
<div class="header-container">
    <div class="main-title">🌍 Delhi NCR Air Quality Monitor</div>
    <div class="subtitle">Real-time Air Quality Index tracking across Delhi NCR region</div>
</div>
""", unsafe_allow_html=True)

# Navigation
tab = st.radio("", ["🗺️ Live Map", "🔔 Alerts", "📊 Analytics"], horizontal=True, label_visibility="collapsed")

# Fetch Data
df = fetch_live_data()

if df.empty:
    st.warning("⚠️ Could not fetch live AQI data. Please check your connection and try again.")
else:
    if tab == "🗺️ Live Map":
        st.markdown('<div class="map-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🗺️ Interactive Air Quality Map</div>', unsafe_allow_html=True)

        # Pydeck ScatterplotLayer for pins
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position='[lon, lat]',
            get_fill_color='color',
            get_radius=300,
            pickable=True,
        )

        tooltip = {
            "html": "<b>{station_name}</b><br/>AQI: {aqi}<br/>Category: {category}<br/>Last Updated: {last_updated}",
            "style": {"color": "white"}
        }

        st.pydeck_chart(pdk.Deck(
            map_style="light",
            initial_view_state=pdk.ViewState(
                latitude=28.6139,
                longitude=77.2090,
                zoom=10,
                pitch=0,
            ),
            layers=[layer],
            tooltip=tooltip
        ))
        st.markdown('</div>', unsafe_allow_html=True)

    elif tab == "🔔 Alerts":
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🔔 Active Air Quality Alerts</div>', unsafe_allow_html=True)
        
        hazardous = df[df['aqi'] > 300]
        very_unhealthy = df[(df['aqi'] > 200) & (df['aqi'] <= 300)]
        unhealthy = df[(df['aqi'] > 150) & (df['aqi'] <= 200)]

        def show_alerts(title, subset, card_class):
            if not subset.empty:
                st.markdown(f'<div class="alert-card {card_class}">', unsafe_allow_html=True)
                st.markdown(f'<div class="alert-title">{title}</div>', unsafe_allow_html=True)
                for _, row in subset.iterrows():
                    st.markdown(f'<div class="alert-item"><b>{row["station_name"]}</b>: AQI {row["aqi"]:.0f}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        show_alerts("🚨 Hazardous Conditions (AQI > 300)", hazardous, "")
        show_alerts("⚠️ Very Unhealthy (AQI 201-300)", very_unhealthy, "alert-card-warning")
        show_alerts("⚡ Unhealthy (AQI 151-200)", unhealthy, "alert-card-caution")

        if hazardous.empty and very_unhealthy.empty and unhealthy.empty:
            st.success("✅ No active alerts. Air quality is within acceptable levels.")
        
        st.markdown('</div>', unsafe_allow_html=True)

    elif tab == "📊 Analytics":
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📊 Air Quality Analytics</div>', unsafe_allow_html=True)
        
        avg_aqi = df['aqi'].mean()
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Average AQI Across All Stations</div>
            <div class="metric-value">{avg_aqi:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📍 Station-wise AQI Levels")
            st.bar_chart(df.set_index('station_name')['aqi'])
        
        with col2:
            st.markdown("### 📈 Distribution Statistics")
            st.metric("Highest AQI", f"{df['aqi'].max():.0f}", delta=None)
            st.metric("Lowest AQI", f"{df['aqi'].min():.0f}", delta=None)
            st.metric("Total Stations", len(df))
        
        st.markdown('</div>', unsafe_allow_html=True)
