#!/usr/bin/env bash
# Перенос данных из db.sqlite3 в локальный PostgreSQL (itcrm/itcrm@localhost:5432)
set -euo pipefail
cd "$(dirname "$0")/.."

export POSTGRES_DB=itcrm
export POSTGRES_USER=itcrm
export POSTGRES_PASSWORD=itcrm
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432

PY="${PY:-.venv/bin/python}"

echo "1. Dump SQLite..."
USE_SQLITE=1 "$PY" manage.py dumpdata \
  --natural-foreign --natural-primary \
  -e contenttypes -e auth.Permission \
  --indent 2 -o data_backup.json

echo "1b. Fix invalid phones in dump..."
"$PY" scripts/sanitize_fixture.py data_backup.json

echo "1c. Fix invalid phones in SQLite..."
USE_SQLITE=1 "$PY" manage.py shell -c "
import re
from django.contrib.auth import get_user_model
User = get_user_model()
pat = re.compile(r'^\\+\\d-\\d{3}-\\d{3}-\\d{2}-\\d{2}$')
for u in User.objects.all():
    if not pat.match(u.phone or ''):
        u.phone = '+7-000-000-00-00'
        u.save(update_fields=['phone'])
print('SQLite phones OK')
"

echo "2. Migrate PostgreSQL..."
"$PY" manage.py migrate --noinput

echo "3. Load data into PostgreSQL..."
"$PY" manage.py loaddata data_backup.json

echo "Done. Run: set -a && source .env && set +a && python manage.py runserver"
