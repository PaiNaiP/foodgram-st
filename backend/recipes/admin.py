from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from recipes.models import Recipe, Ingredient, Favorite, ShoppingCart, User, Subscription, RecipeIngredient
import numpy as np


class ExistenceFilter(admin.SimpleListFilter):
    """Базовый класс для фильтров по наличию чего-либо."""
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(**{f'{self.lookup_field}__isnull': False}).distinct()
        if self.value() == 'no':
            return queryset.filter(**{f'{self.lookup_field}__isnull': True})
        return queryset


class HasRecipesFilter(ExistenceFilter):
    title = 'Наличие рецептов'
    parameter_name = 'has_recipes'
    lookup_field = 'recipes'
    LOOKUPS = (
        ('yes', 'Есть рецепты'),
        ('no', 'Нет рецептов'),
    )

    def lookups(self, request, model_admin):
        return self.LOOKUPS


class HasSubscriptionsFilter(ExistenceFilter):
    title = 'Наличие подписок'
    parameter_name = 'has_subscriptions'
    lookup_field = 'subscriptions'
    LOOKUPS = (
        ('yes', 'Есть подписки'),
        ('no', 'Нет подписок'),
    )

    def lookups(self, request, model_admin):
        return self.LOOKUPS


class HasSubscribersFilter(ExistenceFilter):
    title = 'Наличие подписчиков'
    parameter_name = 'has_subscribers'
    lookup_field = 'authors'
    LOOKUPS = (
        ('yes', 'Есть подписчики'),
        ('no', 'Нет подписчиков'),
    )

    def lookups(self, request, model_admin):
        return self.LOOKUPS


class CookingTimeFilter(admin.SimpleListFilter):
    title = 'Время приготовления'
    parameter_name = 'cooking_time_filter'

    def _get_thresholds(self):
        if hasattr(self, '_q1') and hasattr(self, '_q3'):
            return self._q1, self._q3

        if Recipe.objects.values('cooking_time').distinct().count() < 3:
            self._q1, self._q3 = None, None
            return self._q1, self._q3

        times = list(Recipe.objects.values_list('cooking_time', flat=True))
        if not times:
            self._q1, self._q3 = None, None
            return self._q1, self._q3

        quantiles = np.percentile(times, [33, 67])
        self._q1 = int(quantiles[0])
        self._q3 = int(quantiles[1])
        return self._q1, self._q3

    def lookups(self, request, model_admin):
        q1, q3 = self._get_thresholds()

        if q1 is None or q3 is None:
            return []

        return (
            ('fast', f'Быстрые (до {q1} мин)'),
            ('medium', f'Средние ({q1}-{q3} мин)'),
            ('slow', f'Долгие (от {q3} мин)'),
        )

    def queryset(self, request, queryset):
        q1, q3 = self._get_thresholds()

        if self.value() is None or q1 is None or q3 is None:
            return queryset

        if self.value() == 'fast':
            return queryset.filter(cooking_time__lte=q1)
        if self.value() == 'medium':
            return queryset.filter(cooking_time__gt=q1, cooking_time__lte=q3)
        if self.value() == 'slow':
            return queryset.filter(cooking_time__gt=q3)
        return queryset


class IsInRecipeFilter(ExistenceFilter):
    title = 'Наличие в рецептах'
    parameter_name = 'is_in_recipe'
    lookup_field = 'recipes'
    LOOKUPS = (
        ('yes', 'Есть в рецептах'),
        ('no', 'Нет в рецептах'),
    )

    def lookups(self, request, model_admin):
        return self.LOOKUPS


@admin.register(User)
class FoodgramUserAdmin(UserAdmin):
    list_display = (
        'id',
        'username',
        'get_full_name',
        'email',
        'get_avatar',
        'get_recipe_count',
        'get_subscription_count',
        'get_subscriber_count',
    )
    search_fields = ('username', 'email')
    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        HasRecipesFilter,
        HasSubscriptionsFilter,
        HasSubscribersFilter,
    )
    ordering = ('username',)
    readonly_fields = ('get_avatar',)

    @admin.display(description='Аватар')
    def get_avatar(self, obj):
        if obj.avatar:
            return mark_safe(f'<img src="{obj.avatar.url}" width="50" height="50" />')
        return "Нет аватара"

    @admin.display(description='Рецептов')
    def get_recipe_count(self, obj):
        return obj.recipes.count()

    @admin.display(description='Подписок')
    def get_subscription_count(self, obj):
        return obj.subscriptions.count()

    @admin.display(description='Подписчиков')
    def get_subscriber_count(self, obj):
        return obj.authors.count()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    search_fields = ('user__username', 'author__username')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'cooking_time',
        'display_author',
        'favorites_count',
        'get_ingredients_list',
        'get_image_preview',
    )
    list_filter = ('author', 'name', 'ingredients', CookingTimeFilter)
    search_fields = ('name', 'author__username', 'ingredients__name')
    readonly_fields = ('get_image_preview',)

    @admin.display(description='Автор')
    def display_author(self, recipe):
        return recipe.author.get_full_name()

    @admin.display(description='В избранном')
    def favorites_count(self, recipe):
        return recipe.favorited.count()

    @admin.display(description='Продукты')
    def get_ingredients_list(self, recipe):
        ingredients = recipe.ingredient_amounts.select_related('ingredient')
        ingredients_list = [
            f'{item.ingredient.name} ({item.ingredient.measurement_unit})'
            f' - {item.amount}' for item in ingredients
        ]
        return mark_safe('<br>'.join(ingredients_list))

    @admin.display(description='Картинка')
    def get_image_preview(self, recipe):
        if recipe.image:
            return mark_safe(f'<img src="{recipe.image.url}" width="100" />')
        return "Нет картинки"


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit', 'get_recipe_count')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit', IsInRecipeFilter)

    @admin.display(description='В рецептах')
    def get_recipe_count(self, obj):
        return obj.recipes.count()


@admin.register(Favorite, ShoppingCart)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name')
