"""Paramètres de la collecte : villes, variables météo et colonnes du CSV produit."""

# 20 principales villes françaises (coordonnées du centre-ville)
CITIES: dict[str, tuple[float, float]] = {
    "Paris": (48.8566, 2.3522),
    "Marseille": (43.2965, 5.3698),
    "Lyon": (45.7640, 4.8357),
    "Toulouse": (43.6047, 1.4442),
    "Nice": (43.7102, 7.2620),
    "Nantes": (47.2184, -1.5536),
    "Strasbourg": (48.5734, 7.7521),
    "Montpellier": (43.6108, 3.8767),
    "Bordeaux": (44.8378, -0.5792),
    "Lille": (50.6292, 3.0573),
    "Rennes": (48.1173, -1.6778),
    "Reims": (49.2583, 4.0317),
    "Le Havre": (49.4944, 0.1079),
    "Saint-Étienne": (45.4397, 4.3872),
    "Toulon": (43.1242, 5.9280),
    "Grenoble": (45.1885, 5.7245),
    "Dijon": (47.3220, 5.0415),
    "Angers": (47.4784, -0.5632),
    "Nîmes": (43.8367, 4.3601),
    "Villeurbanne": (45.7667, 4.8800),
}

# Variable Open-Meteo -> nom de colonne dans le CSV et dans Hive (unité dans le nom)
VARIABLES: dict[str, str] = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "humidity_percent",
    "dew_point_2m": "dew_point_c",
    "apparent_temperature": "apparent_temperature_c",
    "precipitation": "precipitation_mm",
    "rain": "rain_mm",
    "snowfall": "snowfall_cm",
    "snow_depth": "snow_depth_m",
    "weather_code": "weather_code",
    "pressure_msl": "pressure_msl_hpa",
    "surface_pressure": "surface_pressure_hpa",
    "cloud_cover": "cloud_cover_percent",
    "cloud_cover_low": "cloud_cover_low_percent",
    "cloud_cover_mid": "cloud_cover_mid_percent",
    "cloud_cover_high": "cloud_cover_high_percent",
    "visibility": "visibility_m",
    "evapotranspiration": "evapotranspiration_mm",
    "vapour_pressure_deficit": "vapour_pressure_deficit_kpa",
    "wind_speed_10m": "wind_speed_10m_kmh",
    "wind_speed_100m": "wind_speed_100m_kmh",
    "wind_direction_10m": "wind_direction_10m_deg",
    "wind_direction_100m": "wind_direction_100m_deg",
    "wind_gusts_10m": "wind_gusts_10m_kmh",
    "soil_temperature_0_to_7cm": "soil_temp_0_7cm_c",
    "soil_temperature_7_to_28cm": "soil_temp_7_28cm_c",
    "soil_moisture_0_to_7cm": "soil_moisture_0_7cm",
    "soil_moisture_7_to_28cm": "soil_moisture_7_28cm",
}

# Ordre des colonnes du CSV : identique au schéma des tables Hive (hive/01_staging.sql)
COLUMNS: list[str] = ["city", *VARIABLES.values(), "timestamp_utc"]
