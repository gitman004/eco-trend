-- Table analytique : format colonnaire ORC compressé, partitionnée par année.
-- Une requête filtrée sur une année (WHERE year = 2023) ne lit que le dossier
-- de cette année (partition pruning) au lieu de parcourir tout l'historique.

DROP TABLE IF EXISTS meteo_data;

CREATE TABLE meteo_data (
    city STRING,
    temperature_c FLOAT,
    humidity_percent FLOAT,
    dew_point_c FLOAT,
    apparent_temperature_c FLOAT,
    precipitation_mm FLOAT,
    rain_mm FLOAT,
    snowfall_cm FLOAT,
    snow_depth_m FLOAT,
    weather_code INT,
    pressure_msl_hpa FLOAT,
    surface_pressure_hpa FLOAT,
    cloud_cover_percent INT,
    cloud_cover_low_percent INT,
    cloud_cover_mid_percent INT,
    cloud_cover_high_percent INT,
    visibility_m FLOAT,
    evapotranspiration_mm FLOAT,
    vapour_pressure_deficit_kpa FLOAT,
    wind_speed_10m_kmh FLOAT,
    wind_speed_100m_kmh FLOAT,
    wind_direction_10m_deg INT,
    wind_direction_100m_deg INT,
    wind_gusts_10m_kmh FLOAT,
    soil_temp_0_7cm_c FLOAT,
    soil_temp_7_28cm_c FLOAT,
    soil_moisture_0_7cm FLOAT,
    soil_moisture_7_28cm FLOAT,
    timestamp_utc TIMESTAMP,
    month INT
)
PARTITIONED BY (year INT)
STORED AS ORC
TBLPROPERTIES ("orc.compress" = "ZLIB");

-- Chargement avec partitionnement dynamique : Hive calcule l'année de chaque
-- ligne et l'écrit dans le bon sous-dossier (year=2005, year=2006, ...).
SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;

INSERT OVERWRITE TABLE meteo_data PARTITION (year)
SELECT
    city, temperature_c, humidity_percent, dew_point_c, apparent_temperature_c,
    precipitation_mm, rain_mm, snowfall_cm, snow_depth_m, weather_code,
    pressure_msl_hpa, surface_pressure_hpa, cloud_cover_percent, cloud_cover_low_percent,
    cloud_cover_mid_percent, cloud_cover_high_percent, visibility_m, evapotranspiration_mm,
    vapour_pressure_deficit_kpa, wind_speed_10m_kmh, wind_speed_100m_kmh,
    wind_direction_10m_deg, wind_direction_100m_deg, wind_gusts_10m_kmh,
    soil_temp_0_7cm_c, soil_temp_7_28cm_c, soil_moisture_0_7cm, soil_moisture_7_28cm,
    -- Format API « 2024-01-01T13:00 » -> TIMESTAMP Hive
    CAST(CONCAT(REPLACE(timestamp_utc, 'T', ' '), ':00') AS TIMESTAMP) AS timestamp_utc,
    CAST(SUBSTR(timestamp_utc, 6, 2) AS INT) AS month,
    CAST(SUBSTR(timestamp_utc, 1, 4) AS INT) AS year
FROM meteo_staging;

-- Contrôle après chargement : nombre de lignes par année
SELECT year, COUNT(*) AS lignes FROM meteo_data GROUP BY year ORDER BY year;
