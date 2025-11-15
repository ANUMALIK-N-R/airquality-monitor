import numpy as np
import pandas as pd
from pyproj import Transformer
from pykrige.ok import OrdinaryKriging


# -----------------------------
# 1. UTM Transformer for Delhi
# -----------------------------
# Delhi → UTM Zone 43N (EPSG:32643)
transformer_to_utm = Transformer.from_crs(
    "epsg:4326",  # WGS 84 (lat/lon)
    "epsg:32643",  # UTM Zone 43N (meters)
    always_xy=True
)
transformer_to_latlon = Transformer.from_crs(
    "epsg:32643",  # UTM Zone 43N (meters)
    "epsg:4326",  # WGS 84 (lat/lon)
    always_xy=True
)


# -----------------------------------------------
# 2. Grid generator in UTM meters
# -----------------------------------------------
def generate_utm_grid(lat_min, lat_max, lon_min, lon_max, resolution=200):
    """
    Generate a grid in UTM meters for Kriging.
    """
    # Convert bounding box corners to UTM meters
    x_min, y_min = transformer_to_utm.transform(lon_min, lat_min)
    x_max, y_max = transformer_to_utm.transform(lon_max, lat_max)

    # Create evenly spaced meter grid
    x = np.linspace(x_min, x_max, resolution)
    y = np.linspace(y_min, y_max, resolution)

    x_grid, y_grid = np.meshgrid(x, y)

    return x_grid, y_grid


# ----------------------------------------------------
# 3. Kriging with UTM coordinates (with safety checks)
# ----------------------------------------------------
def perform_kriging_correct(df, bounds, resolution=200):
    """
    Performs Ordinary Kriging on AQI data.

    df: DataFrame from fetch_live_data() containing columns:
        lat, lon, aqi
    bounds: (LAT_MIN, LAT_MAX, LON_MIN, LON_MAX)
    """

    # -----------------------------
    # SAFETY CHEKS BEFORE KRIGING
    # -----------------------------

    # Drop missing values
    df = df.dropna(subset=["lat", "lon", "aqi"]).copy()

    # Remove duplicate coordinates (PyKrige cannot handle them)
    df = df.drop_duplicates(subset=["lat", "lon"]).reset_index(drop=True)

    # Ensure numeric AQI
    df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
    df = df.dropna(subset=["aqi"])

    # Must have at least 4 stations
    if len(df) < 4:
        raise ValueError(
            f"Kriging requires at least 4 unique stations. Found {len(df)}")

    # Must have variance
    if df["aqi"].nunique() < 2:
        raise ValueError("AQI values have zero variance — kriging impossible.")

    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = bounds

    # Convert station coords to UTM
    xs, ys = transformer_to_utm.transform(
        df["lon"].values, df["lat"].values
    )
    values = df["aqi"].values.astype(float)

    # Generate UTM grid
    x_grid, y_grid = generate_utm_grid(
        LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, resolution
    )

    # -----------------------------
    # RUN ORDINARY KRIGING
    # -----------------------------
    
    # --- CORRECTION ---
    # The 'variogram_model' parameter must be a SINGLE STRING.
    # PyKrige will then fit the parameters (sill, range, nugget)
    # for this specific model to the data.
    # 'spherical' is a common, robust model for environmental data.
    # Your original 'exponential' is also a perfectly valid choice.
    
    OK = OrdinaryKriging(
        xs, ys, values,
        variogram_model='spherical',  # <-- This is the fix
        nlags=6,      
        weight=True,  # Use weighted variogram for clustered stations
        enable_plotting=False,
        verbose=False
    )
    # --- End of correction ---

    # Interpolate on the UTM grid
    z, ss = OK.execute("grid", x_grid[0], y_grid[:, 0])

    # Clip values to a realistic AQI range (0 to 500)
    z = np.clip(z, 0, 500)

    # Transform the grid coordinates back into lat/lon for plotting
    lon_grid, lat_grid = transformer_to_latlon.transform(
        x_grid, y_grid
    )

    return lon_grid, lat_grid, z
