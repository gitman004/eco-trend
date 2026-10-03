#!/usr/bin/env bash
# Démarre HiveServer2 en arrière-plan (connexions JDBC sur le port 10000, utilisées par Superset).
set -euo pipefail

LOG="${HIVE_LOG:-/tmp/hiveserver2.log}"
nohup hive --service hiveserver2 > "$LOG" 2>&1 &
echo "HiveServer2 démarré (PID $!). Journal : $LOG"
echo "Le port 10000 est disponible après environ une minute : beeline -u jdbc:hive2://localhost:10000"
