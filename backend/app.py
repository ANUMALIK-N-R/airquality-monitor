import streamlit as st
import pandas as pd
import numpy as np
import requests
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from krigging import perform_kriging_correct
from krigging import get_aqi_at_location
import geopandas as gpd
from shapely.geometry import Point
import pyproj
from shapely.ops import transform
import smtplib
from email.message import EmailMessage
import json
import os
from pathlib import Path

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

DELHI_GEOJSON_URL = "https://raw.githubusercontent.com/shuklaneerajdev/IndiaStateTopojsonFiles/master/Delhi.geojson"

# Historical data storage path
HISTORICAL_DATA_DIR = Path("aqi_historical_data")
HISTORICAL_DATA_DIR.mkdir(exist_ok=True)
HISTORICAL_DATA_FILE = HISTORICAL_DATA_DIR / "aqi_history.json"

# ==========================
# EMAIL TO SMS CONFIGURATION
# ==========================
SENDER_EMAIL = "anumaliknr@gmail.com"
GMAIL_APP_PASSWORD = "xczo lasg vcek olqp"

SMS_GATEWAYS = {
    "Airtel": "@airtelmail.com",
    "Jio": "@jionet.com", 
    "Vi (Vodafone Idea)": "@myvi.in",
    "BSNL": "@bsnlmail.com",
    "AT&T (USA)": "@txt.att.net",
    "T-Mobile (USA)": "@tmomail.net",
    "Verizon (USA)": "@vtext.com",
    "Sprint (USA)": "@messaging.sprintpcs.com"
}

def send_sms_via_email(phone_number, carrier_gateway, message, subject="AQI Alert"):
    """Send SMS using Email-to-SMS gateway via Gmail SMTP"""
    try:
        phone_clean = ''.join(filter(str.isdigit, phone_number))
        gateway_address = f"{phone_clean}{carrier_gateway}"
        
        msg = EmailMessage()
        msg.set_content(message)
        msg["From"] = SENDER_EMAIL
        msg["To"] = gateway_address
        msg["Subject"] = subject
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        return True, f"SMS sent successfully to {phone_clean} via {carrier_gateway}"
        
    except smtplib.SMTPAuthenticationError:
        return False, "Email authentication failed. Please check your Gmail credentials and ensure 'App Password' is enabled."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"SMS sending failed: {str(e)}"

# ==========================
# HISTORICAL DATA FUNCTIONS
# ==========================

def save_historical_snapshot(df):
    """Save current AQI snapshot to historical database"""
    try:
        # Load existing data
        if HISTORICAL_DATA_FILE.exists():
            with open(HISTORICAL_DATA_FILE, 'r') as f:
                historical_data = json.load(f)
        else:
            historical_data = []
        
        # Create snapshot
        timestamp = datetime.now().isoformat()
        snapshot = {
            "timestamp": timestamp,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "hour": datetime.now().hour,
            "stations": []
        }
        
        # Add station data
        for _, row in df.iterrows():
            snapshot["stations"].append({
                "station_name": row["station_name"],
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "aqi": float(row["aqi"]),
                "category": row["category"]
            })
        
        # Add snapshot if we don't have one for this hour yet
        existing_dates = [s["timestamp"][:13] for s in historical_data]  # Compare by hour
        current_hour_key = timestamp[:13]
        
        if current_hour_key not in existing_dates:
            historical_data.append(snapshot)
            
            # Keep only last 90 days
            cutoff_date = (datetime.now() - timedelta(days=90)).isoformat()
            historical_data = [s for s in historical_data if s["timestamp"] >= cutoff_date]
            
            # Save back
            with open(HISTORICAL_DATA_FILE, 'w') as f:
                json.dump(historical_data, f)
            
            return True, len(historical_data)
        return False, len(historical_data)
        
    except Exception as e:
        st.warning(f"Could not save historical data: {str(e)}")
        return False, 0

