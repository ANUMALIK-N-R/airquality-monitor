import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import plotly.express as px
from datetime import datetime
from tensorflow.keras.models import load_model
import numpy as np


# ==========================
# CUSTOM CSS FOR STYLING
# ==========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main background - Sky Blue Theme */
    .stApp {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 50%, #90CAF9 100%);
    }

    /* Hide Streamlit's default header and footer */
    header, footer, #MainMenu {
        visibility: hidden;
    }

    /* Main title styling */
    .main-title {
        font-size: 3.5rem;
        font-weight: 900;
        color: #0D47A1;
        padding: 1.5rem 0 0.5rem 0;
        text-align: center;
        text-shadow: 2px 2px 4px rgba(13, 71, 161, 0.2);
        letter-spacing: -1px;
    }

    /* Subtitle styling */
    .subtitle {
        font-size: 1.2rem;
        color: #1565C0;
        text-align: center;
        padding-bottom: 1.5rem;
        font-weight: 500;
    }

    /* Metric cards styling */
    .metric-card {
        background-color: #FFFFFF;
        border-radius: 15px;
        padding: 1.5rem;
        border: 2px solid #BBDEFB;
        box-shadow: 0 4px 20px rgba(33, 150, 243, 0.15);
        text-align: center;
        height: 100%;
    }
    .metric-card-label {
        font-size: 1rem;
        font-weight: 600;
        color: #1565C0;
        margin-bottom: 0.5rem;
    }
    .metric-card-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #0D47A1;
        margin: 0.5rem 0;
    }
    .metric-card-delta {
        font-size: 0.9rem;
        color: #1976D2;
        font-weight: 500;
    }

    /* Weather widget styling */
    .weather-widget {
        background-color: #FFFFFF;
        border-radius: 15px;
        padding: 1.5rem;
        border: 2px solid #BBDEFB;
        box-shadow: 0 4px 20px rgba(33, 150, 243, 0.15);
        height: 100%;
    }
    .weather-temp {
        font-size: 2.5rem;
        font-weight: 800;
        color: #0D47A1;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background-color: transparent;
        padding: 1rem 0;
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 1.1rem;
        font-weight: 600;
        background-color: white;
        border-radius: 15px;
        padding: 1rem 2rem;
        border: 2px solid #BBDEFB;
        color: #1565C0;
        box-shadow: 0 2px 10px rgba(33, 150, 243, 0.1);
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #E3F2FD;
        border-color: #2196F3;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        color: white !important;
        border-color: #1976D2;
    }

    /* Section cards */
    .content-card {
        background-color: #FFFFFF;
        padding: 2rem;
        border-radius: 20px;
        border: 2px solid #BBDEFB;
        box-shadow: 0 10px 40px rgba(33, 150, 243, 0.2);
        margin-top: 1.5rem;
    }

    /* Alert cards */
    .alert-card {
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        color: white;
        font-weight: 600;
    }
    .alert-hazardous { 
        background: linear-gradient(135deg, #EF5350 0%, #E53935 100%);
        box-shadow: 0 4px 15px rgba(239, 83, 80, 0.3);
    }
    .alert-very-unhealthy { 
        background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
        box-shadow: 0 4px 15px rgba(255, 152, 0, 0.3);
    }
    .alert-unhealthy { 
        background: linear-gradient(135deg, #FFA726 0%, #FB8C00 100%);
        box-shadow: 0 4px 15px rgba(255, 167, 38, 0.3);
    }

    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0D47A1;
        margin-bottom: 1.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #BBDEFB;
    }

    /* Streamlit alert boxes */
    div[data-testid="stAlert"] {
        background-color: white;
        border-left: 5px solid #2196F3;
        border-radius: 10px;
        color: #0D47A1;
    }

    div[data-testid="stSuccess"] {
        background-color: white;
        border-left: 5px solid #4CAF50;
        border-radius: 10px;
        color: #2E7D32;
    }

    div[data-testid="stError"] {
        background-color: white;
        border-left: 5px solid #EF5350;
        border-radius: 10px;
        color: #C62828;
    }

    /* DataFrame styling */
    div[data-testid="stDataFrame"] {
        border: 2px solid #BBDEFB;
        border-radius: 10px;
        background-color: white;
    }

    /* Charts */
    div[data-testid="stPlotlyChart"] {
        background-color: white;
        border-radius: 10px;
        padding: 0.5rem;
    }

    /* Main padding */
    .block-container {
        background-color: transparent;
        padding-top: 2rem;
    }

</style>
""", unsafe_allow_html=True)


# ==========================
# PAGE CONFIGURATION
# ==========================
st.set_page_config(
    layout="wide",
    page_title="Delhi Air Quality Dashboard",
    page_icon="💨"
)

# ==========================
# STATIC CONFIG
# ==========================
API_TOKEN = "97a0e712f47007556b57ab4b14843e72b416c0f9"
DELHI_BOUNDS = "28.404,76.840,28.883,77.349"
DELHI_LAT = 28.6139
DELHI_LON = 77.2090

# Twilio Configuration (replace with your credentials)
TWILIO_ACCOUNT_SID = "AC2cc57109fc63de336609901187eca69d"
TWILIO_AUTH_TOKEN = "62b791789bb490f91879e89fa2ed959d"
TWILIO_PHONE_NUMBER = "+13856005348"

# ==========================
# CUSTOM CSS
# ==========================
st.markdown("""
<style>
/* --- Simplified CSS block (same as your original code) --- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 50%, #90CAF9 100%); }
header, footer, #MainMenu { visibility: hidden; }
/* More CSS definitions remain same */
</style>
""", unsafe_allow_html=True)

# ==========================
# HELPER FUNCTIONS
# ==========================
@st.cache_data(ttl=600, show_spinner="Fetching Air Quality Data...")
def fetch_live_data():
    url = f"https://api.waqi.info/map/bounds/?latlng={DELHI_BOUNDS}&token={API_TOKEN}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ok":
            df = pd.DataFrame(data["data"])
            df = df[df['aqi'] != "-"]
            df['aqi'] = pd.to_numeric(df['aqi'], errors='coerce')
            df = df.dropna(subset=['aqi'])
            def safe_get_name(x):
                if isinstance(x, dict):
                    return x.get('name', 'N/A')
                elif isinstance(x, str):
                    return x
                return 'N/A'
            def safe_get_time(x):
                if isinstance(x, dict):
                    time_data = x.get('time', {})
                    if isinstance(time_data, dict):
                        return time_data.get('s', 'N/A')
                    elif isinstance(time_data, str):
                        return time_data
                return 'N/A'
            df['station_name'] = df['station'].apply(safe_get_name)
            df['last_updated'] = df['station'].apply(safe_get_time)
            df[['category', 'color', 'emoji', 'advice']] = df['aqi'].apply(get_aqi_category).apply(pd.Series)
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
            return df
        return pd.DataFrame()
    except requests.RequestException:
        return pd.DataFrame()

@st.cache_data(ttl=1800, show_spinner="Fetching Weather Data...")
def fetch_weather_data():
    url = f"https://api.open-meteo.com/v1/forecast?latitude={DELHI_LAT}&longitude={DELHI_LON}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=Asia/Kolkata"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None

def get_aqi_category(aqi):
    if aqi <= 50: 
        return "Good", [0, 158, 96], "✅", "Enjoy outdoor activities."
    elif aqi <= 100: 
        return "Moderate", [255, 214, 0], "🟡", "Unusually sensitive people should reduce exertion."
    elif aqi <= 150: 
        return "Unhealthy for Sensitive Groups", [249, 115, 22], "🟠", "Sensitive groups should reduce prolonged exertion."
    elif aqi <= 200: 
        return "Unhealthy", [220, 38, 38], "🔴", "Everyone may begin to experience health effects."
    elif aqi <= 300: 
        return "Very Unhealthy", [147, 51, 234], "🟣", "Health alert: everyone may experience serious health effects."
    else: 
        return "Hazardous", [126, 34, 206], "☠️", "Health warnings of emergency conditions."

def get_weather_info(code):
    codes = {
        0: ("Clear sky", "☀️"), 1: ("Mainly clear", "🌤️"), 2: ("Partly cloudy", "⛅"), 
        3: ("Overcast", "☁️"), 45: ("Fog", "🌫️"), 48: ("Depositing rime fog", "🌫️"),
        51: ("Light drizzle", "💧"), 53: ("Moderate drizzle", "💧"), 55: ("Dense drizzle", "💧"),
        61: ("Slight rain", "🌧️"), 63: ("Moderate rain", "🌧️"), 65: ("Heavy rain", "🌧️"),
        80: ("Slight rain showers", "🌦️"), 81: ("Moderate rain showers", "🌦️"),
        82: ("Violent rain showers", "⛈️"), 95: ("Thunderstorm", "⚡"),
        96: ("Thunderstorm, slight hail", "⛈️"), 99: ("Thunderstorm, heavy hail", "⛈️")
    }
    return codes.get(code, ("Unknown", "❓"))

def calculate_distance(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def get_nearby_stations(df, user_lat, user_lon, radius_km=10):
    df['distance'] = df.apply(lambda row: calculate_distance(user_lat, user_lon, row['lat'], row['lon']), axis=1)
    return df[df['distance'] <= radius_km].sort_values('distance')

# ==========================
# FORECASTING FUNCTIONS
# ==========================
@st.cache_resource
def load_forecast_model():
    try:
        model = load_model("backend/model/lstm_aqi_model.h5")
        return model
    except Exception as e:
        st.error(f"⚠️ Could not load model: {e}")
        return None

def forecast_next_24_hours(model, recent_aqi_values):
    if model is None:
        return None
    try:
        X_input = np.array(recent_aqi_values).reshape(1, -1, 1)
        preds = model.predict(X_input)
        preds = preds.flatten()[:24]
        future_times = pd.date_range(datetime.now(), periods=24, freq='H')
        forecast_df = pd.DataFrame({"timestamp": future_times, "forecast_aqi": preds})
        return forecast_df
    except Exception as e:
        st.error(f"❌ Forecasting failed: {e}")
        return None

# ==========================
# UI RENDERING
# ==========================
def render_header(df):
    st.markdown('<h1 style="text-align:center; color:#0D47A1;">🌍 Delhi Air Quality Dashboard</h1>', unsafe_allow_html=True)
    last_update_time = df['last_updated'].max() if not df.empty else "N/A"
    st.markdown(f'<p style="text-align:center; color:#1565C0;">Last updated: {last_update_time}</p>', unsafe_allow_html=True)

def render_map_tab(df):
    st.markdown('<h3>📍 Interactive Air Quality Map</h3>', unsafe_allow_html=True)
    st.pydeck_chart(pdk.Deck(
        map_style="light",
        initial_view_state=pdk.ViewState(latitude=DELHI_LAT, longitude=DELHI_LON, zoom=9.5, pitch=50),
        layers=[pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position='[lon, lat]',
            get_fill_color='color',
            get_radius=250,
            pickable=True,
            opacity=0.8
        )],
        tooltip={"html": "<b>{station_name}</b><br/>AQI: {aqi}<br/>Category: {category}", "style": {"color": "white"}}
    ))

def render_alerts_tab(df):
    st.markdown('<h3>🔔 Health Alerts</h3>', unsafe_allow_html=True)
    max_aqi = df['aqi'].max()
    advice = get_aqi_category(max_aqi)[3]
    st.info(f"Highest AQI: {max_aqi:.0f}. Recommendation: {advice}")

def render_analytics_tab(df):
    st.markdown('<h3>📊 Analytics</h3>', unsafe_allow_html=True)
    category_counts = df['category'].value_counts()
    fig = px.pie(values=category_counts.values, names=category_counts.index, hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

def render_forecasting_tab(df):
    """Renders AQI forecasting section with a 24-hour forecast graph."""
    st.markdown('<div class="section-header">📈 24-Hour AQI Forecast</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color: #E3F2FD; padding: 1rem; border-radius: 10px; border-left: 4px solid #2196F3;">
        <p style="color: #0D47A1; margin: 0; font-weight: 500;">
        Using the trained deep learning model to forecast Air Quality Index (AQI) for the next 24 hours in Delhi.
        </p>
    </div>
    """, unsafe_allow_html=True)

    model = load_forecast_model()
    if model is None:
        return

    if df.empty:
        st.warning("No live AQI data available for forecasting.")
        return

    recent_aqi_values = df['aqi'].sort_values(ascending=False).head(24).tolist()
    if len(recent_aqi_values) < 10:
        st.warning("Not enough recent AQI values to make forecast.")
        return

    forecast_df = forecast_next_24_hours(model, recent_aqi_values)
    if forecast_df is None:
        return

    fig = px.line(forecast_df, x="timestamp", y="forecast_aqi", title="Predicted AQI for Next 24 Hours",
                  markers=True, line_shape="spline")
    fig.update_layout(xaxis_title="Time", yaxis_title="Predicted AQI", paper_bgcolor='#F5F5F5')
    st.plotly_chart(fig, use_container_width=True)

    avg_forecast = forecast_df["forecast_aqi"].mean()
    category, _, emoji, advice = get_aqi_category(avg_forecast)
    st.info(f"**Average Forecasted AQI:** {avg_forecast:.1f} ({emoji} {category})\n\n💡 {advice}")

# ==========================
# MAIN APP EXECUTION
# ==========================
aqi_data = fetch_live_data()
render_header(aqi_data)

if aqi_data.empty:
    st.error("⚠️ Could not fetch live AQI data.")
else:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ Live Map", "🔔 Alerts", "📊 Analytics", "📱 SMS Alerts", "📈 Forecast"
    ])
    with tab1:
        render_map_tab(aqi_data)
    with tab2:
        render_alerts_tab(aqi_data)
    with tab3:
        render_analytics_tab(aqi_data)
    with tab5:
        render_forecasting_tab(aqi_data)
