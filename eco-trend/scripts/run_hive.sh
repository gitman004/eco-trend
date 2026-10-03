#!/usr/bin/env bash
# Crée les tables Hive et charge la table ORC partitionnée, dans l'ordre.
#
# Usage : scripts/run_hive.sh
# Variable : HIVE_URL (par défaut jdbc:hive2://localhost:10000/default)
set -euo pipefail

HIVE_URL="${HIVE_URL:-jdbc:hive2://localhost:10000/default}"
HIVE_DIR="$(cd "$(dirname "$0")/../hive" && pwd)"

for sql in 01_staging.sql 03_villes.sql 02_meteo_data.sql; do
    echo "== $sql"
    beeline -u "$HIVE_URL" --silent=true -f "$HIVE_DIR/$sql"
done
