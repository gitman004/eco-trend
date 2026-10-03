-- Température moyenne annuelle par ville : la tendance de réchauffement sur la période.
-- Les années incomplètes (première et dernière) sont exclues pour ne pas biaiser la moyenne.
WITH bornes AS (
    SELECT MIN(year) AS premiere, MAX(year) AS derniere FROM meteo_data
)
SELECT
    m.city,
    m.year,
    ROUND(AVG(m.temperature_c), 2) AS temperature_moyenne_c
FROM meteo_data m
CROSS JOIN bornes b
WHERE m.year > b.premiere AND m.year < b.derniere
GROUP BY m.city, m.year
ORDER BY m.city, m.year;
