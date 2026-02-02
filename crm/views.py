from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
# Импорты login, validate_password, ValidationError удалены - больше не используются после удаления SignupView

from accounts.mixins import ManagerRequiredMixin, DeveloperRequiredMixin, LoginRequiredMixin, ClientRequiredMixin
from accounts.models import User
from .models import ClientRequest, Project, Task, RequestCheckpoint, TaskCheckpoint
from .models import Message


class PublicRequestView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "crm/public_request.html")

    def post(self, request: HttpRequest) -> HttpResponse:
        data = request.POST
        ClientRequest.objects.create(
            project_type=data.get("project_type"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            contact_email=data.get("contact_email", ""),
            contact_telegram=data.get("contact_telegram", ""),
        )
        return render(request, "crm/public_request_success.html")


class ManagerRequestListView(ManagerRequiredMixin, ListView):
    model = ClientRequest
    template_name = "crm/manager/request_list.html"
    paginate_by = 20
    ordering = ["-created_at"]


class ManagerRequestDetailView(ManagerRequiredMixin, DetailView):
    model = ClientRequest
    template_name = "crm/manager/request_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Все чекпоинты заявки в удобном для таймлайна виде
        ctx["checkpoints"] = list(
            self.object.checkpoints.all().values(
                "id", "title", "comment", "is_done", "order", "created_at", "updated_at"
            )
        )
        return ctx

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        client_request = self.get_object()
        action = request.POST.get("action")
        if action == "to_discuss":
            client_request.status = ClientRequest.Status.DISCUSS
            client_request.manager = request.user
            client_request.save()
        elif action == "to_work":
            client_request.status = ClientRequest.Status.IN_PROGRESS
            client_request.manager = request.user
            client_request.save()
            Project.objects.get_or_create(
                client_request=client_request,
                defaults={"name": client_request.title, "description": client_request.description},
            )
        return redirect("crm:manager_request_detail", pk=client_request.pk)


class ManagerProjectDetailView(ManagerRequiredMixin, DetailView):
    model = Project
    template_name = "crm/manager/project_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Список разработчиков для назначения исполнителя прямо при создании задачи
        ctx["developers"] = (
            User.objects.filter(role=User.Role.DEVELOPER, is_active=True)
            .order_by("username")
            .only("id", "username", "first_name", "last_name", "developer_type")
        )
        return ctx

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        project = self.get_object()
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        task_type = request.POST.get("task_type")
        assignee_id = request.POST.get("assignee") or ""
        due_date = request.POST.get("due_date") or None
        story_points_raw = request.POST.get("story_points") or "0"

        assignee = None
        if assignee_id:
            assignee = get_object_or_404(User, pk=assignee_id, role=User.Role.DEVELOPER)

        try:
            story_points = int(story_points_raw)
        except Exception:
            story_points = 0
        story_points = max(0, min(100, story_points))

        if title and task_type in dict(Task.TaskType.choices):
            Task.objects.create(
                project=project,
                title=title,
                description=description,
                task_type=task_type,
                created_by=request.user,
                assignee=assignee,
                due_date=due_date,
                story_points=story_points,
            )
        return redirect("crm:manager_project_detail", pk=project.pk)


class DeveloperOpenTasksView(DeveloperRequiredMixin, ListView):
    model = Task
    template_name = "crm/dev/open_tasks.html"

    def get_queryset(self):
        user: User = self.request.user
        dev_types = []
        if user.developer_type == User.DeveloperType.FULLSTACK:
            dev_types = [User.DeveloperType.FRONTEND, User.DeveloperType.BACKEND, User.DeveloperType.FULLSTACK]
        else:
            dev_types = [user.developer_type]
        return (
            Task.objects.filter(status=Task.Status.TODO, assignee__isnull=True, task_type__in=dev_types)
            .select_related("project")
            .order_by("project__created_at")
        )


class DeveloperTakeTaskView(DeveloperRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        task = get_object_or_404(Task, pk=pk, assignee__isnull=True, status=Task.Status.TODO)
        # Ограничение: один исполнитель — одна активная задача
        has_active = Task.objects.filter(assignee=request.user).exclude(status=Task.Status.DONE).exists()
        if not has_active:
            task.assignee = request.user
            task.status = Task.Status.IN_PROGRESS
            task.save()
        return redirect("crm:dev_open_tasks")


class DashboardRedirectView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        user: User = request.user
        if user.is_manager():
            return redirect("crm:manager_request_list")
        if user.is_developer():
            return redirect("crm:dev_open_tasks")
        return redirect("crm:client_requests")


class LandingView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        return render(request, "crm/landing.html")


class ClientRequestListView(ClientRequiredMixin, ListView):
    model = ClientRequest
    template_name = "crm/client/requests.html"

    def get_queryset(self):
        return ClientRequest.objects.filter(client=self.request.user).order_by("-created_at")


class ClientRequestDetailView(ClientRequiredMixin, DetailView):
    model = ClientRequest
    template_name = "crm/client/request_detail.html"

    def get_queryset(self):
        return ClientRequest.objects.filter(client=self.request.user)

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        obj = self.get_object()
        text = request.POST.get("text", "").strip()
        if text:
            Message.objects.create(request=obj, author=request.user, text=text)
        return redirect("crm:client_request_detail", pk=obj.pk)


# SignupView удален - теперь используется accounts.views.RegisterUser


class KanbanBoardView(ManagerRequiredMixin, DetailView):
    model = Project
    template_name = "crm/kanban.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project: Project = self.object
        ctx["todo"] = project.tasks.filter(status=Task.Status.TODO).order_by("order", "created_at")
        ctx["in_progress"] = project.tasks.filter(status=Task.Status.IN_PROGRESS).order_by("order", "created_at")
        ctx["review"] = project.tasks.filter(status=Task.Status.REVIEW).order_by("order", "created_at")
        ctx["done"] = project.tasks.filter(status=Task.Status.DONE).order_by("order", "created_at")
        return ctx


@method_decorator(require_POST, name='dispatch')
class KanbanMoveApiView(ManagerRequiredMixin, View):
    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            import json
            payload = json.loads(request.body.decode("utf-8"))
            task_id = int(payload.get("id"))
            new_status = payload.get("status")
        except Exception:
            return JsonResponse({"ok": False, "error": "invalid_payload"}, status=400)

        if new_status not in dict(Task.Status.choices):
            return JsonResponse({"ok": False, "error": "bad_status"}, status=400)

        task = get_object_or_404(Task, pk=task_id)
        task.status = new_status
        # Простое переупорядочивание: помещаем в конец колонки
        last_order = (
            Task.objects.filter(project=task.project, status=new_status)
            .exclude(pk=task.pk)
            .order_by("-order")
            .values_list("order", flat=True)
            .first()
        ) or 0
        task.order = last_order + 1
        task.save(update_fields=["status", "order", "updated_at"])
        return JsonResponse({"ok": True})


@method_decorator(require_POST, name="dispatch")
class RequestCheckpointApiView(ManagerRequiredMixin, View):
    """
    Простое JSON‑API для управления чекпоинтами заявки:
    - action=create  (title, comment, is_done?)
    - action=update  (id, title?, comment?, is_done?)
    - action=delete  (id)
    - action=reorder (ids: [id1, id2, ...] в новом порядке)
    """

    def post(self, request: HttpRequest, pk: int) -> JsonResponse:
        import json

        client_request = get_object_or_404(ClientRequest, pk=pk)
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

        action = payload.get("action")

        if action == "create":
            title = (payload.get("title") or "").strip()
            comment = (payload.get("comment") or "").strip()
            if not title:
                return JsonResponse({"ok": False, "error": "title_required"}, status=400)
            last_order = (
                client_request.checkpoints.order_by("-order")
                .values_list("order", flat=True)
                .first()
                or 0
            )
            cp = RequestCheckpoint.objects.create(
                request=client_request,
                title=title,
                comment=comment,
                order=last_order + 1,
            )
            return JsonResponse(
                {
                    "ok": True,
                    "checkpoint": {
                        "id": cp.id,
                        "title": cp.title,
                        "comment": cp.comment,
                        "is_done": cp.is_done,
                        "order": cp.order,
                    },
                }
            )

        if action == "update":
            cp_id = payload.get("id")
            cp = get_object_or_404(RequestCheckpoint, pk=cp_id, request=client_request)
            title = payload.get("title")
            comment = payload.get("comment")
            is_done = payload.get("is_done")
            changed = False
            if title is not None:
                cp.title = (title or "").strip()
                changed = True
            if comment is not None:
                cp.comment = (comment or "").strip()
                changed = True
            if is_done is not None:
                cp.is_done = bool(is_done)
                changed = True
            if changed:
                cp.save()
            return JsonResponse({"ok": True})

        if action == "delete":
            cp_id = payload.get("id")
            cp = get_object_or_404(RequestCheckpoint, pk=cp_id, request=client_request)
            cp.delete()
            return JsonResponse({"ok": True})

        if action == "reorder":
            ids = payload.get("ids") or []
            if not isinstance(ids, list):
                return JsonResponse({"ok": False, "error": "ids_list_required"}, status=400)
            order_map = {cp_id: idx for idx, cp_id in enumerate(ids, start=1)}
            for cp in client_request.checkpoints.all():
                if cp.id in order_map:
                    cp.order = order_map[cp.id]
                    cp.save(update_fields=["order"])
            return JsonResponse({"ok": True})

        return JsonResponse({"ok": False, "error": "bad_action"}, status=400)


@method_decorator(require_POST, name="dispatch")
class TaskPanelApiView(ManagerRequiredMixin, View):
    """
    JSON‑API для боковой панели задачи на канбане.
    - action=detail: данные задачи + чекпоинты + чат (последние 50)
    - action=checkpoint_create/update/delete/reorder
    - action=chat_add
    """

    def post(self, request: HttpRequest, pk: int) -> JsonResponse:
        import json

        task = get_object_or_404(Task.objects.select_related("assignee", "created_by", "project"), pk=pk)
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

        action = payload.get("action") or "detail"

        if action == "detail":
            checkpoints = list(task.checkpoints.all().values("id", "title", "comment", "is_done", "order"))
            chat = list(
                task.comments.select_related("author")
                .order_by("-created_at")[:50]
                .values("id", "text", "created_at", "author__username")
            )[::-1]
            return JsonResponse(
                {
                    "ok": True,
                    "task": {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "status": task.status,
                        "status_label": task.get_status_display(),
                        "task_type": task.task_type,
                        "task_type_label": task.get_task_type_display(),
                        "story_points": task.story_points,
                        "assignee": getattr(task.assignee, "username", None),
                        "created_by": getattr(task.created_by, "username", None),
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "project_id": task.project_id,
                    },
                    "checkpoints": checkpoints,
                    "chat": chat,
                }
            )

        # ---- Checkpoints ----
        if action == "checkpoint_create":
            title = (payload.get("title") or "").strip()
            comment = (payload.get("comment") or "").strip()
            if not title:
                return JsonResponse({"ok": False, "error": "title_required"}, status=400)
            last_order = task.checkpoints.order_by("-order").values_list("order", flat=True).first() or 0
            cp = TaskCheckpoint.objects.create(task=task, title=title, comment=comment, order=last_order + 1)
            return JsonResponse(
                {
                    "ok": True,
                    "checkpoint": {
                        "id": cp.id,
                        "title": cp.title,
                        "comment": cp.comment,
                        "is_done": cp.is_done,
                        "order": cp.order,
                    },
                }
            )

        if action == "checkpoint_update":
            cp_id = payload.get("id")
            cp = get_object_or_404(TaskCheckpoint, pk=cp_id, task=task)
            title = payload.get("title")
            comment = payload.get("comment")
            is_done = payload.get("is_done")
            changed = False
            if title is not None:
                cp.title = (title or "").strip()
                changed = True
            if comment is not None:
                cp.comment = (comment or "").strip()
                changed = True
            if is_done is not None:
                cp.is_done = bool(is_done)
                changed = True
            if changed:
                cp.save()
            return JsonResponse({"ok": True})

        if action == "checkpoint_delete":
            cp_id = payload.get("id")
            cp = get_object_or_404(TaskCheckpoint, pk=cp_id, task=task)
            cp.delete()
            return JsonResponse({"ok": True})

        if action == "checkpoint_reorder":
            ids = payload.get("ids") or []
            if not isinstance(ids, list):
                return JsonResponse({"ok": False, "error": "ids_list_required"}, status=400)
            order_map = {cp_id: idx for idx, cp_id in enumerate(ids, start=1)}
            for cp in task.checkpoints.all():
                if cp.id in order_map:
                    cp.order = order_map[cp.id]
                    cp.save(update_fields=["order"])
            return JsonResponse({"ok": True})

        # ---- Chat ----
        if action == "chat_add":
            text = (payload.get("text") or "").strip()
            if not text:
                return JsonResponse({"ok": False, "error": "text_required"}, status=400)
            comment = task.comments.create(author=request.user, text=text)
            return JsonResponse(
                {
                    "ok": True,
                    "message": {
                        "id": comment.id,
                        "text": comment.text,
                        "created_at": comment.created_at.isoformat(),
                        "author__username": request.user.username,
                    },
                }
            )

        return JsonResponse({"ok": False, "error": "bad_action"}, status=400)


# Create your views here.
