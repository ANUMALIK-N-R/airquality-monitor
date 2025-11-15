import numpy as np
import pandas as pd
from pyproj import Transformer
from pykrige.ok import OrdinaryKriging


# -----------------------------
# 1. UTM Transformer for Delhi
# -----------------------------
# Delhi → UTM Zone 43N (EPSG:32643)
# This is CRITICAL for correct distance-based analysis (kriging).
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
    # We use complex numbers (e.g., 200j) to define the *number* of points
    # which matches the 'resolution' parameter's intent.
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
    # SAFETY CHECKS BEFORE KRIGING
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

    # Must have variance (if all stations report 150, interpolation is impossible)
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
    
    # --- GEOSPATIAL BEST PRACTICE ---
    # Instead of hard-coding a model (e.g., 'exponential'), we provide
    # a list of common models. PyKrige will automatically fit each one
    # to the data's experimental variogram and select the model
    # with the lowest sum-of-squared-errors (SSE).
    # This is the correct approach, as the model should be
    # data-driven.
    
    # We also set weight=True, which is recommended for clustered
    # data (which monitoring stations often are).
    
    common_models = ['spherical', 'exponential', 'gaussian', 'power']

    OK = OrdinaryKriging(
        xs, ys, values,
        variogram_model=common_models,
        nlags=6,      # Use 6 lags for the experimental variogram
        weight=True,  # Use weighted variogram for clustered stations
        enable_plotting=False,
        verbose=False
    )
    # --- End of improvement ---

    # Interpolate on the UTM grid.
    # OK.execute expects the 1D vectors for the x and y axes.
    # x_grid[0] is the 1D vector of x-coordinates
    # y_grid[:, 0] is the 1D vector of y-coordinates
    z, ss = OK.execute("grid", x_grid[0], y_grid[:, 0])

    # Clip values to a realistic AQI range (0 to 500)
    z = np.clip(z, 0, 500)

    # Transform the grid coordinates back into lat/lon for plotting
    lon_grid, lat_grid = transformer_to_latlon.transform(
        x_grid, y_grid
    )

    return lon_grid, lat_grid, z
