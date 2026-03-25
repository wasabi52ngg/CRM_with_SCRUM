from django import template

from crm.models import Task

register = template.Library()


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
def subtask_label(task):
    if not task or not getattr(task, "pk", None):
        return ""
    ch = list(task.children.all()[:50])
    if not ch:
        return ""
    done = sum(1 for c in ch if c.status == Task.Status.DONE)
    return f"{done}/{len(ch)}"
