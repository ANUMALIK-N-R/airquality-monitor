import streamlit as st
import pandas as pd
import numpy as np
import requests
import pydeck as pdk
import plotly.express as px
from datetime import datetime, timedelta

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
# CUSTOM CSS FOR STYLING
# ==========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main background */
    .stApp {
        background-color: #F0F4F8;
    }

    /* Hide Streamlit's default header and footer */
    header, footer {
        visibility: hidden;
    }
    
    /* Main title styling */
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        color: #1E293B;
        padding: 1rem 0 0 0;
    }

    /* Subtitle styling */
    .subtitle {
        font-size: 1.1rem;
        color: #475569;
        padding-bottom: 2rem;
    }

    /* Metric cards styling */
    .metric-card {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        text-align: center;
    }
    .metric-card-label {
        font-size: 1rem;
        font-weight: 500;
        color: #64748B;
    }
    .metric-card-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-card-delta {
        font-size: 0.9rem;
        color: #64748B;
    }

    /* Weather widget styling */
    .weather-widget {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }
    .weather-temp {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
    }

    /* Styling for Streamlit tabs */
    button[data-baseweb="tab"] {
        font-size: 1rem;
        font-weight: 600;
        background-color: transparent;
        border-radius: 8px;
        margin: 0 5px;
        transition: background-color 0.3s ease;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #FFFFFF;
        color: #2563EB;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* General card for content */
    .content-card {
        background-color: #FFFFFF;
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-top: 1.5rem;
    }

    /* Alert cards for different severity levels */
    .alert-card {
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .alert-hazardous { background-color: #FEE2E2; border-left: 5px solid #DC2626; }
    .alert-very-unhealthy { background-color: #FEF3C7; border-left: 5px solid #F59E0B; }
    .alert-unhealthy { background-color: #FFEDD5; border-left: 5px solid #F97316; }

</style>
""", unsafe_allow_html=True)

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
            df['aqi'] = pd.to_numeric(df['aqi'])
            df['station_name'] = df['station'].apply(lambda x: x.get('name', 'N/A') if isinstance(x, dict) else 'N/A')
            df['last_updated'] = df['station'].apply(lambda x: x.get('time', {}).get('s', 'N/A') if isinstance(x, dict) else 'N/A')
            df[['category', 'color', 'emoji', 'advice']] = df['aqi'].apply(get_aqi_category).apply(pd.Series)
            df['lat'] = pd.to_numeric(df['lat'])
            df['lon'] = pd.to_numeric(df['lon'])
            return df
        return pd.DataFrame()
    except requests.RequestException:
        return pd.DataFrame()

@st.cache_data(ttl=1800, show_spinner="Fetching Weather Data...")
def fetch_weather_data():
    """Fetches current weather data from Open-Meteo API."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=Asia/Kolkata"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None

def get_aqi_category(aqi):
    """Categorizes AQI value and provides color, emoji, and health advice."""
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
    """Converts WMO weather code to a description and icon."""
    codes = {0: ("Clear sky", "☀️"), 1: ("Mainly clear", "🌤️"), 2: ("Partly cloudy", "⛅"), 3: ("Overcast", "☁️"), 45: ("Fog", "🌫️"), 48: ("Depositing rime fog", "🌫️"), 51: ("Light drizzle", "💧"), 53: ("Moderate drizzle", "💧"), 55: ("Dense drizzle", "💧"), 61: ("Slight rain", "🌧️"), 63: ("Moderate rain", "🌧️"), 65: ("Heavy rain", "🌧️"), 80: ("Slight rain showers", "🌦️"), 81: ("Moderate rain showers", "🌦️"), 82: ("Violent rain showers", "⛈️"), 95: ("Thunderstorm", "⚡"), 96: ("Thunderstorm, slight hail", "⛈️"), 99: ("Thunderstorm, heavy hail", "⛈️")}
    return codes.get(code, ("Unknown", "❓"))

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the distance between two points on Earth."""
    R = 6371  # Earth radius in kilometers
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = sin(dLat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance


def get_nearby_stations(df, user_lat, user_lon, radius_km=10):

def send_sms(to_number, body):
    """Sends an SMS using Twilio."""
    try:
        # Check if placeholder credentials are still being used
        if "ACxxxxxxxx" in TWILIO_ACCOUNT_SID or "your_auth_token" in TWILIO_AUTH_TOKEN:
            st.error("Twilio credentials are not configured. Please update them in the script.")
            return False
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=body,
            messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
            to=to_number
        )
        return True
    except Exception as e:
        st.error(f"Failed to send SMS: {e}")
        return False

# ==========================
# UI RENDERING FUNCTIONS
# ==========================
def render_header(df):
    """Renders the main header with summary metrics and weather."""
    st.markdown('<div class="main-title">Delhi Air Quality Dashboard</div>', unsafe_allow_html=True)
    last_update_time = df['last_updated'].max() if not df.empty and 'last_updated' in df.columns else "N/A"
    st.markdown(f'<p class="subtitle">Last updated: {last_update_time}</p>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    if not df.empty:
        with c1:
            st.markdown(f'<div class="metric-card"><div class="metric-card-label">Avg. AQI</div><div class="metric-card-value">{df["aqi"].mean():.1f}</div><div class="metric-card-delta">{get_aqi_category(df["aqi"].mean())[0]}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card"><div class="metric-card-label">Min AQI</div><div class="metric-card-value">{df["aqi"].min():.0f}</div><div class="metric-card-delta">{df.loc[df["aqi"].idxmin()]["station_name"]}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card"><div class="metric-card-label">Max AQI</div><div class="metric-card-value">{df["aqi"].max():.0f}</div><div class="metric-card-delta">{df.loc[df["aqi"].idxmax()]["station_name"]}</div></div>', unsafe_allow_html=True)

    with c4:
        weather_data = fetch_weather_data()
        if weather_data and 'current' in weather_data:
def render_dummy_forecast_tab():
    """Render a dummy 24-hour AQI forecast using simulated data."""
    st.markdown('<div class="section-header">📈 24-Hour AQI Forecast (Sample)</div>',
                unsafe_allow_html=True)

    st.markdown("""
    <div style="background-color: #E3F2FD; padding: 1rem; border-radius: 10px; border-left: 4px solid #2196F3; margin-bottom: 1rem;">
        <p style="color: #0D47A1; margin: 0; font-weight: 500;">
        This sample forecast simulates how the Air Quality Index (AQI) may change over the next 24 hours.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Simulate a smooth AQI forecast for 24 hours
    hours = np.arange(0, 24)
    base_aqi = 120 + 40 * np.sin(hours / 3) + np.random.normal(0, 5, size=24)
    timestamps = [datetime.now() + timedelta(hours=i) for i in range(24)]
    forecast_df = pd.DataFrame({
        "timestamp": timestamps,
        "forecast_aqi": np.clip(base_aqi, 40, 300)
    })

    # Plot forecast trend
    fig = px.line(
        forecast_df,
        x="timestamp",
        y="forecast_aqi",
        title="Predicted AQI Trend for Next 24 Hours (Simulated)",
        markers=True,
        line_shape="spline"
    )
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Predicted AQI",
        showlegend=False,
        margin=dict(t=40, b=20, l=0, r=20),
        paper_bgcolor='white',
        plot_bgcolor='white',
        title_font_color="#0D47A1",
        font_color="#0D47A1",
        xaxis=dict(gridcolor='#E3F2FD'),
        yaxis=dict(gridcolor='#E3F2FD')
    )

    st.plotly_chart(fig, use_container_width=True)

    # Display summary
    avg_aqi = forecast_df["forecast_aqi"].mean()
    max_aqi = forecast_df["forecast_aqi"].max()
    min_aqi = forecast_df["forecast_aqi"].min()

    st.markdown(f"""
    <div style="background-color: white; padding: 1rem; border-radius: 10px; border-left: 5px solid #1976D2; margin-top: 1rem; color: #1E293B;">
        <b>Average Forecasted AQI:</b> {avg_aqi:.1f}  
        <br><b>Expected Range:</b> {min_aqi:.1f} – {max_aqi:.1f}
        <br><b>Air Quality Outlook:</b> Moderate to Unhealthy range over the next day.
    </div>
    """, unsafe_allow_html=True)


def render_analytics_tab(df):
    """Renders charts and data analytics."""
    st.markdown("##### 📊 Data Analytics")
    c1, c2 = st.columns([1, 1])

    with c1:
        st.markdown("**AQI Category Distribution**")
        category_counts = df['category'].value_counts()
        fig = px.pie(
            values=category_counts.values, names=category_counts.index, hole=0.4,
            color=category_counts.index,
            color_discrete_map={
                "Good": "#009E60", "Moderate": "#FFD600", "Unhealthy for Sensitive Groups": "#F97316",
                "Unhealthy": "#DC2626", "Very Unhealthy": "#9333EA", "Hazardous": "#7E22CE"
            }
        )
        fig.update_traces(textinfo='percent+label', pull=[0.05]*len(category_counts.index))
        fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("**Top 10 Most Polluted Stations**")
        top_10 = df.nlargest(10, 'aqi').sort_values('aqi', ascending=True)
        fig = px.bar(
            top_10, x='aqi', y='station_name', orientation='h',
            color='aqi', color_continuous_scale=px.colors.sequential.Reds
        )
        fig.update_layout(xaxis_title="AQI", yaxis_title="", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Full Station Data**")
    st.dataframe(df[['station_name', 'aqi', 'category', 'last_updated']].set_index('station_name'))

def render_subscription_tab(df):
    """Renders the SMS alert subscription form."""
    st.markdown("##### 📞 Subscribe to SMS Alerts")
    st.markdown("Get real-time air quality and weather alerts for your location sent directly to your phone.")

    with st.form("sms_form"):
        col1, col2, col3 = st.columns([2, 2, 3])
        with col1:
            lat = st.number_input("Your Latitude", value=DELHI_LAT, format="%.4f")
        with col2:
            lon = st.number_input("Your Longitude", value=DELHI_LON, format="%.4f")
        with col3:
            phone_number = st.text_input("Phone Number (with country code)", placeholder="+919876543210")
        
        submitted = st.form_submit_button("Get Instant Alert")

        if submitted:
            if not phone_number:
                st.warning("Please enter a valid phone number.")
            else:
                with st.spinner("Finding nearest station and sending alert..."):
                    # Find nearest station
                    nearest_station = find_nearest_station(lat, lon, df)
                    station_name = nearest_station['station_name']
                    aqi = nearest_station['aqi']
                    category = nearest_station['category']
                    advice = nearest_station['advice']

                    # Get weather for user's location
                    weather_data = fetch_weather_data(lat, lon)
                    if weather_data and 'current' in weather_data:
                        current = weather_data['current']
                        temp = current['temperature_2m']
                        desc, icon = get_weather_info(current.get('weather_code', 0))
                        weather_summary = f"{icon} {temp}°C, {desc}"
                    else:
                        weather_summary = "Weather data unavailable."
                    
                    # Compose and send SMS
                    sms_body = (
                        f"AQI Alert for your location ({lat:.2f}, {lon:.2f}):\n"
                        f"Nearest Station: {station_name}\n"
                        f"AQI: {aqi:.0f} ({category})\n"
                        f"Advice: {advice}\n"
                        f"Weather: {weather_summary}"
                    )
                    
                    if send_sms(phone_number, sms_body):
                        st.success(f"✅ Alert successfully sent to {phone_number}!")
                        st.text_area("Message Sent:", sms_body, height=150)

# ==========================
# MAIN APP EXECUTION
# ==========================
aqi_data = fetch_live_data()
render_header(aqi_data)

if aqi_data.empty:
    st.error("⚠️ **Could not fetch live AQI data.** The API may be down or there's a network issue. Please try again later.", icon="🚨")
else:
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Live Map", "🔔 Alerts & Health", "📊 Analytics", "📞 Subscribe to Alerts"])
    with tab1:
        with st.container():
             st.markdown('<div class="content-card">', unsafe_allow_html=True)
             render_map_tab(aqi_data)
             st.markdown('</div>', unsafe_allow_html=True)
    with tab2:
        with st.container():
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            render_alerts_tab(aqi_data)
            st.markdown('</div>', unsafe_allow_html=True)
    with tab3:
        with st.container():
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            render_analytics_tab(aqi_data)
            st.markdown('</div>', unsafe_allow_html=True)
    with tab4:
        with st.container():
            st.markdown('<div class="content-card">', unsafe_allow_html=True)
            render_subscription_tab(aqi_data)
            st.markdown('</div>', unsafe_allow_html=True)

