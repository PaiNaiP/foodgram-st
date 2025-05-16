import json
from django.core.management.base import BaseCommand
from django.db import transaction
from ingredients.models import Ingredient  


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Основной метод команды для загрузки ингредиентов из JSON файла.
        Выполняет загрузку в рамках атомарной транзакции.
        """
        try:
            # Открываем файл с данными ингредиентов
            with open('/app/data/ingredients.json', 'r', encoding='utf-8') as f:
                data = json.load(f)

                with transaction.atomic():
                    created_count = 0
                    existing_count = 0

                    # Обрабатываем каждый элемент из JSON
                    for item in data:
                        obj, created = Ingredient.objects.get_or_create(
                            name=item['name'],
                            defaults={'measurement_unit': item['measurement_unit']}
                        )
                        if created:
                            created_count += 1
                        else:
                            existing_count += 1

                    # Выводим результат загрузки
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Результат загрузки:\n'
                            f'Создано новых: {created_count}\n'
                            f'Уже существовало: {existing_count}\n'
                            f'Всего в базе: {Ingredient.objects.count()}'
                        )
                    )
        except Exception as e:
            # В случае ошибки выводим сообщение и пробрасываем исключение
            self.stdout.write(self.style.ERROR(f'Ошибка: {str(e)}'))
            raise e
