import numpy as np
import pandas as pd
from shapely.geometry import Point
from pyproj import Transformer
from pykrige.ok import OrdinaryKriging
from scipy.spatial import cKDTree

# Delhi UTM Zone 43N
transformer_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
transformer_to_latlon = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)


def generate_utm_grid(lat_min, lat_max, lon_min, lon_max, resolution=200):
    x_min, y_min = transformer_to_utm.transform(lon_min, lat_min)
    x_max, y_max = transformer_to_utm.transform(lon_max, lat_max)

    x = np.linspace(x_min, x_max, resolution)
    y = np.linspace(y_min, y_max, resolution)
    xx, yy = np.meshgrid(x, y)

    return xx, yy


def mask_grid_with_polygon(lon_grid, lat_grid, polygon):
    """
    polygon must be EPSG:4326 lat/lon
    """
    flat_lon = lon_grid.flatten()
    flat_lat = lat_grid.flatten()

    pts = [Point(lon, lat) for lon, lat in zip(flat_lon, flat_lat)]
    mask = np.array([polygon.contains(pt) for pt in pts])

    return mask.reshape(lon_grid.shape)


def get_nearest_kriging_value(user_lat, user_lon, lat_grid, lon_grid, z):
    pts = np.column_stack((lat_grid.flatten(), lon_grid.flatten()))
    tree = cKDTree(pts)

    _, idx = tree.query([user_lat, user_lon], k=1)
    return z.flatten()[idx]

def perform_kriging_correct(df, bounds, polygon, resolution=220):

    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = bounds

    # Convert station coords to UTM
    xs, ys = transformer_to_utm.transform(df["lon"].values, df["lat"].values)
    values = df["aqi"].values

    # Generate UTM grid
    x_grid, y_grid = generate_utm_grid(
        LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, resolution
    )

    # Ordinary Kriging (working variogram)
    OK = OrdinaryKriging(
        xs, ys, values,
        variogram_model="spherical",
        verbose=False,
        enable_plotting=False
    )

    z, _ = OK.execute("grid", x_grid[0], y_grid[:, 0])
    z = np.clip(z, 0, 500)

    # Convert Kriging output back to lat/lon grid
    lon_grid, lat_grid = transformer_to_latlon.transform(x_grid, y_grid)

    # Apply polygon mask
    mask = mask_grid_with_polygon(lon_grid, lat_grid, polygon)
    z_masked = np.where(mask, z, np.nan)

    return lon_grid, lat_grid, z_masked

