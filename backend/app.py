import streamlit as st
import pandas as pd
import requests
import pydeck as pdk
import plotly.express as px
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# Email configuration (use your SMTP details)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "anumaliknr@gmail.com"  # Replace with sender email
EMAIL_PASSWORD = "yivi yzzo cqtk slep"     # Use app password if using Gmail

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
    """Fetches current weather data from Open-Meteo API."""
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

def create_alert_message(nearby_stations, weather_data, location_name):
    if nearby_stations.empty:
        return "No nearby air quality monitoring stations found."
    avg_aqi = nearby_stations['aqi'].mean()
    worst_station = nearby_stations.iloc[0]
    weather_desc = "N/A"
    temp = "N/A"
    if weather_data and 'current' in weather_data:
        current = weather_data['current']
        weather_desc, _ = get_weather_info(current.get('weather_code', 0))
        temp = f"{current['temperature_2m']:.1f}°C"
    category, _, emoji, advice = get_aqi_category(avg_aqi)
    message = f"""🌍 Air Quality Alert - {location_name}

{emoji} AQI Status: {category}
📊 Average AQI: {avg_aqi:.0f}

🔴 Worst Station: {worst_station['station_name']}
AQI: {worst_station['aqi']:.0f} ({worst_station['distance']:.1f} km away)

🌤️ Weather: {weather_desc}
🌡️ Temperature: {temp}

💡 Advice: {advice}

Stay safe!"""
    return message

def get_coordinates_from_place(place_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_name, "format": "json", "limit": 1}
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        return None, None
    except:
        return None, None

def send_email_alert(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True, f"Email sent successfully to {to_email}!"
    except Exception as e:
        return False, f"Error sending email: {str(e)}"

# ==========================
# UI RENDERING FUNCTIONS
# ==========================
# (render_header, render_map_tab, render_alerts_tab, render_analytics_tab remain the same as your previous code)
# Only the alert subscription tab changes:

def render_alert_subscription_tab(df):
    st.markdown('<div class="section-header">📧 Email Alert Subscription</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        location_name = st.text_input("📍 Enter Your Location", placeholder="e.g., Connaught Place, New Delhi")
    with col2:
        email_address = st.text_input("📧 Email Address", placeholder="example@gmail.com")
        radius = st.slider("Search Radius (km)", min_value=1, max_value=20, value=10)
        st.markdown("<br>", unsafe_allow_html=True)
        send_alert_btn = st.button("📤 Send Email Alert", type="primary", use_container_width=True)

    if send_alert_btn:
        if not location_name or not email_address:
            st.error("Please fill in both Location and Email Address", icon="⚠️")
        elif "@" not in email_address:
            st.error("Please enter a valid email address", icon="⚠️")
        else:
            with st.spinner("Fetching location coordinates..."):
                user_lat, user_lon = get_coordinates_from_place(location_name)
                if user_lat is None or user_lon is None:
                    st.error("Could not find the location. Please enter a valid place name.", icon="⚠️")
                else:
                    nearby_stations = get_nearby_stations(df, user_lat, user_lon, radius)
                    if nearby_stations.empty:
                        st.warning(f"No monitoring stations found within {radius} km.", icon="⚠️")
                    else:
                        weather_data = fetch_weather_data()
                        alert_message = create_alert_message(nearby_stations, weather_data, location_name)
                        st.markdown("### 📄 Alert Preview")
                        st.info(alert_message)
                        subject = f"Air Quality Alert - {location_name}"
                        success, message = se
