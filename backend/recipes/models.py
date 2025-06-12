from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from .validators import validate_username


class User(AbstractUser):
    """
    Кастомная модель пользователя с электронной почтой как уникальным идентификатором,
    а также полями для подписки и аватара.
    """
    username = models.CharField(
        "Никнейм",
        max_length=150,
        unique=True,
        validators=[validate_username],
        help_text=(
            "Обязательное поле. Не более 150 символов. "
            "Разрешены: буквы, цифры и символы @ . + - _"
        ),
    )
    email = models.EmailField(
        "Адрес электронной почты",
        max_length=254,
        unique=True,
    )
    first_name = models.CharField("Имя", max_length=150)
    last_name = models.CharField("Фамилия", max_length=150)
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        verbose_name='Аватар'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.email


class Subscription(models.Model):
    """
    Модель подписки пользователя на автора рецептов.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authors'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(fields=['user', 'author'], name='unique_subscription')
        ]

    def __str__(self):
        return f"{self.user} подписан на {self.author}"


class Ingredient(models.Model):
    """Модель ингредиента с названием и единицей измерения."""
    name = models.CharField(max_length=128)
    measurement_unit = models.CharField(max_length=64)

    class Meta:
        ordering = ('name',)
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        constraints = [
            models.UniqueConstraint(fields=['name', 'measurement_unit'], name='unique_ingredient')
        ]

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    """Модель рецепта с автором, списком ингредиентов и описанием."""
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField("Название", max_length=256)
    image = models.ImageField("Картинка", upload_to='recipes/images/')
    text = models.TextField("Описание")
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты',
        related_name='recipes'
    )
    cooking_time = models.PositiveIntegerField(
        "Время приготовления (в минутах)",
        validators=[MinValueValidator(1)]
    )
    pub_date = models.DateTimeField("Дата публикации", auto_now_add=True)

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class RecipeIngredient(models.Model):
    """Связующая модель между рецептом и ингредиентом с количеством."""
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_amounts'
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='recipe_ingredients')
    amount = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = 'Продукт в рецепте'
        verbose_name_plural = 'Продукты в рецептах'
        constraints = [
            models.UniqueConstraint(fields=['recipe', 'ingredient'], name='unique_recipe_ingredient')
        ]


class Favorite(models.Model):
    """Модель избранных рецептов пользователя."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='favorites',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        constraints = [
            models.UniqueConstraint(fields=['user', 'recipe'], name='unique_favorite')
        ]

    def __str__(self):
        return f"{self.user} добавил {self.recipe} в избранное"


class ShoppingCart(models.Model):
    """Модель списка покупок пользователя."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_carts',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_carts',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзины покупок'
        constraints = [
            models.UniqueConstraint(fields=['user', 'recipe'], name='unique_shopping_cart')
        ]

    def __str__(self):
        return f'{self.user} добавил {self.recipe} в корзину'
