#!/bin/sh

echo "Waiting for db to be ready..."
sleep 5

echo "Applying migrations..."
python manage.py migrate

echo "Loading ingredients..."
python manage.py load_ingredients

echo "Starting server..."
gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000 
