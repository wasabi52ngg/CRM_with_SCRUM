# CRM для IT-компании (Django)

## Запуск локально

1. Создать и активировать venv
```bash
python -m venv venv
source venv/bin/activate
```
2. Установить зависимости
```bash
pip install -r requirements.txt
```
3. Применить миграции
```bash
python manage.py migrate
```
4. Создать суперпользователя
```bash
python manage.py createsuperuser
```
5. Запуск сервера
```bash
python manage.py runserver
```

Публичная форма заявки: `/request/`
Админ-панель: `/admin/`
