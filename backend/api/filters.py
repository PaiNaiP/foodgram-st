from django_filters import rest_framework as filters
from recipes.models import Recipe


class RecipeFilter(filters.FilterSet):
    """
    Фильтр для рецептов по автору, наличию в избранном
    и в списке покупок.
    """
    is_favorited = filters.BooleanFilter(method='filter_favorited')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('author', 'is_favorited', 'is_in_shopping_cart')

    def filter_favorited(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorited__user=user)
        # Если пользователь анонимный, но запросил избранное - вернуть пустой список
        if value and not user.is_authenticated:
            return queryset.none()
        return queryset

    def filter_shopping_cart(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shopping_cart__user=user)
        # Если пользователь анонимный, но запросил корзину - вернуть пустой список
        if value and not user.is_authenticated:
            return queryset.none()
        return queryset
        
