# Проект Foodgram: "Продуктовый помощник"

Веб-сервис, где пользователи могут публиковать рецепты, подписываться на авторов, добавлять рецепты в избранное и формировать список покупок в формате .txt.

## Технологический стек

- **Бэкенд:** Python 3.9, Django 3.2, Django REST Framework
- **База данных:** PostgreSQL
- **Веб-сервер:** Nginx
- **WSGI-сервер:** Gunicorn
- **Контейнеризация:** Docker, Docker Compose
- **CI/CD:** GitHub Actions

---

## Локальный запуск проекта

### 1. Предварительные требования

Убедитесь, что у вас установлены и запущены:
- Git
- Docker
- Docker Compose

### 2. Установка

**Шаг 1. Клонирование репозитория**

```bash
git clone https://github.com/PaiNaiP/foodgram-st.git
cd foodgram-st
```

**Шаг 2. Создание файла переменных окружения**

В директории `infra/` создайте файл `.env` со следующим содержимым. Эти значения используются по умолчанию в `docker-compose.yml`.

```env
# Ключ Django
SECRET_KEY="$!0&8sl(l7%+n3z@_an0*c+t6#1%6)@x18%f*71%&0r$mf+ujk"

# Настройки базы данных
DB_ENGINE=django.db.backends.postgresql
DB_NAME=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# Режим отладки (0 - выключен, 1 - включен)
DEBUG=0
```

**Шаг 3. Сборка и запуск контейнеров**

```bash
cd infra/
docker compose up -d --build
```
Флаг `-d` запустит контейнеры в фоновом режиме.

### 3. Первичная настройка базы данных

После того как контейнеры будут запущены, выполните следующие команды в другом терминале для настройки базы данных. **Они должны выполняться из директории `infra/`**.

**Применение миграций:**
```bash
docker-compose exec backend python manage.py migrate
```

**Загрузка ингредиентов в базу данных:**
```bash
docker-compose exec backend python manage.py load_ingredients
```

**Создание суперпользователя:**
```bash
docker compose exec backend python manage.py createsuperuser
```
Следуйте инструкциям в терминале для создания администратора.

---

## Использование

После успешного запуска проект будет доступен по следующим адресам:

- **Сайт:** `http://localhost/`
- **Панель администратора:** `http://localhost:8000/admin/`
- **[Документация API (ReDoc)](http://localhost/api/docs/)**

### Тестирование API

Для тестирования API можно использовать предоставленную коллекцию Postman.
- **Файл коллекции:** `postman_collection/foodgram_collection.json`
- Импортируйте коллекцию в Postman и используйте ее для отправки запросов к вашему локально запущенному сервису.
Весь код выполнен так, чтобы все тесты выполнялись, сейчас именно так.
---

## Автор проекта

- **[Батыгина Екатерина Ильинична](https://github.com/PaiNaiP)**
- **Email:** [RedBlueShip@yandex.ru](mailto:RedBlueShip@yandex.ru)

Хорошей вам проверки!


