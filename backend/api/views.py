from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from djoser.serializers import SetPasswordSerializer

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeFilter,
    ShoppingCart,
)
from users.models import Subscription

from .pagination import CustomPagination
from .serializers import (
    FavoriteSerializer,
    IngredientSerializer,
    RecipeSerializer,
    SubscriptionSerializer,
    UserAvatarSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


# ViewSet для отображения списка ингредиентов
class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        search_query = self.request.query_params.get('name', '')
        if search_query:
            # Фильтрация по началу или вхождению в имя ингредиента
            queryset = queryset.filter(
                Q(name__istartswith=search_query)
                | Q(name__icontains=search_query)
            ).order_by('name')
        return queryset


# ViewSet для управления пользователями и подписками
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        # Получение текущего пользователя
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='set_password')
    def set_password(self, request):
        serializer = SetPasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            current_password = serializer.validated_data['current_password']
            new_password = serializer.validated_data['new_password']
            if not user.check_password(current_password):
                return Response(
                    {"current_password": "Неверный текущий пароль"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(new_password)
            user.save()
            return Response({"status": "Пароль успешно изменён"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        # Обновление аватара
        serializer = UserAvatarSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['delete'], permission_classes=[permissions.IsAuthenticated], url_path='me/avatar')
    def delete_avatar(self, request):
        user = request.user
        if not user.avatar:
            return Response({'detail': 'Аватар отсутствует.'}, status=status.HTTP_400_BAD_REQUEST)
        user.avatar.delete(save=False)
        user.avatar = None
        user.save()
        return Response({'detail': 'Аватар успешно удалён.'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='subscriptions')
    def subscriptions(self, request):
        # Получение подписок пользователя
        recipes_limit = request.query_params.get('recipes_limit')
        subscriptions = Subscription.objects.filter(user=request.user).select_related('author')
        paginator = CustomPagination()
        page = paginator.paginate_queryset(subscriptions, request)
        serializer = SubscriptionSerializer(
            page,
            many=True,
            context={'request': request, 'recipes_limit': recipes_limit}
        )
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        user = request.user
        if author == user:
            return Response({'errors': 'Нельзя подписаться на самого себя'}, status=status.HTTP_400_BAD_REQUEST)
        if Subscription.objects.filter(user=user, author=author).exists():
            return Response({'errors': 'Вы уже подписаны'}, status=status.HTTP_400_BAD_REQUEST)
        subscription = Subscription.objects.create(user=user, author=author)
        serializer = SubscriptionSerializer(subscription, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        user = request.user
        subscription = Subscription.objects.filter(user=user, author=author)
        if not subscription.exists():
            return Response({'errors': 'Вы не подписаны'}, status=status.HTTP_400_BAD_REQUEST)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ViewSet для управления рецептами, избранным и корзиной
class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        is_favorited = self.request.query_params.get('is_favorited')
        author_id = self.request.query_params.get('author')

        if is_favorited in ('1', 'true', 'True'):
            if user.is_authenticated:
                queryset = queryset.filter(favorited_by__user=user)
            else:
                return Recipe.objects.none()

        if author_id:
            queryset = queryset.filter(author__id=author_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        if Favorite.objects.filter(user=user, recipe=recipe).exists():
            return Response({'errors': 'Уже в избранном'}, status=status.HTTP_400_BAD_REQUEST)
        favorite = Favorite.objects.create(user=user, recipe=recipe)
        serializer = FavoriteSerializer(favorite)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        favorite = Favorite.objects.filter(user=request.user, recipe=recipe)
        if favorite.exists():
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'errors': 'Не найдено в избранном'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request):
        user = request.user
        recipes = Recipe.objects.filter(in_shopping_carts__user=user)
        paginator = CustomPagination()
        page = paginator.paginate_queryset(recipes, request)
        serializer = RecipeSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    @shopping_cart.mapping.post
    def add_to_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            return Response({'errors': 'Рецепт уже в корзине.'}, status=status.HTTP_400_BAD_REQUEST)
        ShoppingCart.objects.create(user=user, recipe=recipe)
        serializer = RecipeSerializer(recipe, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def remove_from_cart(self, request, pk=None):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        cart_item = ShoppingCart.objects.filter(user=user, recipe=recipe)
        if cart_item.exists():
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'errors': 'Рецепта нет в корзине.'}, status=status.HTTP_400_BAD_REQUEST)


# Отдаёт короткую ссылку на рецепт
class RecipeLinkView(APIView):
    def get(self, request, id, format=None):
        recipe = get_object_or_404(Recipe, id=id)
        short_link = f"{settings.BASE_URL}/recipes/{recipe.id}"
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)


# Скачивание списка покупок в формате TXT
class DownloadShoppingCartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        shopping_cart = ShoppingCart.objects.filter(user=user)
        ingredients = {}

        # Подсчёт общего количества ингредиентов из всех рецептов в корзине
        for item in shopping_cart:
            for recipe_ingredient in item.recipe.ingredient_amounts.all():
                name = recipe_ingredient.ingredient.name
                amount = recipe_ingredient.amount
                unit = recipe_ingredient.ingredient.measurement_unit
                key = (name, unit)
                ingredients[key] = ingredients.get(key, 0) + amount

        sorted_ingredients = sorted(ingredients.items(), key=lambda x: x[0][0])

        txt_content = f"Список покупок для {user.username}\n\n"
        for (name, unit), amount in sorted_ingredients:
            txt_content += f"{name} ({unit}) — {amount}\n"

        response = HttpResponse(txt_content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response
