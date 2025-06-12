import re
from rest_framework import serializers


def validate_username(value):
    if value.lower() == 'me':
        raise serializers.ValidationError(
            'Использовать имя "me" в качестве username запрещено.'
        )
    invalid_chars = set(re.findall(r'[^\w.@+-]', value))
    if invalid_chars:
        raise serializers.ValidationError(
            f'Недопустимые символы в имени пользователя: {"".join(invalid_chars)}'
        )
    return value
