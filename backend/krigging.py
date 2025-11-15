def perform_kriging_correct(df, bounds, resolution=200):
    """
    Performs UTM-corrected kriging with full safety checks.
    df must contain: lat, lon, aqi
    bounds: (LAT_MIN, LAT_MAX, LON_MIN, LON_MAX)
    """

    # -----------------------------
    # SAFETY CHECKS BEFORE KRIGING
    # -----------------------------

    # Remove NaN values
    df = df.dropna(subset=["lat", "lon", "aqi"]).copy()

    # Remove duplicates (PyKrige will crash on duplicate coords)
    df = df.drop_duplicates(subset=["lat", "lon"]).reset_index(drop=True)

    # Ensure AQI is numeric
    df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
    df = df.dropna(subset=["aqi"])

    # Must have AT LEAST 4 stations for kriging
    if len(df) < 4:
        raise ValueError(f"Kriging requires at least 4 AQI stations. Found: {len(df)}")

    # Must have variance > 0 (PyKrige crashes if all AQIs are identical)
    if df["aqi"].nunique() < 2:
        raise ValueError("AQI values have zero variance — cannot perform kriging.")

    # Now extract values
    LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = bounds

    # Convert station coords to UTM
    xs, ys = transformer_to_utm.transform(df["lon"].values, df["lat"].values)
    values = df["aqi"].values.astype(float)

    # -----------------------------
    # GENERATE UTM GRID
    # -----------------------------
    x_grid, y_grid = generate_utm_grid(
        LAT_MIN, LAT_MAX, LON_MIN, LON_MAX, resolution=resolution
    )

    # -----------------------------
    # PERFORM SAFE KRIGING
    # -----------------------------
    OK = OrdinaryKriging(
        xs, ys, values,
        variogram_model="best",    # auto-fit the correct model
        enable_plotting=False,
        verbose=False
    )

    # Perform interpolation
    z, ss = OK.execute("grid", x_grid[0], y_grid[:, 0])

    # Clip AQI values to realistic range
    z = np.clip(z, 0, 500)

    # Convert grid back to lat/lon for plotting
    lon_grid, lat_grid = transformer_to_latlon.transform(x_grid, y_grid)

    return lon_grid, lat_grid, z
