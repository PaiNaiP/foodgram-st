import json
from django.core.management.base import BaseCommand
from django.conf import settings
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загружает ингредиенты из JSON файла в базу данных'

    def handle(self, *args, **options):
        file_path = settings.BASE_DIR / 'data' / 'ingredients.json'
        self.stdout.write(self.style.SUCCESS(f'Загрузка данных из {file_path}'))

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('Файл не найден. Прерывание.'))
            return

        existing_ingredients = set(
            Ingredient.objects.values_list('name', flat=True)
        )
        ingredients_to_create = []

        for item in data:
            if item['name'] not in existing_ingredients:
                ingredients_to_create.append(Ingredient(**item))

        if ingredients_to_create:
            Ingredient.objects.bulk_create(ingredients_to_create)
            self.stdout.write(self.style.SUCCESS(
                f'Успешно добавлено {len(ingredients_to_create)} новых ингредиентов.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                'Все ингредиенты уже существуют в базе данных.'
            ))
