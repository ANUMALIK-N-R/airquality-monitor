import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.ops import transform
from shapely.geometry import Point, Polygon
from pykrige.ok import OrdinaryKriging


# ----------------------------
# UTM Transform (Delhi = 32643)
# ----------------------------
to_utm = Transformer.from_crs("epsg:4326", "epsg:32643", always_xy=True).transform
to_latlon = Transformer.from_crs("epsg:32643", "epsg:4326", always_xy=True).transform


# ----------------------------
# Generate UTM Grid
# ----------------------------
def generate_utm_grid(lat_min, lat_max, lon_min, lon_max, resolution=200):
    x_min, y_min = to_utm(lon_min, lat_min)
    x_max, y_max = to_utm(lon_max, lat_max)

    x = np.linspace(x_min, x_max, resolution)
    y = np.linspace(y_min, y_max, resolution)

    x_grid, y_grid = np.meshgrid(x, y)
    return x_grid, y_grid


# ----------------------------
# Main Kriging Function
# ----------------------------
def perform_kriging_correct(df, bbox, polygon=None, resolution=200):
    """
    df → AQI station dataframe
    bbox → (lat_min, lat_max, lon_min, lon_max)
    polygon → Delhi boundary (UTM transformed)
    """

    lat_min, lat_max, lon_min, lon_max = bbox

    # ------------------------------------------------------
    # 1. Convert station coordinates to UTM (meters)
    # ------------------------------------------------------
    xs, ys = to_utm(df["lon"].values, df["lat"].values)
    values = df["aqi"].values

    # ------------------------------------------------------
    # 2. Build UTM grid for interpolation
    # ------------------------------------------------------
    x_grid, y_grid = generate_utm_grid(lat_min, lat_max, lon_min, lon_max, resolution)

    # ------------------------------------------------------
    # 3. Perform Ordinary Kriging in meters
    # ------------------------------------------------------
    OK = OrdinaryKriging(
        xs, ys, values,
        variogram_model="spherical",
        verbose=False,
        enable_plotting=False,
    )

    z, ss = OK.execute("grid", x_grid[0], y_grid[:, 0])

    # ------------------------------------------------------
    # 4. Mask grid using Delhi polygon in UTM
    # ------------------------------------------------------
    if polygon is not None:
        mask = np.zeros_like(z, dtype=bool)

        for i in range(z.shape[0]):
            for j in range(z.shape[1]):
                px = x_grid[i, j]
                py = y_grid[i, j]

                if polygon.contains(Point(px, py)):
                    mask[i, j] = True

        z = np.where(mask, z, np.nan)

    # ------------------------------------------------------
    # 5. Convert grid from UTM → Lat/Lon
    # ------------------------------------------------------
    lon_grid, lat_grid = to_latlon(x_grid, y_grid)

    return lon_grid, lat_grid, z
