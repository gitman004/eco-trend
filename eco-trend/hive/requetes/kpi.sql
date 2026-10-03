-- Indicateurs clés du tableau de bord, sur toute la période et toutes les villes
SELECT
    ROUND(AVG(temperature_c), 2)     AS temperature_moyenne_c,
    MAX(temperature_c)               AS temperature_max_c,
    MIN(temperature_c)               AS temperature_min_c,
    ROUND(AVG(humidity_percent), 2)  AS humidite_moyenne_pct,
    ROUND(SUM(precipitation_mm), 1)  AS cumul_precipitations_mm,
    MAX(wind_gusts_10m_kmh)          AS rafale_max_kmh
FROM meteo_data;
