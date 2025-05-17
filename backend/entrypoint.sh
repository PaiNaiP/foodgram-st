#!/bin/sh

# Ожидание запуска базы данных 
echo "Waiting for db to be ready..."
sleep 5

# Применение миграций
echo "Applying migrations..."
python manage.py migrate

# Загрузка ингредиентов (выполнится один раз, можно сделать проверку на пустую таблицу)
echo "Loading ingredients..."
python manage.py load_ingredients

# Запуск Gunicorn
echo "Starting server..."
gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000
