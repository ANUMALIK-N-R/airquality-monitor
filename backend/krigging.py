import numpy as np
import pandas as pd
from shapely.geometry import Point
from pyproj import Transformer
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
from pykrige.ok import OrdinaryKriging


# ---------------------------------------------------
# 1. Coordinate Transformers (Delhi = UTM Zone 43N)
# ---------------------------------------------------
transformer_to_utm = Transformer.from_crs(
    "EPSG:4326", "EPSG:32643", always_xy=True
)
transformer_to_latlon = Transformer.from_crs(
    "EPSG:32643", "EPSG:4326", always_xy=True
)


# ---------------------------------------------------
# 2. Generate UTM Grid (meters)
# ---------------------------------------------------
def generate_utm_grid(lat_min, lat_max, lon_min, lon_max, resolution=200):
    """
    Generates a meter-scaled grid for kriging.
    """

    x_min, y_min = transformer_to_utm.transform(lon_min, lat_min)
    x_max, y_max = transformer_to_utm.transform(lon_max, lat_max)

    x = np.linspace(x_min, x_max, resolution)
    y = np.linspace(y_min, y_max, resolution)

    xx, yy = np.meshgrid(x, y)
    return xx, yy


# ---------------------------------------------------
# 3. Apply Polygon Mask
# ---------------------------------------------------
def mask_grid_with_polygon(lon_grid, lat_grid, polygon):
    """
    polygon must be EPSG:4326.
    Returns True for cells inside polygon.
    """

    flat_lon = lon_grid.flatten()
    flat_lat = lat_grid.flatten()

    pts = [Point(lon, lat) for lon, lat in zip(flat_lon, flat_lat)]
    mask = np.array([polygon.contains(pt) for pt in pts])

    return mask.reshape(lon_grid.shape)


# ---------------------------------------------------
# 4. Get Nearest Kriging Value (KD-Tree)
# ---------------------------------------------------
def get_nearest_kriging_value(user_lat, user_lon, lat_grid, lon_grid, z):
    """Get the nearest non-NaN kriging value for a given location."""
    # Flatten and remove NaN values
    flat_lat = lat_grid.flatten()
    flat_lon = lon_grid.flatten()
    flat_z = z.flatten()
    
    # Filter out NaN values
    valid_mask = ~np.isnan(flat_z)
    valid_lats = flat_lat[valid_mask]
    valid_lons = flat_lon[valid_mask]
    valid_z = flat_z[valid_mask]
    
    if len(valid_z) == 0:
        return np.nan
    
    # Build KD-tree with valid points
    pts = np.column_stack((valid_lats, valid_lons))
    tree = cKDTree(pts)

    _, idx = tree.query([user_lat, user_lon], k=1)
    return valid_z[idx]


# ---------------------------------------------------
# 5. Get AQI for Alerts / Geolocation (Main Hook)
# ---------------------------------------------------
def get_aqi_at_location(user_lat, user_lon, lat_grid, lon_grid, z_masked, polygon):
    """
    Returns:
        aqi_value,
        bool -> True if point was outside polygon but nearest value used.
    """

    pt = Point(user_lon, user_lat)

    # Inside polygon → accurate
    if polygon.contains(pt):
        aqi_val = get_nearest_kriging_value(
            user_lat, user_lon, lat_grid, lon_grid, z_masked
        )
        return aqi_val, False

    # Outside polygon → fallback
    aqi_val = get_nearest_kriging_value(
        user_lat, user_lon, lat_grid, lon_grid, z_masked
    )
    return aqi_val, True


# ---------------------------------------------------
# 6. Perform Kriging (Correct + Stable)
# ---------------------------------------------------
def perform_kriging_correct(df, bounds, polygon, resolution=220):
    """
    df: must contain lat, lon, aqi  
    bounds: (LAT_MIN, LAT_MAX, LON_MIN, LON_MAX)
    polygon: shapely polygon in EPSG:4326
    """

    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = bounds

    # Guard against insufficient station count
    if len(df) < 3:
        raise ValueError("Not enough AQI stations for kriging interpolation.")

    # Extract and clean values - DON'T clip too aggressively
    values = df["aqi"].values.copy()
    
    # Only remove extreme outliers (not normal low/high values)
    values = np.clip(values, 0, 999)
    
    print(f"Station AQI range: {values.min():.1f} to {values.max():.1f}")

    # Convert station coordinates to UTM meters
    xs, ys = transformer_to_utm.transform(df["lon"].values, df["lat"].values)

    # Generate interpolation grid (meters)
    x_grid, y_grid = generate_utm_grid(
        LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, resolution
    )

    # Run Ordinary Kriging with better parameters
    OK = OrdinaryKriging(
        xs, ys, values,
        variogram_model="spherical",
        verbose=False,
        enable_plotting=False,
        nlags=6  # Fewer lags for better local variation
    )

    z, ss = OK.execute("grid", x_grid[0], y_grid[:, 0])

    # Don't clip the interpolated values too aggressively
    # Kriging should respect the input range
    z = np.clip(z, max(0, values.min() - 50), values.max() + 50)
    
    print(f"Kriged AQI range (before smoothing): {np.nanmin(z):.1f} to {np.nanmax(z):.1f}")

    # Light smoothing only (sigma=0.5 instead of 1)
    z = gaussian_filter(z, sigma=0.5)
    
    print(f"Kriged AQI range (after smoothing): {np.nanmin(z):.1f} to {np.nanmax(z):.1f}")

    # Convert grid back to lat/lon
    lon_grid, lat_grid = transformer_to_latlon.transform(x_grid, y_grid)

    # Mask using boundary polygon
    mask = mask_grid_with_polygon(lon_grid, lat_grid, polygon)

    z_masked = np.where(mask, z, np.nan)

    return lon_grid, lat_grid, z_masked
