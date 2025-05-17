#!/bin/bash

# Применяем миграции
python manage.py migrate

# Загружаем ингредиенты 
python manage.py load_ingredients

# Запускаем основной процесс (Gunicorn)
exec "$@"