from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.urls import reverse
from django.utils import timezone

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from djoser.views import UserViewSet as DjoserUserViewSet

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingCart,
    Subscription,
)
from .filters import RecipeFilter
from .pagination import LimitPageNumberPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AuthorWithRecipesSerializer,
    IngredientSerializer,
    RecipeWriteSerializer,
    ShortRecipeSerializer,
    AvatarSerializer,
    UserSerializer,
)

User = get_user_model()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Предоставляет доступ к списку ингредиентов."""
    serializer_class = IngredientSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        search_query = self.request.query_params.get('name', '')
        if search_query:
            queryset = queryset.filter(
                name__startswith=search_query
            ).order_by('name')
        return queryset


class UserViewSet(DjoserUserViewSet):
    """
    Предоставляет доступ к пользователям и управление подписками.
    Наследуется от Djoser UserViewSet.
    """
    pagination_class = LimitPageNumberPagination
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.action == 'me':
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return UserSerializer
        if self.action == 'subscriptions':
            return AuthorWithRecipesSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=['post', 'put', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        """Управляет аватаром текущего пользователя."""
        user = request.user
        if request.method in ('POST', 'PUT'):
            serializer = AvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        """Возвращает пользователей, на которых подписан текущий пользователь."""
        user = request.user
        queryset = User.objects.filter(authors__user=user)
        page = self.paginate_queryset(queryset)
        serializer = AuthorWithRecipesSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        """Создает и удаляет подписку на пользователя."""
        author = get_object_or_404(User, id=id)
        user = request.user

        if request.method == 'POST':
            if user == author:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            subscription, created = Subscription.objects.get_or_create(
                user=user, author=author
            )
            if not created:
                return Response(
                    {'errors': f'Вы уже подписаны на пользователя {author.username}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            context = {'request': request}
            serializer = AuthorWithRecipesSerializer(author, context=context)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        get_object_or_404(Subscription, user=user, author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(viewsets.ModelViewSet):
    """
    Предоставляет CRUD-операции для рецептов,
    а также управление избранным и корзиной.
    """
    queryset = Recipe.objects.all()
    serializer_class = RecipeWriteSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = LimitPageNumberPagination

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @staticmethod
    def _add_remove_from_list(request, pk, model):
        """Вспомогательный метод для добавления/удаления из списков (избранное, корзина)."""
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        model_name_genitive = model._meta.verbose_name.lower()
        model_name_accusative = model._meta.verbose_name_plural.lower()

        if request.method == 'POST':
            instance, created = model.objects.get_or_create(user=user, recipe=recipe)
            if not created:
                return Response(
                    {'errors': f'Рецепт «{recipe.name}» уже в {model_name_accusative}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        instance = model.objects.filter(user=user, recipe=recipe)
        if not instance.exists():
            return Response(
                {'errors': f'Рецепта «{recipe.name}» нет в {model_name_genitive}.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавляет или удаляет рецепт из избранного."""
        return RecipeViewSet._add_remove_from_list(
            request, pk, Favorite
        )

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавляет или удаляет рецепт из корзины."""
        return RecipeViewSet._add_remove_from_list(
            request, pk, ShoppingCart
        )

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[permissions.AllowAny],
        url_path='get-link',
        url_name='get-link'
    )
    def get_link(self, request, pk=None):
        """Генерирует короткую ссылку на рецепт."""
        get_object_or_404(Recipe, pk=pk)
        path = reverse('recipes:recipe-short-link', kwargs={'recipe_id': pk})
        absolute_url = request.build_absolute_uri(path)
        return Response({'short-link': absolute_url}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        """Формирует и отдает текстовый файл со списком покупок."""
        user = request.user
        recipe_ids = user.shopping_carts.values_list('recipe_id', flat=True)

        ingredients = RecipeIngredient.objects.filter(
            recipe__id__in=recipe_ids
        ).values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        recipes = Recipe.objects.select_related('author').filter(id__in=recipe_ids).order_by('name')

        report_lines = [
            f'Список покупок для {user.get_full_name() or user.username}',
            f'Дата: {timezone.now().strftime("%d %B %Y")}',
            '',
            'Продукты к покупке:',
            *[
                f'{i}. {ing["ingredient__name"].capitalize()} '
                f'({ing["ingredient__measurement_unit"]}) — {ing["total_amount"]}'
                for i, ing in enumerate(ingredients, 1)],
            '',
            'Из рецептов:',
            *[f'- {recipe.name} (автор: {recipe.author.get_full_name() or recipe.author.username})'
              for recipe in recipes]
        ]
        txt_content = '\n'.join(report_lines)

        return FileResponse(
            txt_content,
            as_attachment=True,
            filename='shopping_list.txt'
        )
