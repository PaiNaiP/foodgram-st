from django.shortcuts import get_object_or_404, redirect
from recipes.models import Recipe


def recipe_short_link_redirect(request, recipe_id):
    """Осуществляет редирект с короткой ссылки на полную страницу рецепта."""
    get_object_or_404(Recipe, id=recipe_id)
    # Я предполагаю, что фронтенд обрабатывает /recipes/<id>/
    return redirect(f'/recipes/{recipe_id}/', permanent=True) 