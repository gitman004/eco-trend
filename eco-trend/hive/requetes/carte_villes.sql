-- Données de la carte : moyenne de température et cumul annuel moyen de pluie par ville,
-- avec les coordonnées GPS de la table de référence.
SELECT
    v.city,
    v.latitude,
    v.longitude,
    ROUND(AVG(m.temperature_c), 2)                                AS temperature_moyenne_c,
    ROUND(SUM(m.precipitation_mm) / COUNT(DISTINCT m.year), 1)    AS pluie_annuelle_moyenne_mm
FROM meteo_data m
JOIN villes v ON v.city = m.city
GROUP BY v.city, v.latitude, v.longitude;
