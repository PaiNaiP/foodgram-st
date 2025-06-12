FROM python:3.10

WORKDIR /app

COPY backend/requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend/ /app/

CMD ["gunicorn", "foodgram.wsgi:application", "--bind", "0.0.0.0:8000"]
