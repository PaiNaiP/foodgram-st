from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from django.urls import reverse
from django.utils import timezone
import io

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import View

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
    RecipeSerializer,
    ShortRecipeSerializer,
    AvatarSerializer,
    RecipeCreateSerializer,
    UserSerializer,
    UserListSerializer,
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        if self.action in ('retrieve', 'me'):
            return UserSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == 'retrieve':
            return [permissions.AllowAny()]
        return super().get_permissions()

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
                    {'errors': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            context = {'request': request}
            recipes_limit_str = request.query_params.get('recipes_limit')
            if recipes_limit_str and recipes_limit_str.isdigit():
                context['recipes_limit'] = int(recipes_limit_str)

            serializer = AuthorWithRecipesSerializer(author, context=context)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        subscription = Subscription.objects.filter(user=user, author=author).first()
        if not subscription:
            return Response(
                {'errors': 'Вы не подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Предоставляет доступ к списку подписок пользователя."""
    permission_classes = [IsAuthenticated]
    serializer_class = AuthorWithRecipesSerializer
    pagination_class = LimitPageNumberPagination

    def get_queryset(self):
        return User.objects.filter(authors__user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        context = {'request': request}

        recipes_limit_str = request.query_params.get('recipes_limit')
        if recipes_limit_str and recipes_limit_str.isdigit():
            context['recipes_limit'] = int(recipes_limit_str)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True, context=context)
        return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    """
    Предоставляет CRUD-операции для рецептов,
    а также управление избранным и корзиной.
    """
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeCreateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @staticmethod
    def _add_remove_from_list(request, pk, model, error_location_string):
        """Вспомогательный метод для добавления/удаления из списков (избранное, корзина)."""
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user

        if request.method == 'POST':
            instance, created = model.objects.get_or_create(user=user, recipe=recipe)
            if not created:
                return Response(
                    {'errors': f'Рецепт "{recipe.name}" уже {error_location_string}.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = ShortRecipeSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        instance = model.objects.filter(user=user, recipe=recipe).first()
        if not instance:
            return Response(
                {'errors': f'Этого рецепта нет {error_location_string}.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавляет или удаляет рецепт из избранного."""
        return RecipeViewSet._add_remove_from_list(
            request, pk, Favorite, "в избранном"
        )

    @action(detail=True, methods=['post', 'delete'], permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавляет или удаляет рецепт из корзины."""
        return RecipeViewSet._add_remove_from_list(
            request, pk, ShoppingCart, "в корзине"
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
        recipe = Recipe.objects.filter(pk=pk).first()
        if recipe:
            path = reverse('recipe-short-link', kwargs={'recipe_id': recipe.id})
        else:
            path = '/'

        absolute_url = request.build_absolute_uri(path)
        return Response({'short-link': absolute_url}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def download_shopping_cart(self, request):
        """Формирует и отдает текстовый файл со списком покупок."""
        user = request.user
        recipe_ids = user.shopping_cart.values_list('recipe_id', flat=True)

        if not recipe_ids:
            return Response(
                {'errors': 'Ваша корзина пуста.'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
              for recipe in recipes],
        ]

        txt_content = '\n'.join(report_lines)
        filename = f'shopping_list_{user.username}.txt'

        file_like_object = io.BytesIO(txt_content.encode('utf-8'))

        return FileResponse(
            file_like_object,
            as_attachment=True,
            filename=filename
        )


class RecipeShortLinkRedirectView(View):
    """Осуществляет редирект с короткой ссылки на страницу рецепта."""
    def get(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        frontend_url = f'/recipes/{recipe.id}'
        return redirect(frontend_url)
