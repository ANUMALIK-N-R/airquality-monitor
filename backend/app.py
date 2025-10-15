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
st.set_page_config(layout="wide", page_title="Delhi NCR Air Quality")
st.title("📍 Delhi NCR Air Quality Monitoring")

tab = st.radio("View:", ["Map", "Alerts", "Analytics"])

df = fetch_live_data()

if df.empty:
    st.warning("⚠️ Could not fetch live AQI data.")
else:
    if tab == "Map":
        st.subheader("Live AQI Map")

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
            map_style="light",  # No Mapbox token needed
            initial_view_state=pdk.ViewState(
                latitude=28.6139,
                longitude=77.2090,
                zoom=10,
                pitch=0,
            ),
            layers=[layer],
            tooltip=tooltip
        ))

    elif tab == "Alerts":
        st.subheader("🔔 Alerts")
        hazardous = df[df['aqi'] > 300]
        very_unhealthy = df[(df['aqi'] > 200) & (df['aqi'] <= 300)]
        unhealthy = df[(df['aqi'] > 150) & (df['aqi'] <= 200)]

        def show_alerts(category_name, subset):
            if not subset.empty:
                st.markdown(f"### {category_name}")
                for _, row in subset.iterrows():
                    st.write(f"{row['station_name']}: {row['aqi']}")

        show_alerts("🚨 Hazardous (AQI > 300)", hazardous)
        show_alerts("⚠️ Very Unhealthy (AQI 201-300)", very_unhealthy)
        show_alerts("⚡ Unhealthy (AQI 151-200)", unhealthy)

        if hazardous.empty and very_unhealthy.empty and unhealthy.empty:
            st.success("✅ No active alerts")

    elif tab == "Analytics":
        st.subheader("📈 Analytics")
        avg_aqi = df['aqi'].mean()
        st.metric("Average AQI", f"{avg_aqi:.1f}")
        st.bar_chart(df.set_index('station_name')['aqi'])