def load_historical_data():
    """Load historical AQI data"""
    try:
        if HISTORICAL_DATA_FILE.exists():
            with open(HISTORICAL_DATA_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.warning(f"Could not load historical data: {str(e)}")
        return []

def get_historical_stats():
    """Calculate statistics from historical data"""
    historical_data = load_historical_data()
    
    if not historical_data:
        return None
    
    # Convert to DataFrame for analysis
    records = []
    for snapshot in historical_data:
        for station in snapshot["stations"]:
            records.append({
                "timestamp": snapshot["timestamp"],
                "date": snapshot["date"],
                "hour": snapshot["hour"],
                "station_name": station["station_name"],
                "aqi": station["aqi"],
                "category": station["category"]
            })
    
    if not records:
        return None
        
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    
    return df

# ==========================
# CUSTOM CSS FOR STYLING
# ==========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 50%, #90CAF9 100%);
    }

    header, footer, #MainMenu {
        visibility: hidden;
    }
    
    .main-title {
        font-size: 3.5rem;
        font-weight: 900;
        color: #0D47A1;
        padding: 1.5rem 0 0.5rem 0;
        text-align: center;
        text-shadow: 2px 2px 4px rgba(13, 71, 161, 0.2);
        letter-spacing: -1px;
    }

    .subtitle {
        font-size: 1.2rem;
        color: #1565C0;
        text-align: center;
        padding-bottom: 1.5rem;
        font-weight: 500;
    }

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

    .content-card {
        background-color: #FFFFFF;
        padding: 2rem;
        border-radius: 20px;
        border: 2px solid #BBDEFB;
        box-shadow: 0 10px 40px rgba(33, 150, 243, 0.2);
        margin-top: 1.5rem;
    }

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

    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0D47A1;
        margin-bottom: 1.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #BBDEFB;
    }

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

    div[data-testid="stDataFrame"] {
        border: 2px solid #BBDEFB;
        border-radius: 10px;
        background-color: white;
    }
    
    div[data-testid="stPlotlyChart"] {
        background-color: white;
        border-radius: 10px;
        padding: 0.5rem;
    }
    
    .element-container {
        background-color: transparent;
    }
    
    .block-container {
        background-color: transparent;
        padding-top: 2rem;
    }

</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading Delhi boundary...")
def load_delhi_boundary_from_url():
    try:
        gdf = gpd.read_file(DELHI_GEOJSON_URL)
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        polygon = gdf.unary_union
        return gdf, polygon
    except Exception as e:
        st.error(f"Failed to load Delhi polygon: {e}")
        return None, None

if "delhi_gdf" not in st.session_state or "delhi_polygon" not in st.session_state:
    gdf, polygon = load_delhi_boundary_from_url()
    st.session_state["delhi_gdf"] = gdf
    st.session_state["delhi_polygon"] = polygon


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
            df[['category', 'color', 'emoji', 'advice']] = df['aqi'].apply(
                get_aqi_category).apply(pd.Series)
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

