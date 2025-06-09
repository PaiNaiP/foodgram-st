import re
from django.core.exceptions import ValidationError


def validate_username_chars(value):
    """
    Проверяет, что имя пользователя содержит только разрешённые символы.
    Разрешены: буквы, цифры и символы @ . + - _
    """
    allowed_chars = re.compile(r'^[\w.@+-]+$')
    if not allowed_chars.match(value):
        invalid_chars = set(re.findall(r'[^\w.@+-]', value))
        raise ValidationError(
            f'Имя пользователя содержит недопустимые символы: {" ".join(invalid_chars)}'
        ) 