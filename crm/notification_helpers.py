"""Создание in-app уведомлений."""

from __future__ import annotations

from django.db.models import Q
from django.urls import reverse

from accounts.models import User
from .models import ClientRequest, Company, CompanyMembership, InAppNotification, Task


def _task_board_link(task: Task) -> str:
    return reverse("crm:kanban_board", args=[task.project_id]) + f"?task={task.id}"


def notify_user(
    user: User | None,
    kind: str,
    title: str,
    body: str = "",
    link_url: str = "",
) -> None:
    if not user or not user.is_authenticated:
        return
    InAppNotification.objects.create(
        user=user,
        kind=kind,
        title=title[:255],
        body=body[:2000] if body else "",
        link_url=link_url[:500] if link_url else "",
    )


def _iter_task_notify_users(task: Task, exclude_user_id: int | None) -> list[User]:
    """Исполнитель и наблюдатели, кроме автора действия."""
    ids: set[int] = set()
    if task.assignee_id and task.assignee_id != exclude_user_id:
        ids.add(task.assignee_id)
    for wid in task.watchers_rel.exclude(user_id=exclude_user_id).values_list("user_id", flat=True):
        ids.add(wid)
    if not ids:
        return []
    return list(User.objects.filter(id__in=ids, is_active=True))


def notify_task_comment(task: Task, author: User, text_preview: str) -> None:
    """Уведомить исполнителя и наблюдателей о новом сообщении в чате задачи."""
    preview = (text_preview or "").strip()[:180]
    if len(preview) < len(text_preview or ""):
        preview += "…"
    link = _task_board_link(task)
    title = f"Чат: {task.title}"
    body = f"{author.username}: {preview}" if preview else f"{author.username} оставил сообщение"

    if task.assignee_id and task.assignee_id != author.id:
        notify_user(
            task.assignee,
            InAppNotification.Kind.TASK_COMMENT,
            title,
            body,
            link_url=link,
        )
    for w in task.watchers_rel.select_related("user").exclude(user_id=author.id):
        if task.assignee_id == w.user_id:
            continue
        notify_user(
            w.user,
            InAppNotification.Kind.TASK_COMMENT,
            title,
            body,
            link_url=link,
        )


def notify_task_assigned(task: Task, assignee: User | None) -> None:
    if not assignee:
        return
    link = _task_board_link(task)
    notify_user(
        assignee,
        InAppNotification.Kind.TASK_ASSIGNED,
        f"Вам назначена задача: {task.title}",
        "",
        link_url=link,
    )


def notify_task_updated(task: Task, editor: User) -> None:
    link = _task_board_link(task)
    title = f"Задача обновлена: {task.title}"
    body = f"Изменил(а): {editor.username}"
    for u in _iter_task_notify_users(task, editor.id):
        notify_user(
            u,
            InAppNotification.Kind.TASK_UPDATED,
            title,
            body,
            link_url=link,
        )


def notify_task_status_changed(task: Task, actor: User, old_status: str, new_status: str) -> None:
    if old_status == new_status:
        return
    status_labels = dict(Task.Status.choices)
    old_l = status_labels.get(old_status, old_status)
    new_l = status_labels.get(new_status, new_status)
    link = _task_board_link(task)
    title = f"Этап задачи: {task.title}"
    body = f"{actor.username}: {old_l} → {new_l}"
    for u in _iter_task_notify_users(task, actor.id):
        notify_user(
            u,
            InAppNotification.Kind.TASK_STATUS_CHANGED,
            title,
            body,
            link_url=link,
        )


def notify_client_message_to_manager(manager: User | None, request_title: str, client_name: str, request_pk: int) -> None:
    if not manager:
        return
    link = reverse("crm:manager_request_detail", args=[request_pk])
    notify_user(
        manager,
        InAppNotification.Kind.CLIENT_MESSAGE,
        f"Сообщение в заявке: {request_title}",
        f"Клиент {client_name}",
        link_url=link,
    )


