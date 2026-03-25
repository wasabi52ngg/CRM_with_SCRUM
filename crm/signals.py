from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Task
from .scrum_helpers import update_sprint_burndown


@receiver(post_save, sender=Task)
def task_update_burndown(sender, instance: Task, **kwargs):
    if instance.sprint_id:
        update_sprint_burndown(instance.sprint)
