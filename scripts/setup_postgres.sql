-- Локальный PostgreSQL: пользователь и БД для IT CRM
-- Запуск: sudo -u postgres psql -f scripts/setup_postgres.sql

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'itcrm') THEN
    CREATE ROLE itcrm WITH LOGIN PASSWORD 'itcrm';
  END IF;
END
$$;

-- template0 без проблемной локали template1 (collation mismatch после обновления ОС)
SELECT 'CREATE DATABASE itcrm OWNER itcrm TEMPLATE template0 ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'itcrm')\gexec

GRANT ALL PRIVILEGES ON DATABASE itcrm TO itcrm;

-- Права на схему public (PostgreSQL 15+)
\c itcrm
GRANT ALL ON SCHEMA public TO itcrm;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO itcrm;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO itcrm;
