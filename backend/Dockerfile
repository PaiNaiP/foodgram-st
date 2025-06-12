FROM python:3.10

WORKDIR /app

COPY ./backend/requirements.txt /app/
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY ./backend/ /app/

# Копируем папку data из корневой директории проекта в контейнер
# Предпологается, что Dockerfile запускается из корня проекта,
# например: docker build -t foodgram-backend -f backend/Dockerfile .
COPY ./data/ /app/data/

CMD ["gunicorn", "foodgram.wsgi:application", "--bind", "0.0.0.0:8000"]