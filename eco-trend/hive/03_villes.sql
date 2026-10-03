-- Table de référence des villes (coordonnées GPS), pour la carte du tableau de bord.
-- Source : data/villes.csv, généré depuis ingestion/config.py.

DROP TABLE IF EXISTS villes;

CREATE EXTERNAL TABLE villes (
    city STRING,
    latitude DOUBLE,
    longitude DOUBLE
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/data/eco_trend/ref/villes';
