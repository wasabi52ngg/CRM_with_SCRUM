#!/usr/bin/env bash
# Сброс БД itcrm и повторный перенос из SQLite (только для локальной разработки)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Сбрасываю базу itcrm..."
sudo -u postgres psql <<'SQL'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'itcrm' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS itcrm;
CREATE DATABASE itcrm OWNER itcrm TEMPLATE template0 ENCODING 'UTF8';
GRANT ALL PRIVILEGES ON DATABASE itcrm TO itcrm;
SQL

sudo -u postgres psql -d itcrm <<'SQL'
GRANT ALL ON SCHEMA public TO itcrm;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO itcrm;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO itcrm;
SQL

./scripts/migrate_sqlite_to_postgres.sh
