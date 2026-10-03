-- Table de staging : lecture directe du CSV déposé dans HDFS par scripts/load_to_hdfs.sh.
-- Table EXTERNE : la supprimer ne supprime pas les fichiers bruts.
-- L'ordre des colonnes est celui de ingestion/config.py (vérifié par les tests).

DROP TABLE IF EXISTS meteo_staging;

CREATE EXTERNAL TABLE meteo_staging (
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
    timestamp_utc STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/data/eco_trend/raw/meteo'
TBLPROPERTIES ("skip.header.line.count" = "1");
