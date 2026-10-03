-- Cumuls mensuels de pluie et de neige (toutes villes)
SELECT
    year,
    month,
    ROUND(SUM(precipitation_mm), 1) AS precipitations_mm,
    ROUND(SUM(snowfall_cm), 1)      AS neige_cm
FROM meteo_data
GROUP BY year, month
ORDER BY year, month;
