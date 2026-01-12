#!/bin/bash
set -e

# Create datastore database and readonly user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE datastore;
    CREATE USER datastore_ro WITH PASSWORD 'password';
    GRANT CONNECT ON DATABASE datastore TO datastore_ro;
EOSQL

echo "Datastore database created"
