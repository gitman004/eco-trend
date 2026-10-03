#!/usr/bin/env bash
# Déploie Apache Superset dans un conteneur Docker sur le nœud maître.
#
# Pourquoi Docker : Superset et Hadoop demandent des versions de bibliothèques
# Python incompatibles ; le conteneur isole Superset sans toucher au cluster.
# Port : YARN utilise déjà 8088 sur l'hôte, Superset est donc exposé sur 8080.
#
# Usage : SUPERSET_ADMIN_PASSWORD='...' scripts/deploy_superset.sh
#         (sans mot de passe fourni, un mot de passe aléatoire est généré et affiché une fois)
set -euo pipefail

CONTAINER=superset
HOST_PORT="${SUPERSET_PORT:-8080}"
ADMIN_USER="${SUPERSET_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${SUPERSET_ADMIN_PASSWORD:-$(openssl rand -base64 18)}"
SECRET_KEY="${SUPERSET_SECRET_KEY:-$(openssl rand -base64 42)}"

if ! command -v docker > /dev/null; then
    echo "Docker est requis : sudo apt-get install -y docker.io" >&2
    exit 1
fi

echo "Suppression d'une éventuelle instance précédente..."
docker rm -f "$CONTAINER" > /dev/null 2>&1 || true

echo "Démarrage de Superset sur le port $HOST_PORT..."
docker run -d --name "$CONTAINER" \
    -p "$HOST_PORT:8088" \
    -e SUPERSET_SECRET_KEY="$SECRET_KEY" \
    apache/superset > /dev/null

echo "Attente du démarrage du serveur..."
for _ in $(seq 1 30); do
    if docker exec "$CONTAINER" curl -sf http://localhost:8088/health > /dev/null 2>&1; then
        break
    fi
    sleep 2
done

echo "Installation du pilote Hive (PyHive)..."
docker exec "$CONTAINER" pip install --quiet pyhive thrift thrift-sasl pure-sasl

echo "Initialisation de la base interne et du compte administrateur..."
docker exec "$CONTAINER" superset db upgrade
docker exec "$CONTAINER" superset fab create-admin \
    --username "$ADMIN_USER" --firstname Admin --lastname Superset \
    --email "$ADMIN_USER@localhost" --password "$ADMIN_PASSWORD"
docker exec "$CONTAINER" superset init

docker restart "$CONTAINER" > /dev/null

HOST_IP="$(hostname -I | awk '{print $1}')"
cat <<EOF

Superset est prêt : http://$HOST_IP:$HOST_PORT
  Utilisateur  : $ADMIN_USER
  Mot de passe : $ADMIN_PASSWORD   (affiché une seule fois, à conserver)

Connexion à Hive dans Superset (Settings > Database Connections > + Database > Apache Hive) :
  hive://$HOST_IP:10000/default
  Utiliser l'IP de l'hôte et non « localhost » : dans le conteneur, localhost désigne le conteneur.
EOF
