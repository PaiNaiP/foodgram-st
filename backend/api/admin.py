from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import User, Subscription
from recipes.models import Recipe, Ingredient, Favorite, ShoppingCart


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    search_fields = ('user__username', 'author__username')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_author', 'favorites_count')
    search_fields = ('name', 'author__username')

    def display_author(self, obj):
        return (
            f'{obj.author.last_name} {obj.author.first_name} '
            f'(username:{obj.author.username}, email: {obj.author.email})'
        )
    display_author.short_description = 'Автор'

    def favorites_count(self, obj):
        return obj.favorited_by.count()
    favorites_count.short_description = 'В избранном'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
