#!/bin/sh
set -e

echo "--- DEBUT : Restauration avec pg_restore ---"

# Utilise pg_restore pour charger le backup binaire.
pg_restore --verbose --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB" "/docker-entrypoint-initdb.d/events-bis.backup" || echo "Erreur lors de la restauration, mais on continue..."

echo "--- FIN : Restauration terminee. ---"
