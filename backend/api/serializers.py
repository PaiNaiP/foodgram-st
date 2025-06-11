from django.contrib.auth import get_user_model
from rest_framework import serializers
from djoser.serializers import UserSerializer as DjoserUserSerializer
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (
    Recipe, Ingredient, RecipeIngredient,
    Favorite, ShoppingCart
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
        read_only_fields = fields

    def get_is_subscribed(self, user):
        return (
            self.context['request'].user.is_authenticated
            and user.authors.filter(
                user=self.context['request'].user
            ).exists()
        )


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Ingredient."""
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit']


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели RecipeIngredient."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'name', 'measurement_unit', 'amount']


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe (только чтение)."""
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True, source='ingredient_amounts', read_only=True
    )
    image = serializers.ImageField(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            'id', 'author', 'name', 'image', 'text',
            'cooking_time', 'ingredients',
            'is_favorited', 'is_in_shopping_cart'
        ]

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


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого представления рецепта."""
    image = Base64ImageField(required=False, read_only=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class AuthorWithRecipesSerializer(UserSerializer):
    """Сериализатор для авторов с их рецептами."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, author):
        request = self.context.get('request')
        limit = None
        if request:
            try:
                limit_str = request.query_params.get('recipes_limit')
                if limit_str and limit_str.isdigit():
                    limit = int(limit_str)
            except (ValueError, TypeError):
                pass

        recipes = author.recipes.all()
        if limit is not None:
            recipes = recipes[:limit]

        return ShortRecipeSerializer(recipes, many=True, context={'request': request}).data


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов для создания рецепта."""
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(write_only=True, min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов (только запись)."""
    ingredients = RecipeIngredientCreateSerializer(
        many=True, source='ingredient_amounts'
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('ingredients', 'image', 'name', 'text', 'cooking_time')

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError('Это поле не может быть пустым.')
        return value

    def validate(self, data):
        ingredients = data.get('ingredient_amounts')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Нужно добавить хотя бы один ингредиент.'}
            )

        ingredient_ids = [item['id'] for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться.'}
            )
        return data

    def _create_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=data['id'],
                amount=data['amount']
            ) for data in ingredients_data
        )

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredient_amounts')
        recipe = super().create(validated_data)
        self._create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredient_amounts', None)
        if ingredients_data is not None:
            instance.ingredients.clear()
            self._create_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)

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
