from django.shortcuts import redirect
from django.http import Http404
from rest_framework.decorators import api_view

from recipes.models import Recipe


@api_view(['GET'])
def recipe_short_link_redirect(request, recipe_id):
    """Осуществляет редирект с короткой ссылки на полную страницу рецепта."""
    if not Recipe.objects.filter(id=recipe_id).exists():
        raise Http404()
    return redirect(f'/recipes/{recipe_id}/', permanent=True)
