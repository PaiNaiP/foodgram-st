from django.contrib.auth import get_user_model
from rest_framework import serializers
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import viewsets
from rest_framework import permissions

from recipes.models import (
    Recipe, Ingredient, RecipeIngredient,
    Favorite, ShoppingCart, Subscription, User
)

User = get_user_model()


class UserSerializer(DjoserUserSerializer):
    """Сериализатор для модели User."""
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True)

    class Meta(DjoserUserSerializer.Meta):
        fields = (
            'id', 'email', 'username',
            'first_name', 'last_name',
            'is_subscribed', 'avatar',
        )

    def get_is_subscribed(self, author):
        """Возвращает флаг подписки текущего пользователя на автора."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Subscription.objects.filter(user=request.user, author=author).exists()
        )


class UserListSerializer(DjoserUserSerializer):
    """Сериализатор для списка пользователей."""
    avatar = serializers.ImageField(read_only=True)

    class Meta(DjoserUserSerializer.Meta):
        fields = (
            'id', 'email', 'username',
            'first_name', 'last_name', 'avatar',
        )


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели RecipeIngredient."""
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source='ingredient'
    )
    name = serializers.CharField(
        source='ingredient.name', read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )
    amount = serializers.IntegerField(
        min_value=1,
        error_messages={'min_value': 'Количество продукта должно быть больше нуля.'}
    )

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'measurement_unit', 'amount']


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe."""
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='ingredient_amounts'
    )
    image = Base64ImageField(required=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'author', 'name', 'image', 'text',
            'cooking_time', 'ingredients',
            'is_favorited', 'is_in_shopping_cart'
        ]
        read_only_fields = ('author', 'pub_date')

    def get_is_favorited(self, recipe):
        """Возвращает флаг добавления рецепта в избранное."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Favorite.objects.filter(user=request.user, recipe=recipe).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        """Возвращает флаг добавления рецепта в корзину."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and ShoppingCart.objects.filter(user=request.user, recipe=recipe).exists()
        )

    def create_ingredients(self, recipe, ingredients_data):
        """Создает ингредиенты для рецепта."""
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            ) for ingredient_data in ingredients_data
        ])

    def create(self, validated_data):
        """Создает рецепт с ингредиентами."""
        ingredients_data = validated_data.pop('ingredient_amounts')
        recipe = super().create(validated_data)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        """Обновляет рецепт."""
        return super().update(instance, validated_data)


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого представления рецепта."""
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class AuthorWithRecipesSerializer(UserSerializer):
    """Сериализатор для автора с ограниченным списком рецептов."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes.count', read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count',)

    def get_recipes(self, author):
        """Возвращает рецепты автора с учетом лимита."""
        request = self.context.get('request')
        limit = self.context.get('recipes_limit')

        queryset = author.recipes.all()
        if limit is not None:
            queryset = queryset[:limit]

        return ShortRecipeSerializer(
            queryset, many=True, context={'request': request}
        ).data


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания подписки."""
    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def to_representation(self, instance):
        return AuthorWithRecipesSerializer(
            instance.author,
            context={'request': self.context.get('request')}
        ).data


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов для создания рецепта."""
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(write_only=True, min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeCreateSerializer(RecipeSerializer):
    """Сериализатор для создания и обновления рецептов."""
    ingredients = RecipeIngredientCreateSerializer(many=True, source='ingredient_amounts')
    image = Base64ImageField(required=True, allow_null=False)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError('Это поле не может быть пустым.')
        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Нужно добавить хотя бы один ингредиент.'
            )

        ingredient_ids = [item['id'] for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )

        return value

    def create(self, validated_data):
        author = validated_data.pop('author')
        ingredients_data = validated_data.pop('ingredient_amounts')

        recipe = Recipe.objects.create(author=author, **validated_data)

        ingredients_to_create = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=data['id'],
                amount=data['amount']
            ) for data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(ingredients_to_create)

        return recipe

    def update(self, instance, validated_data):
        if 'ingredient_amounts' not in validated_data:
            raise serializers.ValidationError({
                'ingredients': 'Это поле обязательно при обновлении рецепта.'
            })

        ingredients_data = validated_data.pop('ingredient_amounts')
        instance.ingredients.clear()
        ingredients_to_create = [
            RecipeIngredient(
                recipe=instance,
                ingredient=data['id'],
                amount=data['amount']
            ) for data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(ingredients_to_create)

        # Обновляем остальные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

    def to_representation(self, instance):
        return RecipeSerializer(
            instance,
            context={'request': self.context.get('request')}
        ).data


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для загрузки аватара."""
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None
    queryset = Ingredient.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset
