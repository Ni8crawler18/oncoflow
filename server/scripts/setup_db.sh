#!/usr/bin/env bash
# One-time Postgres setup for OncoFlow.
# Creates the `oncoflow` role and database to match server/.env.
# Requires superuser access (sudo to the postgres OS user).
set -euo pipefail

DB_NAME="${DB_NAME:-oncoflow}"
DB_USER="${DB_USER:-oncoflow}"
DB_PASS="${DB_PASS:-oncoflow}"

echo "Creating role '${DB_USER}' and database '${DB_NAME}'…"

sudo -u postgres psql <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec
SQL

echo "Done. DATABASE_URL=postgresql+psycopg://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}"
