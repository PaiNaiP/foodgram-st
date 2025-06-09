from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from recipes.models import Recipe, Ingredient, Favorite, ShoppingCart, User, Subscription, RecipeIngredient
import numpy as np


class HasRecipesFilter(admin.SimpleListFilter):
    title = 'Наличие рецептов'
    parameter_name = 'has_recipes'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Есть рецепты'),
            ('no', 'Нет рецептов'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(recipes__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(recipes__isnull=True)


class HasSubscriptionsFilter(admin.SimpleListFilter):
    title = 'Наличие подписок'
    parameter_name = 'has_subscriptions'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Есть подписки'),
            ('no', 'Нет подписок'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(subscriptions__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(subscriptions__isnull=True)


class HasSubscribersFilter(admin.SimpleListFilter):
    title = 'Наличие подписчиков'
    parameter_name = 'has_subscribers'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Есть подписчики'),
            ('no', 'Нет подписчиков'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(authors__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(authors__isnull=True)


class CookingTimeFilter(admin.SimpleListFilter):
    title = 'Время приготовления'
    parameter_name = 'cooking_time_filter'

    def lookups(self, request, model_admin):
        times = Recipe.objects.values_list('cooking_time', flat=True)
        if not times:
            return []

        q1, q3 = np.percentile(list(times), [33, 67])
        q1, q3 = int(q1), int(q3)

        return (
            ('fast', f'Быстрые (до {q1} мин)'),
            ('medium', f'Средние ({q1}-{q3} мин)'),
            ('slow', f'Долгие (от {q3} мин)'),
        )

    def queryset(self, request, queryset):
        times = Recipe.objects.values_list('cooking_time', flat=True)
        if not times:
            return queryset

        q1, q3 = np.percentile(list(times), [33, 67])
        q1, q3 = int(q1), int(q3)

        if self.value() == 'fast':
            return queryset.filter(cooking_time__lte=q1)
        if self.value() == 'medium':
            return queryset.filter(cooking_time__gt=q1, cooking_time__lte=q3)
        if self.value() == 'slow':
            return queryset.filter(cooking_time__gt=q3)


class IsInRecipeFilter(admin.SimpleListFilter):
    title = 'Наличие в рецептах'
    parameter_name = 'is_in_recipe'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Есть в рецептах'),
            ('no', 'Нет в рецептах'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(recipes__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(recipes__isnull=True)


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
    list_filter = ('is_staff', 'is_superuser', 'is_active', HasRecipesFilter, HasSubscriptionsFilter, HasSubscribersFilter)
    ordering = ('username',)
    readonly_fields = ('get_avatar',)

    @admin.display(description='Аватар')
    def get_avatar(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" height="50" />', obj.avatar.url)
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
        return ", ".join(recipe.ingredients.values_list('name', flat=True))

    @admin.display(description='Картинка')
    def get_image_preview(self, recipe):
        if recipe.image:
            return format_html('<img src="{}" width="100" />', recipe.image.url)
        return "Нет картинки"


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit', 'get_recipe_count')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit', IsInRecipeFilter)

    @admin.display(description='Используется в рецептах')
    def get_recipe_count(self, obj):
        return obj.recipes.count()


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    search_fields = ('recipe__name', 'ingredient__name') 