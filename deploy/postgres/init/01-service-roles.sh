#!/bin/bash
# Runs once, when the data directory is first created. One role and one database per
# service; other roles cannot even connect to it (INV-PLT-003 isolation).
set -euo pipefail

create_service() {
  local name="$1" password
  password="$(cat "/run/secrets/${name}_db_password")"
  psql -v ON_ERROR_STOP=1 -v password="$password" -U postgres <<SQL
create role ${name} login password :'password';
create database ${name} owner ${name};
revoke connect on database ${name} from public;
SQL
}

create_service identity