def render_kriging_tab(df):
    st.subheader("Spatial Interpolation (Kriging)")
    delhi_bounds_tuple = (28.40, 28.88, 76.84, 77.35)
    delhi_polygon = st.session_state.get("delhi_polygon", None)

    if delhi_polygon is None:
        st.error("Delhi boundary could not be loaded.")
        return

    if len(df) < 3:
        st.error("Not enough AQI stations within Delhi boundary for kriging interpolation (minimum 3 required).")
        return

    with st.spinner("Performing spatial interpolation..."):
        try:
            lon_grid, lat_grid, z = perform_kriging_correct(
                df,
                delhi_bounds_tuple,
                polygon=delhi_polygon,
                resolution=250
            )

            st.session_state["kriging_output"] = (lon_grid, lat_grid, z)
            st.success("✅ Kriging interpolation completed successfully!")

            heatmap_df = pd.DataFrame({
                "lon": lon_grid.flatten(),
                "lat": lat_grid.flatten(),
                "aqi": z.flatten()
            })
            
            heatmap_df = heatmap_df.dropna(subset=['aqi'])

            fig = px.density_mapbox(
                heatmap_df,
                lat="lat",
                lon="lon",
                z="aqi",
                radius=15,
                center=dict(lat=28.6139, lon=77.2090),
                zoom=9.5,
                mapbox_style="carto-positron",
                color_continuous_scale=[
                    "#009E60", "#FFD600", "#F97316",
                    "#DC2626", "#9333EA", "#7E22CE"
                ],
                range_color=[0, 400],
                title="Interpolated AQI Heatmap across Delhi"
            )
            
            fig.update_layout(
                margin=dict(t=40, b=0, l=0, r=0),
                coloraxis_colorbar=dict(
                    title="AQI",
                    thicknessmode="pixels",
                    thickness=15,
                    lenmode="pixels",
                    len=300
                )
            )

            st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.error(f"Error performing kriging: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


def get_weather_info(code):
    """Converts WMO weather code to a description and icon."""
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


# ==========================
# STATISTICAL VISUALIZATION FUNCTIONS
# ==========================

def render_hourly_boxplot(historical_df):
    """Render hourly box plot showing daily variability patterns"""
    st.markdown("### 📦 Best Time to Go Out: Hourly AQI Patterns")
    
    if historical_df is None or len(historical_df) < 24:
        st.info(f"""
        📊 **Historical Data Collection in Progress**
        
        Currently collecting: **{len(historical_df) if historical_df is not None else 0}** hourly snapshots
        
        **What you'll see here after 7+ days:**
        - Box plots showing AQI patterns for each hour (0-23)
        - Best time windows for outdoor activities (lowest median AQI)
        - Risk assessment for each hour (worst-case scenarios)
        - Variability indicators (how consistent each hour is)
        
        **Interpretation Guide:**
        - **Box center line** = Typical AQI for that hour
        - **Box height** = How much variation to expect
        - **Whiskers** = Range of historical values
        - **Dots** = Unusual outlier days
        
        Keep the dashboard running to collect more data!
        """)
        return
    
    # Group by hour and calculate statistics
    hourly_stats = historical_df.groupby('hour')['aqi'].apply(list).to_dict()
    
    # Create box plot
    fig = go.Figure()
    
    hours = sorted(hourly_stats.keys())
    for hour in hours:
        values = hourly_stats[hour]
        fig.add_trace(go.Box(
            y=values,
            name=f"{hour:02d}:00",
            boxmean='sd',
            marker_color='lightblue',
            line=dict(color='rgb(8,81,156)')
        ))
    
    # Add AQI category background colors
    fig.add_hrect(y0=0, y1=50, fillcolor="green", opacity=0.1, line_width=0)
    fig.add_hrect(y0=50, y1=100, fillcolor="yellow", opacity=0.1, line_width=0)
    fig.add_hrect(y0=100, y1=150, fillcolor="orange", opacity=0.1, line_width=0)
    fig.add_hrect(y0=150, y1=200, fillcolor="red", opacity=0.1, line_width=0)
    fig.add_hrect(y0=200, y1=300, fillcolor="purple", opacity=0.1, line_width=0)
    fig.add_hrect(y0=300, y1=500, fillcolor="maroon", opacity=0.1, line_width=0)
    
    fig.update_layout(
        title="AQI Distribution by Hour of Day",
        xaxis_title="Hour of Day",
        yaxis_title="AQI Value",
        showlegend=False,
        height=500,
        yaxis=dict(range=[0, min(400, historical_df['aqi'].max() * 1.1)])
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Find best and worst hours
    median_by_hour = {h: np.median(vals) for h, vals in hourly_stats.items()}
    best_hour = min(median_by_hour, key=median_by_hour.get)
    worst_hour = max(median_by_hour, key=median_by_hour.get)
    
    col1, col2 = st.columns(2)
    with col1:
        st.success(f"""
        **✅ Best Time for Outdoor Activities**
        
        **{best_hour:02d}:00 - {(best_hour+1)%24:02d}:00**
        
        Median AQI: {median_by_hour[best_hour]:.1f}
        """)
    
    with col2:
        st.error(f"""
        **⚠️ Most Polluted Hour**
        
        **{worst_hour:02d}:00 - {(worst_hour+1)%24:02d}:00**
        
        Median AQI: {median_by_hour[worst_hour]:.1f}
        """)


def render_risk_frequency_histogram(historical_df):
    """Render histogram showing frequency of AQI categories over time"""
    st.markdown("### 📊 Air Quality Risk Distribution (Last 30-90 Days)")
    
    if historical_df is None or len(historical_df) < 7:
        st.info(f"""
        📈 **Long-term Risk Assessment (Building Dataset)**
        
        Currently collected: **{len(historical_df) if historical_df is not None else 0}** data points
        
        **What you'll see here after 30+ days:**
        - Frequency of each AQI category (Good, Moderate, Unhealthy, etc.)
        - Percentage of days meeting health standards
        - Trend analysis showing if air quality is improving or worsening
        - Compliance metrics for environmental goals
        
        **Use Cases:**
        - Assess long-term health risk exposure
        - Identify seasonal patterns
        - Track effectiveness of pollution control measures
        - Set realistic expectations for air quality
        
        Continue collecting data for comprehensive analysis!
        """)
        return
    
    # Calculate daily statistics
    daily_stats = historical_df.groupby('date').agg({
        'aqi': ['mean', 'max']
    }).reset_index()
    daily_stats.columns = ['date', 'avg_aqi', 'max_aqi']
    
    # Categorize each day by its maximum AQI
    daily_stats['category'] = daily_stats['max_aqi'].apply(lambda x: get_aqi_category(x)[0])
    
    # Count categories
    category_counts = daily_stats['category'].value_counts()
    
    # Define category order and colors
    category_order = ["Good", "Moderate", "Unhealthy for Sensitive Groups", 
                     "Unhealthy", "Very Unhealthy", "Hazardous"]
    category_colors = {
        "Good": "#009E60",
        "Moderate": "#FFD600",
        "Unhealthy for Sensitive Groups": "#F97316",
        "Unhealthy": "#DC2626",
        "Very Unhealthy": "#9333EA",
        "Hazardous": "#7E22CE"
    }
    
    # Prepare data for plotting
    plot_data = []
    for cat in category_order:
        count = category_counts.get(cat, 0)
        plot_data.append({
            'Category': cat,
            'Days': count,
            'Percentage': (count / len(daily_stats) * 100) if len(daily_stats) > 0 else 0
        })
    
    plot_df = pd.DataFrame(plot_data)
    
    # Create bar chart
    fig = go.Figure(data=[
        go.Bar(
            x=plot_df['Category'],
            y=plot_df['Days'],
            text=plot_df['Percentage'].apply(lambda x: f'{x:.1f}%'),
            textposition='auto',
            marker_color=[category_colors.get(cat, '#999999') for cat in plot_df['Category']]
        )
    ])
    
    fig.update_layout(
        title=f"Air Quality Distribution Over Last {len(daily_stats)} Days",
        xaxis_title="AQI Category",
        yaxis_title="Number of Days",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Calculate health metrics
    total_days = len(daily_stats)
    good_moderate_days = category_counts.get("Good", 0) + category_counts.get("Moderate", 0)
    unhealthy_days = total_days - good_moderate_days
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Healthy Days",
            f"{good_moderate_days} days",
            f"{good_moderate_days/total_days*100:.1f}%",
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            "Unhealthy Days",
            f"{unhealthy_days} days",
            f"{unhealthy_days/total_days*100:.1f}%",
            delta_color="inverse"
        )
    
    with col3:
        # Goal: 80% healthy days
        goal_pct = 80
        current_pct = good_moderate_days/total_days*100
        delta = current_pct - goal_pct
        st.metric(
            "Health Goal (80%)",
            f"{current_pct:.1f}%",
            f"{delta:+.1f}%",
            delta_color="normal" if delta >= 0 else "inverse"
        )

# ==========================
# UI RENDERING FUNCTIONS
# ==========================

def render_header(df):
    """Renders the main header with summary metrics and weather."""
    st.markdown('<div class="main-title">🌍 Delhi Air Quality Dashboard</div>',
                unsafe_allow_html=True)
    
    # Show data collection status
    historical_data = load_historical_data()
    data_points = len(historical_data)
    
    if data_points > 0:
        first_snapshot = datetime.fromisoformat(historical_data[0]["timestamp"])
        days_collecting = (datetime.now() - first_snapshot).days
        st.markdown(f"""
        <div style="background-color: #E8F5E9; padding: 0.75rem; border-radius: 8px; text-align: center; margin-bottom: 1rem; border: 2px solid #4CAF50;">
            <span style="color: #2E7D32; font-weight: 600;">
                📊 Historical Data: {data_points} snapshots collected over {days_collecting} days
                {' ✅ Ready for statistical analysis!' if data_points >= 168 else ' 🔄 Keep collecting...'}
            </span>
        </div>
        """, unsafe_allow_html=True)
    
    last_update_time = df['last_updated'].max() if not df.empty and 'last_updated' in df.columns else "N/A"
    st.markdown(f'<p class="subtitle">Real-time monitoring • Last updated: {last_update_time}</p>', 
                unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    if not df.empty:
        with c1:
            avg_aqi = df["aqi"].mean()
            avg_cat = get_aqi_category(avg_aqi)[0]
            st.markdown(
                f'<div class="metric-card"><div class="metric-card-label">Average AQI</div><div class="metric-card-value">{avg_aqi:.1f}</div><div class="metric-card-delta">{avg_cat}</div></div>', 
                unsafe_allow_html=True)
        with c2:
            min_station = df.loc[df["aqi"].idxmin()]["station_name"]
            min_aqi = df["aqi"].min()
            st.markdown(
                f'<div class="metric-card"><div class="metric-card-label">Minimum AQI</div><div class="metric-card-value">{min_aqi:.0f}</div><div class="metric-card-delta">{min_station}</div></div>', 
                unsafe_allow_html=True)
        with c3:
            max_station = df.loc[df["aqi"].idxmax()]["station_name"]
            max_aqi = df["aqi"].max()
            st.markdown(
                f'<div class="metric-card"><div class="metric-card-label">Maximum AQI</div><div class="metric-card-value">{max_aqi:.0f}</div><div class="metric-card-delta">{max_station}</div></div>', 
                unsafe_allow_html=True)

    with c4:
        weather_data = fetch_weather_data()
        if weather_data and 'current' in weather_data:
            current = weather_data['current']
            desc, icon = get_weather_info(current.get('weather_code', 0))
            st.markdown(f"""
            <div class="weather-widget">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <div class="metric-card-label">Current Weather</div>
                        <div class="weather-temp">{current['temperature_2m']:.1f}°C</div>
                    </div>
                    <div style="font-size: 3rem;">{icon}</div>
                </div>
                <div style="text-align: left; font-size: 0.9rem; color: #1976D2; margin-top: 1rem; font-weight: 500;">
                    {desc}<br/>Humidity: {current['relative_humidity_2m']}%<br/>Wind: {current['wind_speed_10m']} km/h
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="weather-widget">
                <div class="metric-card-label">Current Weather</div>
                <div style="color: #1976D2; margin-top: 1rem;">Weather data unavailable</div>
            </div>
            """, unsafe_allow_html=True)
