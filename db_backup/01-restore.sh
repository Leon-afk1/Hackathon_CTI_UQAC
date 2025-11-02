#!/bin/bash
set -e

echo "--- DEBUT : Restauration avec pg_restore ---"

# Utilise pg_restore pour charger le backup binaire.
pg_restore --verbose --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB" "/docker-entrypoint-initdb.d/events-bis.backup"

echo "--- FIN : Restauration terminee. ---"