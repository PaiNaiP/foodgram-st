from django.urls import path

from api.views import recipe_short_link_redirect

urlpatterns = [
    path(
        '<int:recipe_id>/',
        recipe_short_link_redirect,
        name='recipe-short-link'
    ),
]
