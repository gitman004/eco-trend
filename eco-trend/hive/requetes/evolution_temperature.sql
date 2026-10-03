-- Température moyenne, minimale et maximale par mois (toutes villes)
SELECT
    year,
    month,
    ROUND(AVG(temperature_c), 2) AS temperature_moyenne_c,
    MIN(temperature_c)           AS temperature_min_c,
    MAX(temperature_c)           AS temperature_max_c
FROM meteo_data
GROUP BY year, month
ORDER BY year, month;
