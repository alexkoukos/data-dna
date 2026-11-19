#!/bin/sh
# Runs once on a fresh vault volume (Postgres docker-entrypoint-initdb.d), as the admin user.
# Loads the schema, then creates the role the app uses: no superuser, no CREATE anything, and
# only the table rights it needs. The admin account is used for nothing after this.
set -eu
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /schema/init.sql
psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v app_user="$APP_USER" -v app_pw="$APP_PASSWORD" <<'SQL'
CREATE ROLE :"app_user" LOGIN PASSWORD :'app_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
GRANT SELECT, INSERT, UPDATE, DELETE ON shares, meta TO :"app_user";
SQL
