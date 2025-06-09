from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Пользовательское разрешение, которое позволяет только автору объекта
    редактировать его. Чтение разрешено всем.
    """

    def has_permission(self, request, view):
        # Разрешения на чтение доступны для любого запроса,
        # анонимные пользователи могут только читать.
        if request.method in permissions.SAFE_METHODS:
            return True
        # Запросы на запись требуют аутентификации.
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Разрешения на чтение доступны для любого запроса,
        # поэтому мы всегда разрешаем GET, HEAD или OPTIONS запросы.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Разрешения на запись предоставляются только автору объекта.
        return obj.author == request.user 