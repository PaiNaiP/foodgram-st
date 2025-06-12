from django.urls import path

from recipes.views import recipe_short_link_redirect

app_name = 'recipes'


urlpatterns = [
    path(
        'r/<int:recipe_id>/',
        recipe_short_link_redirect,
        name='recipe-short-link'
    ),
]
