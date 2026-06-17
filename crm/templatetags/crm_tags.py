from django import template
from django.contrib.auth.models import AbstractBaseUser

from crm.models import Task
from crm.chat_attachments import is_chat_image

register = template.Library()


@register.filter
def user_display(user: AbstractBaseUser | None) -> str:
    """
    Имя и фамилия, при наличии, и ник в скобках; иначе только логин.
    """
    if not user:
        return ""
    fn = (getattr(user, "first_name", None) or "").strip()
    ln = (getattr(user, "last_name", None) or "").strip()
    full = f"{fn} {ln}".strip()
    un = (getattr(user, "username", None) or "").strip()
    if full and un:
        return f"{full} ({un})"
    if full:
        return full
    return un or "—"


@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None
    if key is None:
        return None
    val = dictionary.get(key)
    if val is None and key is not None:
        val = dictionary.get(str(key))
    return val


@register.filter
def chat_image(file_field) -> bool:
    return is_chat_image(file_field)


@register.filter
def file_basename(file_field) -> str:
    if not file_field:
        return ""
    return file_field.name.rsplit("/", 1)[-1]


@register.filter
def subtask_label(task):
    if not task or not getattr(task, "pk", None):
        return ""
    ch = list(task.children.all()[:50])
    if not ch:
        return ""
    done = sum(1 for c in ch if c.status == Task.Status.DONE)
    return f"{done}/{len(ch)}"
