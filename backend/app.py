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
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Main Container */
    .main {
        padding: 2rem;
    }
    
    /* Header */
    .header-container {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        color: #666;
        font-size: 1.1rem;
        font-weight: 400;
    }
    
    /* Navigation Tabs */
    .stRadio > div {
        background: white;
        padding: 1rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
    }
    
    .stRadio > div > label {
        display: flex;
        gap: 1rem;
        justify-content: center;
    }
    
    .stRadio > div > label > div {
        background: #f8f9fa !important;
        padding: 0.75rem 2rem !important;
        border-radius: 10px !important;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .stRadio > div > label > div:hover {
        background: #e9ecef !important;
        transform: translateY(-2px);
    }
    
    /* Content Cards */
    .content-card {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
    }
    
    .section-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #333;
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
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }
    
    /* Alert Cards */
    .alert-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin-bottom: 1rem;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
    }
    
    .alert-card-warning {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    }
    
    .alert-card-caution {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
    }
    
    .alert-title {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    .alert-item {
        background: rgba(255,255,255,0.2);
        padding: 0.75rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        backdrop-filter: blur(10px);
    }
    
    /* Metrics */
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.15);
    }
    
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
    }
    
    /* Charts */
    div[data-testid="stMetric"] {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
    }
    
    /* Warning Messages */
    .stWarning {
        background: white;
        border-left: 5px solid #ff6b6b;
        border-radius: 10px;
        padding: 1.5rem;
    }
    
    .stSuccess {
        background: white;
        border-left: 5px solid #51cf66;
        border-radius: 10px;
        padding: 1.5rem;
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
