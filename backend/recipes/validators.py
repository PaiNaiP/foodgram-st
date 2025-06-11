import re
from django.core.exceptions import ValidationError


def validate_username_chars(value):
    """
    Проверяет, что имя пользователя содержит только разрешённые символы.
    Разрешены: буквы, цифры и символы @ . + - _
    """
    invalid_chars = sorted(list(set(re.findall(r'[^\w.@+-]', value))))
    if invalid_chars:
        raise ValidationError(
            'Имя пользователя содержит недопустимые символы: '
            f'{" ".join(invalid_chars)}'
        )
