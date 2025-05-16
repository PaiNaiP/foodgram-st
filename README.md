# Foodgram – Продуктовый помощник

Проект Foodgram позволяет пользователям публиковать рецепты, добавлять их в избранное, создавать список покупок и загружать его в формате TXT. 
## 📦 Стек технологий

- Python, Django, Django REST Framework
- PostgreSQL
- Docker, Docker Compose
- Nginx + Gunicorn
- GitHub Actions (CI/CD)
- Postman (для тестирования API)

## Как запустить проект локально в Docker

### 1. Клонировать репозиторий:

```bash
cd infra
```
2. Создать .env файл
Создайте файл ../backend/.env со следующим содержимым:

```
SECRET_KEY="$!0&8sl(l7%+n3z@_an0*c+t6#1%6)@x18%f*71%&0r$mf+ujk" 
DB_ENGINE=django.db.backends.postgresql 
DB_NAME=postgres 
POSTGRES_USER=postgres 
POSTGRES_PASSWORD=postgres 
DB_HOST=db 
DB_PORT=5432 
DEBUG=0
```
3. Собрать и запустить контейнеры:
```
docker-compose up -d --build
```
Проект будет доступен по адресу:
http://localhost/

⚙️ Команды внутри контейнера backend
Собрать статику:
```
docker-compose exec backend python manage.py collectstatic --noinput
```
Применить миграции:
```
docker-compose exec backend python manage.py migrate
```
Создать суперпользователя:
```
docker-compose exec backend python manage.py createsuperuser
```
Тестирование API
Коллекция Postman
Файл с готовыми запросами находится в папке:
postman_collection/foodgram_collection.json

Импортируйте его в Postman и используйте для проверки API.
Не забудьте указать переменную base_url, например:
http://localhost или адрес вашего сервера.

CI/CD и Docker Hub
Проект автоматически собирается и выкладывается на Docker Hub при пуше в ветку main.
Также запускается деплой на сервер через GitHub Actions.

Админка работает на http://localhost:8000/admin

Автор проекта: Батыгина Екатерина Ильинична 

Хорошей вам проверки!😉


