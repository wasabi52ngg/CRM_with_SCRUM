"""Аватар пользователя: фото или буква на синем фоне."""

from django import template

register = template.Library()


@register.inclusion_tag("crm/snippets/user_avatar.html")
def user_avatar(user, size=40, css_class=""):
    """Рендер аватара для шаблонов (сообщения, списки)."""
    if not user:
        return {
            "photo_url": "",
            "initial": "?",
            "size": int(size),
            "font_size": max(int(size) // 2, 11),
            "css_class": css_class,
            "has_photo": False,
        }
    initial = (getattr(user, "first_name", None) or user.username or "?")[0].upper()
    has_photo = bool(getattr(user, "photo", None) and user.photo.name)
    photo_url = user.photo.url if has_photo else ""
    return {
        "photo_url": photo_url,
        "initial": initial,
        "size": int(size),
        "font_size": max(int(size) // 2, 11),
        "css_class": css_class,
        "has_photo": has_photo,
    }
