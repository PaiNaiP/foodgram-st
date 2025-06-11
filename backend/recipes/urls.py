from django.urls import path

from foodgram.views import recipe_short_link_redirect

urlpatterns = [
    path(
        '<int:recipe_id>/',
        recipe_short_link_redirect,
        name='recipe-short-link'
    ),
] 