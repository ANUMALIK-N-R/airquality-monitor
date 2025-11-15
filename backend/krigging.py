import numpy as np
import pandas as pd
from pyproj import Transformer
from pykrige.ok import OrdinaryKriging

# -----------------------------
# 1. UTM Transformer for Delhi
# -----------------------------

# Delhi is in UTM Zone 43N  (for Shanghai we’d use 51N — I can adjust)
transformer_to_utm = Transformer.from_crs("epsg:4326", "epsg:32643", always_xy=True)
transformer_to_latlon = Transformer.from_crs("epsg:32643", "epsg:4326", always_xy=True)

# -----------------------------------------------
# 2. Grid generator in UTM meters (NOT lat/lon!)
# -----------------------------------------------

def generate_utm_grid(lat_min, lat_max, lon_min, lon_max, resolution=200):
    """
    Generate a grid in UTM coordinates for Kriging.
    """
    # Convert bounding box corners to UTM meters
    x_min, y_min = transformer_to_utm.transform(lon_min, lat_min)
    x_max, y_max = transformer_to_utm.transform(lon_max, lat_max)

    # Create evenly spaced meter grid
    x = np.linspace(x_min, x_max, resolution)
    y = np.linspace(y_min, y_max, resolution)
    x_grid, y_grid = np.meshgrid(x, y)

    return x_grid, y_grid


# -----------------------------------------------
# 3. Kriging with UTM coordinates (CORRECT WAY)
# -----------------------------------------------

def perform_kriging_correct(df, bounds, resolution=200):
    """
    df: DataFrame from your fetch_live_data()
        must contain: lat, lon, aqi
    bounds: (LAT_MIN, LAT_MAX, LON_MIN, LON_MAX)
    """

    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = bounds

    # Convert station coords to UTM
    xs, ys = transformer_to_utm.transform(df["lon"].values, df["lat"].values)
    values = df["aqi"].values

    # Generate UTM grid
    x_grid, y_grid = generate_utm_grid(
        LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, resolution=resolution
    )

    # Kriging (auto-select best variogram)
    OK = OrdinaryKriging(
        xs, ys, values,
        variogram_model="best",
        enable_plotting=False,
        verbose=False
    )

    # Interpolate
    z, ss = OK.execute("grid", x_grid[0], y_grid[:, 0])

    # Clip output (AQI must be 0–500)
    z = np.clip(z, 0, 500)

    # Convert grid back to lat/lon for plotting
    lon_grid, lat_grid = transformer_to_latlon.transform(x_grid, y_grid)

    return lon_grid, lat_grid, z