def notify_request_staff_message(client_request: ClientRequest, author: User, text_preview: str) -> None:
    """Сообщение от менеджера/команды в чате заявки — уведомление клиенту."""
    if not client_request.client_id or client_request.client_id == author.id:
        return
    preview = (text_preview or "").strip()[:180]
    if len(preview) < len(text_preview or ""):
        preview += "…"
    link = reverse("crm:client_request_detail", args=[client_request.pk])
    notify_user(
        client_request.client,
        InAppNotification.Kind.REQUEST_STAFF_MESSAGE,
        f"Сообщение по заявке: {client_request.title}",
        f"{author.username}: {preview}" if preview else author.username,
        link_url=link,
    )


def notify_new_client_request_company_managers(req: ClientRequest) -> None:
    if not req.company_id:
        return
    link = reverse("crm:manager_request_detail", args=[req.pk])
    title = f"Новая заявка: {req.title}"[:255]
    body = (req.contact_email or "")[:200]
    qs = (
        User.objects.filter(
            company_memberships__company_id=req.company_id,
            company_memberships__is_approved=True,
        )
        .filter(Q(company_memberships__is_manager=True) | Q(company_memberships__is_owner=True))
        .distinct()
    )
    for u in qs:
        notify_user(u, InAppNotification.Kind.NEW_CLIENT_REQUEST, title, body, link_url=link)


def notify_employee_join_pending(company: Company, applicant: User) -> None:
    """Владельцам компании: новый сотрудник ждёт подтверждения."""
    link = reverse("crm:company_detail", args=[company.slug])
    title = f"Заявка на вступление: {applicant.username}"
    body = f"{applicant.get_full_name() or applicant.username} ({applicant.email})"
    owners = (
        User.objects.filter(
            company_memberships__company=company,
            company_memberships__is_approved=True,
            company_memberships__is_owner=True,
        )
        .distinct()
    )
    for u in owners:
        if u.id == applicant.id:
            continue
        notify_user(
            u,
            InAppNotification.Kind.EMPLOYEE_JOIN_PENDING,
            title,
            body,
            link_url=link,
        )


def _developer_matches_open_task(user: User, task: Task) -> bool:
    if task.status != Task.Status.TODO or task.assignee_id:
        return False
    dt = user.developer_type
    if not dt or dt == User.DeveloperType.NONE:
        return True
    tt = task.task_type
    if dt == User.DeveloperType.FULLSTACK:
        return tt in (Task.TaskType.FRONTEND, Task.TaskType.BACKEND, Task.TaskType.FULLSTACK)
    return dt == tt


def notify_matching_devs_new_open_task(task: Task) -> None:
    """Свободная задача в TODO без исполнителя — разработчикам компании по типу."""
    if task.status != Task.Status.TODO or task.assignee_id or not task.project.company_id:
        return
    link = _task_board_link(task)
    title = f"Свободная задача: {task.title}"
    body = task.project.name
    company_id = task.project.company_id
    devs = (
        User.objects.filter(
            company_memberships__company_id=company_id,
            company_memberships__is_approved=True,
        )
        .filter(Q(company_memberships__is_developer=True) | Q(company_memberships__is_owner=True))
        .distinct()
    )
    for u in devs:
        if _developer_matches_open_task(u, task):
            notify_user(u, InAppNotification.Kind.NEW_OPEN_TASK, title, body, link_url=link)


def notify_project_devs_sprint_event(project, sprint, event: str) -> None:
    """Уведомить разработчиков компании о старте/завершении спринта."""
    if not project.company_id:
        return
    link = reverse("crm:kanban_board", args=[project.pk])
    if event == "started":
        kind = InAppNotification.Kind.SPRINT_STARTED
        title = f"Спринт активирован: {sprint.name}"
        body = project.name
    elif event == "completed":
        kind = InAppNotification.Kind.SPRINT_COMPLETED
        title = f"Спринт завершён: {sprint.name}"
        body = project.name
    else:
        return
    devs = (
        User.objects.filter(
            company_memberships__company_id=project.company_id,
            company_memberships__is_approved=True,
            company_memberships__is_developer=True,
        )
        .distinct()
    )
    for u in devs:
        notify_user(u, kind, title, body, link_url=link)
