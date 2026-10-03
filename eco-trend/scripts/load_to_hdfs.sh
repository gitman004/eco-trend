#!/usr/bin/env bash
# Dépose le CSV collecté et la table de référence des villes dans HDFS,
# aux emplacements lus par les tables externes Hive (hive/01_staging.sql, hive/03_villes.sql).
#
# Usage : scripts/load_to_hdfs.sh [dossier_data]   (par défaut : data)
set -euo pipefail

DATA_DIR="${1:-data}"
HDFS_ROOT="${HDFS_ROOT:-/data/eco_trend}"
METEO_CSV="$DATA_DIR/meteo_data.csv"
VILLES_CSV="$DATA_DIR/villes.csv"

for f in "$METEO_CSV" "$VILLES_CSV"; do
    if [[ ! -f "$f" ]]; then
        echo "Fichier introuvable : $f (lancer d'abord : python -m ingestion.collect)" >&2
        exit 1
    fi
done

echo "Contrôle qualité avant chargement..."
python -m ingestion.quality "$METEO_CSV"

echo "Création des dossiers HDFS sous $HDFS_ROOT..."
hdfs dfs -mkdir -p "$HDFS_ROOT/raw/meteo" "$HDFS_ROOT/ref/villes"

echo "Copie des fichiers (remplace la version précédente)..."
hdfs dfs -put -f "$METEO_CSV" "$HDFS_ROOT/raw/meteo/meteo_data.csv"
hdfs dfs -put -f "$VILLES_CSV" "$HDFS_ROOT/ref/villes/villes.csv"

# Lecture et écriture pour le propriétaire et le groupe (dont l'utilisateur hive),
# lecture seule pour les autres : pas de 777.
hdfs dfs -chmod -R 775 "$HDFS_ROOT"

echo "Contenu de $HDFS_ROOT :"
hdfs dfs -du -h "$HDFS_ROOT/raw/meteo" "$HDFS_ROOT/ref/villes"
