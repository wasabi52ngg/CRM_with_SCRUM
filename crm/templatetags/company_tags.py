from django import template
from django.db.models import Q

register = template.Library()


@register.filter
def is_manager_in_company(user):
    """Проверяет, является ли пользователь менеджером в какой-либо компании"""
    if not user.is_authenticated:
        return False
    return user.company_memberships.filter(
        is_approved=True
    ).filter(
        Q(is_manager=True) | Q(is_owner=True)
    ).exists()


@register.filter
def is_developer_in_company(user):
    """Проверяет, является ли пользователь разработчиком в какой-либо компании"""
    if not user.is_authenticated:
        return False
    return user.company_memberships.filter(
        is_approved=True
    ).filter(
        Q(is_developer=True) | Q(is_owner=True)
    ).exists()
