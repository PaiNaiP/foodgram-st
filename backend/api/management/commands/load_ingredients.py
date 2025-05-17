import json
from django.core.management.base import BaseCommand
from django.db import transaction
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из JSON файла'

    def handle(self, *args, **options):
        try:
            # Формируем правильный путь к файлу
            file_path = '/mnt/data/ingredients.json'

            self.stdout.write(f"Пытаемся загрузить данные из: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                with transaction.atomic():
                    created_count = 0
                    existing_count = 0

                    for item in data:
                        obj, created = Ingredient.objects.get_or_create(
                            name=item['name'],
                            defaults={'measurement_unit': item['measurement_unit']}
                        )
                        if created:
                            created_count += 1
                        else:
                            existing_count += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Успешно загружено:\n'
                            f'Создано новых: {created_count}\n'
                            f'Уже существовало: {existing_count}\n'
                            f'Всего в базе: {Ingredient.objects.count()}'
                        )
                    )
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f'Файл не найден по пути: {file_path}\n'
                                 f'Проверьте, что файл ingredients.json находится в директории data/')
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка: {str(e)}'))
            raise
