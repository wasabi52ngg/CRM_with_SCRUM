from __future__ import annotations

from django.db.models import Sum
from django.utils import timezone

from .models import Sprint, SprintBurndownSnapshot, Task


def remaining_story_points_in_sprint(sprint: Sprint) -> int:
    total = (
        Task.objects.filter(sprint=sprint)
        .exclude(status=Task.Status.DONE)
        .aggregate(s=Sum("story_points"))["s"]
    )
    return int(total or 0)


def update_sprint_burndown(sprint: Sprint) -> None:
    if not sprint.pk:
        return
    today = timezone.now().date()
    rem = remaining_story_points_in_sprint(sprint)
    SprintBurndownSnapshot.objects.update_or_create(
        sprint=sprint,
        day=today,
        defaults={"remaining_points": rem},
    )


def velocity_for_completed_sprints(project_id: int, limit: int = 8) -> list[dict]:
    """Сумма story points по задачам в статусе Done для завершённых спринтов."""
    sprints = (
        Sprint.objects.filter(project_id=project_id, completed_at__isnull=False)
        .order_by("-completed_at")[:limit]
    )
    out = []
    for sp in reversed(list(sprints)):
        done_sp = (
            Task.objects.filter(sprint=sp, status=Task.Status.DONE).aggregate(s=Sum("story_points"))["s"]
            or 0
        )
        out.append(
            {
                "sprint_id": sp.id,
                "name": sp.name,
                "completed_at": sp.completed_at if sp.completed_at else None,
                "velocity": int(done_sp),
            }
        )
    return out
