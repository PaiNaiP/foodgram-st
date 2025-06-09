from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    IngredientViewSet,
    RecipeViewSet,
    UserViewSet,
    SubscriptionViewSet,
    RecipeShortLinkRedirectView,
)

router = DefaultRouter()
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipes')
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path(
        'users/subscriptions/',
        SubscriptionViewSet.as_view({'get': 'list'}),
        name='subscriptions-list'
    ),
    path(
        's/<int:recipe_id>/',
        RecipeShortLinkRedirectView.as_view(),
        name='recipe-short-link'
    ),
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
