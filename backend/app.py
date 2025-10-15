import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import plotly.express as px
from datetime import datetime
import numpy as np
import os
from tensorflow.keras.models import load_model

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

# Twilio Configuration (you need to add your credentials)
TWILIO_ACCOUNT_SID = "AC2cc57109fc63de336609901187eca69d"
TWILIO_AUTH_TOKEN = "62b791789bb490f91879e89fa2ed959d"
TWILIO_PHONE_NUMBER = "+13856005348"

# ==========================
# LOAD PREDICTION MODEL
# ==========================
MODEL_DIR = "models"
model_files = [f for f in os.listdir(MODEL_DIR) if f.endswith(".h5")]

if len(model_files) == 0:
    raise FileNotFoundError("No .h5 model found in 'models/' folder!")
MODEL_PATH = os.path.join(MODEL_DIR, model_files[0])
model = load_model(MODEL_PATH)

# ==========================
# HELPER FUNCTIONS
# ==========================
@st.cache_data(ttl=600, show_spinner="Fetching Air Quality Data...")
def fetch_live_data():
    """Fetches and processes live AQI data from the WAQI API."""
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
                else:
                    return 'N/A'
            def safe_get_time(x):
                if isinstance(x, dict):
                    time_data = x.get('time', {})
                    if isinstance(time_data, dict):
                        return time_data.get('s', 'N/A')
                    elif isinstance(time_data, str):
                        return time_data
                    else:
                        return 'N/A'
                else:
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
        return "Moderate", [255, 214, 0], "🟡", "Unusually sensitive people should consider reducing prolonged or heavy exertion."
    elif aqi <= 150: 
        return "Unhealthy for Sensitive Groups", [249, 115, 22], "🟠", "Sensitive groups should reduce prolonged or heavy exertion."
    elif aqi <= 200: 
        return "Unhealthy", [220, 38, 38], "🔴", "Everyone may begin to experience health effects."
    elif aqi <= 300: 
        return "Very Unhealthy", [147, 51, 234], "🟣", "Health alert: everyone may experience more serious health effects."
    else: 
        return "Hazardous", [126, 34, 206], "☠️", "Health warnings of emergency conditions. The entire population is more likely to be affected."

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
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def get_nearby_stations(df, user_lat, user_lon, radius_km=10):
    df['distance'] = df.apply(lambda row: calculate_distance(user_lat, user_lon, row['lat'], row['lon']), axis=1)
    nearby = df[df['distance'] <= radius_km].sort_values('distance')
    return nearby

# ==========================
# PREDICTION FUNCTIONS
# ==========================
def get_last_24_hours(df):
    df_sorted = df.sort_values('last_updated')
    return df_sorted['aqi'].tail(24).values

def predict_next_24_hours(model, last_24_hours):
    predictions = []
    input_seq = last_24_hours.reshape(1, -1, 1)
    for _ in range(24):
        next_pred = model.predict(input_seq, verbose=0)[0][0]
        predictions.append(next_pred)
        input_seq = np.append(input_seq[:, 1:, :], [[[next_pred]]], axis=1)
    return predictions

# ==========================
# UI RENDERING FUNCTIONS
# ==========================
# (Use your existing render_header, render_map_tab, render_alerts_tab, render_alert_subscription_tab, render_analytics_tab)

# ==========================
# MAIN APP EXECUTION
# ==========================
aqi_data = fetch_live_data()
# render_header(aqi_data)  # Keep your existing header function

if aqi_data.empty:
    st.error("⚠️ **Could not fetch live AQI data.** Please try again later.", icon="🚨")
else:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Live Map", "🔔 Alerts & Health", "📊 Analytics", "📱 SMS Alerts", "📈 24h Prediction"])
    
    with tab1:
        # st.container() + render_map_tab(aqi_data)
        pass
    with tab2:
        # st.container() + render_alerts_tab(aqi_data)
        pass
    with tab3:
        # st.container() + render_analytics_tab(aqi_data)
        pass
    with tab4:
        # st.container() + render_alert_subscription_tab(aqi_data)
        pass
    with tab5:
        st.markdown('<div class="section-header">📈 Next 24-Hour AQI Prediction</div>', unsafe_allow_html=True)
        last_24 = get_last_24_hours(aqi_data)
        next_24_pred = predict_next_24_hours(model, last_24)
        hours = pd.date_range(start=pd.Timestamp.now(), periods=24, freq='H')
        pred_df = pd.DataFrame({"Time": hours, "Predicted AQI": next_24_pred})
        fig = px.line(pred_df, x="Time", y="Predicted AQI", markers=True)
        fig.update_layout(yaxis_title="AQI", xaxis_title="Time", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)
