#!/bin/sh
set -eu
: "${APP_DATABASE_PASSWORD:?Configure the application database password}"
PGOPTIONS='-c log_min_error_statement=panic' psql --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv application_password APP_DATABASE_PASSWORD
CREATE ROLE library LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD :'application_password';
ALTER DATABASE library OWNER TO library;
REVOKE ALL ON DATABASE library FROM PUBLIC;
GRANT CONNECT ON DATABASE library TO library;
SQL
