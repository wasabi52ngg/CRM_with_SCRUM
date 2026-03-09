from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import models
# Импорты login, validate_password, ValidationError удалены - больше не используются после удаления SignupView

from accounts.mixins import ManagerRequiredMixin, DeveloperRequiredMixin, LoginRequiredMixin, ClientRequiredMixin
from accounts.models import User
from .models import (
    Company,
    CompanyMembership,
    ClientRequest,
    Project,
    Task,
    Sprint,
    RequestCheckpoint,
    RequestCheckpointEdge,
    TaskCheckpoint,
    KanbanColumnConfig,
    KanbanFilterPreset,
    TaskActivity,
    Message,
)


def _get_user_company_ids(user: User) -> list[int]:
    """
    Вспомогательная функция: возвращает список id компаний, в которых состоит пользователь.
    Используется для фильтрации объектов по компании (мульти‑тенантность).
    Учитывает только подтверждённые участия (is_approved=True).
    """
    if not user.is_authenticated:
        return []
    return list(user.company_memberships.filter(is_approved=True).values_list("company_id", flat=True))


def _is_user_manager_in_company(user: User, company_id: int | None = None) -> bool:
    """
    Проверяет, является ли пользователь менеджером в компании.
    Если company_id не указан, проверяет во всех компаниях пользователя.
    """
    if not user.is_authenticated:
        return False
    qs = user.company_memberships.filter(is_approved=True)
    if company_id:
        qs = qs.filter(company_id=company_id)
    return qs.filter(is_manager=True).exists() or qs.filter(is_owner=True).exists()


def _is_user_developer_in_company(user: User, company_id: int | None = None) -> bool:
    """
    Проверяет, является ли пользователь разработчиком в компании.
    Если company_id не указан, проверяет во всех компаниях пользователя.
    """
    if not user.is_authenticated:
        return False
    qs = user.company_memberships.filter(is_approved=True)
    if company_id:
        qs = qs.filter(company_id=company_id)
    return qs.filter(is_developer=True).exists() or qs.filter(is_owner=True).exists()


def _log_task_activity(
    *,
    task: Task,
    user: User | None,
    action: str,
    field: str = "",
    old_value: str | None = "",
    new_value: str | None = "",
) -> None:
    """
    Создаёт запись в истории изменений задачи.
    """
    TaskActivity.objects.create(
        task=task,
        author=user if user and user.is_authenticated else None,
        action=action,
        field=field,
        old_value=str(old_value or ""),
        new_value=str(new_value or ""),
    )


class PublicRequestView(View):
    """
    Публичная форма оставления заявки для конкретной компании.
    Доступ по ссылке вида /request/<company_slug>/ или по токену.
    """

    def get_company(self, *, company_slug: str | None = None, token: str | None = None) -> Company:
        if company_slug:
            return get_object_or_404(Company, slug=company_slug)
        if token:
            return get_object_or_404(Company, public_token=token)
        # Для совместимости можно показывать первую компанию, но в дипломе
        # этот случай лучше явно не использовать.
        return get_object_or_404(Company.objects.order_by("id"))

    def get(self, request: HttpRequest, company_slug: str | None = None, token: str | None = None) -> HttpResponse:
        company = self.get_company(company_slug=company_slug, token=token)
        if not request.user.is_authenticated and request.GET.get("skip_register"):
            request.session["register_prompt_dismissed"] = True
            request.session.modified = True
            if company_slug:
                base_url = reverse("crm:public_request_by_slug", args=[company.slug])
            else:
                token_val = request.resolver_match.kwargs.get("token") or company.public_token or ""
                base_url = reverse("crm:public_request_by_token", args=[token_val])
            return redirect(base_url)
        show_register_prompt = (
            not request.user.is_authenticated
            and not request.session.get("register_prompt_dismissed")
        )
        ctx = {"company": company, "show_register_prompt": show_register_prompt}
        return render(request, "crm/public_request.html", ctx)

    def post(self, request: HttpRequest, company_slug: str | None = None, token: str | None = None) -> HttpResponse:
        company = self.get_company(company_slug=company_slug, token=token)
        data = request.POST
        client = request.user if request.user.is_authenticated else None
        req = ClientRequest.objects.create(
            company=company,
            project_type=data.get("project_type"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            contact_email=data.get("contact_email", ""),
            contact_telegram=data.get("contact_telegram", ""),
            client=client,
        )
        # Для анонимных: сохраняем id заявки в сессии, чтобы показать её в «Мои заявки» после регистрации
        if not request.user.is_authenticated:
            ids = list(request.session.get("anonymous_request_ids", []))
            if req.pk not in ids:
                ids.append(req.pk)
            request.session["anonymous_request_ids"] = ids
            request.session.modified = True
        ctx = {"company": company, "request_obj": req}
        return render(request, "crm/public_request_success.html", ctx)


class PublicRequestChooseCompanyView(View):
    """
    Входная точка для гостей: выбрать компанию и перейти на публичную форму заявки.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        companies = Company.objects.all().order_by("name")
        return render(request, "crm/public_request_choose_company.html", {"companies": companies})


class ManagerRequestListView(LoginRequiredMixin, ListView):
    model = ClientRequest
    template_name = "crm/manager/request_list.html"
    paginate_by = 20
    ordering = ["-created_at"]

    def dispatch(self, request, *args, **kwargs):
        # Проверяем, что пользователь является менеджером или владельцем в какой-либо компании
        if not _is_user_manager_in_company(request.user):
            return redirect("crm:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        company_ids = _get_user_company_ids(self.request.user)
        qs = super().get_queryset()
        if company_ids:
            qs = qs.filter(company_id__in=company_ids)
        return qs


class ManagerRequestDetailView(LoginRequiredMixin, DetailView):
    model = ClientRequest
    template_name = "crm/manager/request_detail.html"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        # Проверяем доступ: менеджер/владелец в компании заявки ИЛИ менеджер, который взял эту заявку
        if not (_is_user_manager_in_company(request.user, obj.company_id) or obj.manager == request.user):
            return redirect("crm:manager_request_list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        client_request = self.object
        # Узлы диаграммы (чекпоинты) с позициями и рёбра (связи)
        ctx["checkpoints"] = list(
            client_request.checkpoints.all().values(
                "id", "title", "comment", "is_done", "order", "x", "y", "created_at", "updated_at"
            )
        )
        ctx["checkpoint_edges"] = list(
            client_request.checkpoint_edges.select_related("source", "target").values("id", "source_id", "target_id")
        )
        # Проверяем, может ли текущий менеджер взять заявку
        ctx["can_take"] = (
            _is_user_manager_in_company(self.request.user, client_request.company_id) and
            client_request.manager is None and
            client_request.status in (ClientRequest.Status.NEW, ClientRequest.Status.DISCUSS)
        )
        ctx["is_responsible"] = client_request.manager == self.request.user
        ctx["is_owner"] = self.request.user.company_memberships.filter(
            company_id=client_request.company_id,
            is_approved=True,
            is_owner=True,
        ).exists()
        ctx["can_chat"] = ctx["is_responsible"] or ctx["is_owner"]
        return ctx

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        client_request = self.get_object()
        action = request.POST.get("action")

        # ---- Chat (manager -> client) ----
        if action == "chat":
            text = request.POST.get("text", "").strip()
            can_chat = (
                client_request.manager == request.user
                or request.user.company_memberships.filter(
                    company_id=client_request.company_id,
                    is_approved=True,
                    is_owner=True,
                ).exists()
            )
            if text and can_chat:
                Message.objects.create(request=client_request, author=request.user, text=text)
                # Если заявка ещё "Новая", то переводим в "В обсуждении" при начале диалога
                if client_request.status == ClientRequest.Status.NEW:
                    client_request.status = ClientRequest.Status.DISCUSS
                    client_request.save(update_fields=["status", "updated_at"])
            return redirect("crm:manager_request_detail", pk=client_request.pk)
        
        if action == "take":
            # Менеджер берет заявку в работу
            if _is_user_manager_in_company(request.user, client_request.company_id) and client_request.manager is None:
                client_request.manager = request.user
                client_request.status = ClientRequest.Status.DISCUSS
                client_request.save()
        elif action == "to_discuss":
            if client_request.manager == request.user:
                client_request.status = ClientRequest.Status.DISCUSS
                client_request.save()
        elif action == "to_work":
            if client_request.manager == request.user:
                client_request.status = ClientRequest.Status.IN_PROGRESS
                client_request.save()
                Project.objects.get_or_create(
                    client_request=client_request,
                    defaults={
                        "name": client_request.title,
                        "description": client_request.description,
                        "company": client_request.company,
                    },
                )
        return redirect("crm:manager_request_detail", pk=client_request.pk)


class ManagerProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "crm/manager/project_detail.html"

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        # Доступ имеют: владелец компании, менеджер который взял заявку, или разработчик с задачами в проекте
        has_access = (
            _is_user_manager_in_company(request.user, obj.company_id) or
            (obj.client_request and obj.client_request.manager == request.user) or
            _is_user_developer_in_company(request.user, obj.company_id)
        )
        if not has_access:
            return redirect("crm:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        company_ids = _get_user_company_ids(self.request.user)
        qs = super().get_queryset()
        if company_ids:
            qs = qs.filter(company_id__in=company_ids)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.object
        # Список разработчиков компании для назначения исполнителя
        company_ids = _get_user_company_ids(self.request.user)
        developer_user_ids = CompanyMembership.objects.filter(
            company_id__in=company_ids,
            is_approved=True,
            is_developer=True
        ).values_list("user_id", flat=True)
        
        ctx["developers"] = (
            User.objects.filter(id__in=developer_user_ids, is_active=True)
            .order_by("username")
            .only("id", "username", "first_name", "last_name", "developer_type")
        )
        # Статистика задач проекта для виджета прогресса
        tasks_qs = project.tasks.all()
        ctx["task_stats"] = {
            "total": tasks_qs.count(),
            "todo": tasks_qs.filter(status=Task.Status.TODO).count(),
            "in_progress": tasks_qs.filter(status=Task.Status.IN_PROGRESS).count(),
            "review": tasks_qs.filter(status=Task.Status.REVIEW).count(),
            "done": tasks_qs.filter(status=Task.Status.DONE).count(),
        }
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
            # Исполнитель должен быть в списке разработчиков компании проекта (как в форме)
            developer_user_ids = CompanyMembership.objects.filter(
                company=project.company,
                is_approved=True,
                is_developer=True,
            ).values_list("user_id", flat=True)
            if int(assignee_id) in developer_user_ids:
                assignee = get_object_or_404(User, pk=assignee_id)

        try:
            story_points = int(story_points_raw)
        except Exception:
            story_points = 0
        story_points = max(0, min(100, story_points))

        if title and task_type in dict(Task.TaskType.choices):
            task = Task.objects.create(
                project=project,
                title=title,
                description=description,
                task_type=task_type,
                created_by=request.user,
                assignee=assignee,
                due_date=due_date,
                story_points=story_points,
            )
            _log_task_activity(
                task=task,
                user=request.user,
                action="create",
                field="task",
                old_value="",
                new_value=task.title,
            )
        return redirect("crm:manager_project_detail", pk=project.pk)


class DeveloperOpenTasksView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "crm/dev/open_tasks.html"

    def dispatch(self, request, *args, **kwargs):
        # Проверяем, что пользователь является разработчиком в какой-либо компании
        if not _is_user_developer_in_company(request.user):
            return redirect("crm:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user: User = self.request.user
        company_ids = _get_user_company_ids(user)
        qs = (
            Task.objects.filter(
                status=Task.Status.TODO,
                assignee__isnull=True,
            )
            .select_related("project")
        )
        if company_ids:
            qs = qs.filter(project__company_id__in=company_ids)
        # Фильтр по типу задачи: если у разработчика задан тип (не NONE), показываем подходящие задачи
        if user.developer_type and user.developer_type != User.DeveloperType.NONE:
            if user.developer_type == User.DeveloperType.FULLSTACK:
                dev_types = [
                    User.DeveloperType.FRONTEND,
                    User.DeveloperType.BACKEND,
                    User.DeveloperType.FULLSTACK,
                ]
            else:
                dev_types = [user.developer_type]
            qs = qs.filter(task_type__in=dev_types)
        return qs.order_by("project__created_at")


class DeveloperTakeTaskView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        task = get_object_or_404(Task, pk=pk, assignee__isnull=True, status=Task.Status.TODO)
        # Проверяем, что пользователь является разработчиком в компании проекта
        if not _is_user_developer_in_company(request.user, task.project.company_id):
            return redirect("crm:dev_open_tasks")
        task.assignee = request.user
        task.status = Task.Status.IN_PROGRESS
        task.save()
        _log_task_activity(
            task=task,
            user=request.user,
            action="assignee_change",
            field="assignee",
            old_value="",
            new_value=request.user.username,
        )
        _log_task_activity(
            task=task,
            user=request.user,
            action="status_change",
            field="status",
            old_value=Task.Status.TODO,
            new_value=Task.Status.IN_PROGRESS,
        )
        return redirect("crm:dev_open_tasks")


class DashboardView(LoginRequiredMixin, View):
    """
    Дашборд для авторизованных пользователей.
    Показывает последние проекты и релевантную информацию в зависимости от роли.
    """
    
    def get(self, request: HttpRequest) -> HttpResponse:
        user: User = request.user
        company_ids = _get_user_company_ids(user)
        ctx = {}
        
        is_manager = _is_user_manager_in_company(user)
        is_developer = _is_user_developer_in_company(user)
        
        if is_manager:
            # Для менеджера: последние проекты и заявки (только те, которые он взял или все, если владелец)
            if user.company_memberships.filter(is_approved=True, is_owner=True).exists():
                # Владелец видит все заявки компании
                requests = ClientRequest.objects.filter(company_id__in=company_ids).order_by("-created_at")[:5]
                projects = Project.objects.filter(company_id__in=company_ids).order_by("-updated_at")[:6]
            else:
                # Обычный менеджер видит только свои заявки
                requests_qs = ClientRequest.objects.filter(company_id__in=company_ids, manager=user).order_by("-created_at")
                requests = requests_qs[:5]
                # У ClientRequest нет поля project_id: проект связан через OneToOne Project.client_request (related_name='project')
                projects = Project.objects.filter(client_request__in=requests_qs).order_by("-updated_at")[:6]
            
            ctx.update({
                "recent_projects": projects,
                "recent_requests": requests,
            })
            return render(request, "crm/dashboard_manager.html", ctx)
        
        elif is_developer:
            # Для разработчика: последние проекты, где он работал, и доступные задачи
            # Сначала получаем project_ids до среза
            tasks_qs = Task.objects.filter(
                assignee=user,
                project__company_id__in=company_ids
            )
            project_ids = list(tasks_qs.values_list("project_id", flat=True).distinct())
            
            # Теперь получаем последние задачи с срезом
            my_tasks = tasks_qs.select_related("project").order_by("-updated_at")[:5]
            
            available_tasks = Task.objects.filter(
                status=Task.Status.TODO,
                assignee__isnull=True,
                project__company_id__in=company_ids
            ).select_related("project")[:5]
            
            # Проекты, где разработчик работал
            recent_projects = Project.objects.filter(
                id__in=project_ids,
                company_id__in=company_ids
            ).order_by("-updated_at")[:6]
            
            ctx.update({
                "recent_projects": recent_projects,
                "my_tasks": my_tasks,
                "available_tasks": available_tasks,
            })
            return render(request, "crm/dashboard_developer.html", ctx)
        
        else:
            # Для клиента: его заявки
            # Проверяем, что пользователь действительно клиент (не менеджер и не разработчик в компании)
            if user.role == User.Role.CLIENT:
                # Дополнительно проверяем, что пользователь не имеет ролей в компании
                has_company_role = is_manager or is_developer
                if not has_company_role:
                    return redirect("crm:client_requests")
            
            # Если пользователь не имеет подтвержденных ролей в компании, но имеет роль MANAGER или DEVELOPER
            # (возможно, он еще не подтвержден администратором), показываем пустой дашборд или редиректим
            # Проверяем, есть ли у пользователя неподтвержденные членства
            has_pending = user.company_memberships.filter(is_approved=False).exists()
            if has_pending:
                # Показываем сообщение о том, что нужно дождаться подтверждения
                ctx = {
                    "pending_approval": True,
                    "message": "Ваша заявка на участие в компании ожидает подтверждения администратором."
                }
                return render(request, "crm/dashboard_pending.html", ctx)
            
            # Если пользователь не имеет ролей в компании и не клиент, показываем пустой дашборд
            # с предложением создать компанию или присоединиться к существующей
            ctx = {
                "no_company": True,
                "message": "Вы не состоите ни в одной компании. Создайте компанию или присоединитесь к существующей."
            }
            return render(request, "crm/dashboard_pending.html", ctx)


class LandingView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        # Если пользователь авторизован, редиректим на дашборд
        if request.user.is_authenticated:
            return redirect("crm:dashboard")
        return render(request, "crm/landing.html")


class CompanyListView(LoginRequiredMixin, ListView):
    """
    Список компаний, в которых состоит текущий пользователь.
    """

    model = Company
    template_name = "crm/company_list.html"

    def get_queryset(self):
        company_ids = _get_user_company_ids(self.request.user)
        return Company.objects.filter(id__in=company_ids).order_by("name")


class CompanyDetailView(LoginRequiredMixin, DetailView):
    """
    Страница настроек компании: участники и публичные ссылки для клиентов.
    """

    model = Company
    template_name = "crm/company_detail.html"

    def get_queryset(self):
        company_ids = _get_user_company_ids(self.request.user)
        return Company.objects.filter(id__in=company_ids)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        company: Company = self.object
        request = self.request

        # Проверяем, является ли пользователь владельцем
        is_owner = company.memberships.filter(
            user=request.user, is_owner=True, is_approved=True
        ).exists()
        ctx["is_owner"] = is_owner

        # Публичные ссылки для клиентов
        slug_url = request.build_absolute_uri(
            reverse("crm:public_request_by_slug", args=[company.slug])
        )
        token_url = request.build_absolute_uri(
            reverse("crm:public_request_by_token", args=[company.public_token])
        )
        ctx["public_slug_url"] = slug_url
        ctx["public_token_url"] = token_url

        # Разделяем участников на подтверждённых и ожидающих подтверждения
        memberships = company.memberships.filter(
            is_approved=True
        ).select_related("user").order_by("user__username")
        ctx["memberships"] = memberships
        ctx["pending_memberships"] = company.memberships.filter(
            is_approved=False
        ).select_related("user").order_by("-created_at")

        # Статистика компании (только для владельца)
        if is_owner:
            # Статистика по сотрудникам
            total_members = memberships.count()
            managers_count = memberships.filter(is_manager=True).count()
            developers_count = memberships.filter(is_developer=True).count()
            owners_count = memberships.filter(is_owner=True).count()
            
            # Статистика по проектам
            projects = Project.objects.filter(company=company)
            total_projects = projects.count()
            active_projects = projects.filter(is_archived=False).count()
            archived_projects = projects.filter(is_archived=True).count()
            
            # Статистика по заявкам
            requests = ClientRequest.objects.filter(company=company)
            total_requests = requests.count()
            new_requests = requests.filter(status=ClientRequest.Status.NEW).count()
            in_progress_requests = requests.filter(status=ClientRequest.Status.IN_PROGRESS).count()
            done_requests = requests.filter(status=ClientRequest.Status.DONE).count()
            
            # Статистика по задачам
            tasks = Task.objects.filter(project__company=company)
            total_tasks = tasks.count()
            todo_tasks = tasks.filter(status=Task.Status.TODO).count()
            in_progress_tasks = tasks.filter(status=Task.Status.IN_PROGRESS).count()
            done_tasks = tasks.filter(status=Task.Status.DONE).count()
            
            # Последние заявки
            recent_requests = requests.select_related("manager", "client").order_by("-created_at")[:5]
            
            # Последние проекты
            recent_projects = projects.order_by("-updated_at")[:5]
            
            ctx.update({
                "stats": {
                    "members": {
                        "total": total_members,
                        "managers": managers_count,
                        "developers": developers_count,
                        "owners": owners_count,
                    },
                    "projects": {
                        "total": total_projects,
                        "active": active_projects,
                        "archived": archived_projects,
                    },
                    "requests": {
                        "total": total_requests,
                        "new": new_requests,
                        "in_progress": in_progress_requests,
                        "done": done_requests,
                    },
                    "tasks": {
                        "total": total_tasks,
                        "todo": todo_tasks,
                        "in_progress": in_progress_tasks,
                        "done": done_tasks,
                    },
                },
                "recent_requests": recent_requests,
                "recent_projects": recent_projects,
            })

        return ctx

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.object = self.get_object()
        company: Company = self.object

        # Разрешаем изменять участников только владельцам
        is_owner = company.memberships.filter(
            user=request.user, is_owner=True, is_approved=True
        ).exists()
        if not is_owner:
            return redirect("crm:company_detail", slug=company.slug)

        # Обработка одобрения заявки с выбором ролей
        action = request.POST.get("action")
        if action == "approve":
            membership_id = request.POST.get("membership_id")
            try:
                membership = CompanyMembership.objects.get(
                    id=membership_id, company=company, is_approved=False
                )
                # Получаем выбранные роли
                is_manager = request.POST.get(f"is_manager_{membership_id}") == "on"
                is_developer = request.POST.get(f"is_developer_{membership_id}") == "on"
                
                if not is_manager and not is_developer:
                    # Если не выбрано ни одной роли, не подтверждаем
                    return redirect("crm:company_detail", slug=company.slug)
                
                membership.is_manager = is_manager
                membership.is_developer = is_developer
                membership.is_approved = True
                membership.save()
            except CompanyMembership.DoesNotExist:
                pass
            return redirect("crm:company_detail", slug=company.slug)
        
        elif action == "reject":
            membership_id = request.POST.get("membership_id")
            try:
                membership = CompanyMembership.objects.get(
                    id=membership_id, company=company, is_approved=False
                )
                membership.delete()
            except CompanyMembership.DoesNotExist:
                pass
            return redirect("crm:company_detail", slug=company.slug)
        
        elif action == "update_roles":
            # Обновление ролей существующего участника
            membership_id = request.POST.get("membership_id")
            try:
                membership = CompanyMembership.objects.get(
                    id=membership_id, company=company, is_approved=True
                )
                # Не позволяем изменять роли владельца
                if membership.is_owner:
                    return redirect("crm:company_detail", slug=company.slug)
                
                # Получаем выбранные роли
                is_manager = request.POST.get(f"is_manager_{membership_id}") == "on"
                is_developer = request.POST.get(f"is_developer_{membership_id}") == "on"
                
                # Хотя бы одна роль должна быть выбрана (кроме владельца)
                if not is_manager and not is_developer:
                    # Если не выбрано ни одной роли, оставляем как есть или можно удалить участника
                    pass
                
                membership.is_manager = is_manager
                membership.is_developer = is_developer
                membership.save()
            except CompanyMembership.DoesNotExist:
                pass
            return redirect("crm:company_detail", slug=company.slug)
        
        elif action == "regenerate_join_code":
            # Регенерация кода для подключения сотрудников
            from django.utils.crypto import get_random_string
            company.join_code = get_random_string(10)
            company.save()
            return redirect("crm:company_detail", slug=company.slug)
        
        elif action == "regenerate_public_token":
            # Регенерация публичного токена
            from django.utils.crypto import get_random_string
            company.public_token = get_random_string(24)
            company.save()
            return redirect("crm:company_detail", slug=company.slug)
        
        elif action == "remove_member":
            # Удаление участника из компании
            membership_id = request.POST.get("membership_id")
            try:
                membership = CompanyMembership.objects.get(
                    id=membership_id, company=company, is_approved=True
                )
                # Не позволяем удалять владельца
                if not membership.is_owner:
                    membership.delete()
            except CompanyMembership.DoesNotExist:
                pass
            return redirect("crm:company_detail", slug=company.slug)

        return redirect("crm:company_detail", slug=company.slug)


class ClientRequestListView(ClientRequiredMixin, ListView):
    model = ClientRequest
    template_name = "crm/client/requests.html"

    def get_queryset(self):
        # При первом заходе клиента привязываем заявки из сессии (оставленные до регистрации)
        session_ids = self.request.session.get("anonymous_request_ids") or []
        if session_ids:
            ClientRequest.objects.filter(pk__in=session_ids).update(client=self.request.user)
            del self.request.session["anonymous_request_ids"]
            self.request.session.modified = True
        return ClientRequest.objects.filter(client=self.request.user).order_by("-created_at")


class ClientRequestBySessionView(View):
    """
    Просмотр заявки по сессии (для анонимных, которые только что отправили заявку).
    Доступ только если pk заявки лежит в session['anonymous_request_ids'].
    """

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        session_ids = list(request.session.get("anonymous_request_ids", []))
        if pk not in session_ids:
            return redirect("crm:landing")
        req = get_object_or_404(ClientRequest, pk=pk)
        ctx = {"object": req, "by_session": True}
        return render(request, "crm/client/request_detail_by_session.html", ctx)


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
            # Начало обсуждения от клиента — переводим из NEW в DISCUSS
            if obj.status == ClientRequest.Status.NEW:
                obj.status = ClientRequest.Status.DISCUSS
                obj.save(update_fields=["status", "updated_at"])
        return redirect("crm:client_request_detail", pk=obj.pk)


class ClientCreateRequestView(ClientRequiredMixin, View):
    """
    Создание новой заявки клиентом с выбором компании.
    Показываем все компании, но есть фильтр по компаниям, куда уже отправлял заявки.
    """

    template_name = "crm/client/request_create.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        # Показываем все компании
        companies = Company.objects.all().order_by("name")
        if not companies.exists():
            return render(request, self.template_name, {"companies": companies, "no_companies": True})
        
        # Получаем ID компаний, куда клиент уже отправлял заявки
        user_companies_ids = list(
            Company.objects.filter(client_requests__client=request.user)
            .distinct()
            .values_list("id", flat=True)
        )
        
        ctx = {
            "companies": companies,
            "user_companies_ids": user_companies_ids,
        }
        return render(request, self.template_name, ctx)

    def post(self, request: HttpRequest) -> HttpResponse:
        companies = Company.objects.all()
        if not companies.exists():
            return render(request, self.template_name, {"companies": companies, "no_companies": True})
        company_id = request.POST.get("company")
        company = get_object_or_404(Company, pk=company_id)
        # Проверяем, что компания существует
        if not companies.filter(pk=company.pk).exists():
            return redirect("crm:client_request_create")
        data = request.POST
        req = ClientRequest.objects.create(
            company=company,
            client=request.user,
            project_type=data.get("project_type"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            contact_email=data.get("contact_email", ""),
            contact_telegram=data.get("contact_telegram", ""),
        )
        return redirect("crm:client_request_detail", pk=req.pk)


# SignupView удален - теперь используется accounts.views.RegisterUser - теперь используется accounts.views.RegisterUser


class KanbanBoardView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "crm/kanban.html"
    
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        # Доступ имеют: владелец компании, менеджер который взял заявку, или разработчик с задачами
        has_access = (
            _is_user_manager_in_company(request.user, obj.company_id) or
            (obj.client_request and obj.client_request.manager == request.user) or
            _is_user_developer_in_company(request.user, obj.company_id)
        )
        if not has_access:
            return redirect("crm:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project: Project = self.object
        base_qs = project.tasks.select_related("assignee").order_by("order", "created_at")

        # Спринты пока не используем в логике канбана: доска показывает все задачи проекта по статусам.
        ctx["sprints"] = []
        ctx["active_sprint"] = None

        # Конфигурация колонок канбана: если нет — создаём дефолтную для проекта.
        default_columns = [
            (Task.Status.TODO, "К выполнению", 1),
            (Task.Status.IN_PROGRESS, "В работе", 2),
            (Task.Status.REVIEW, "К проверке", 3),
            (Task.Status.DONE, "Готово", 4),
        ]
        if not project.kanban_columns.exists():
            for status, title, order in default_columns:
                KanbanColumnConfig.objects.create(
                    project=project,
                    status=status,
                    title=title,
                    order=order,
                    is_visible=True,
                    wip_limit=0,
                )

        columns = []
        for col in project.kanban_columns.all():
            col_tasks = base_qs.filter(status=col.status)
            sp_sum = col_tasks.aggregate(models.Sum("story_points"))["story_points__sum"] or 0
            columns.append(
                {
                    "config": col,
                    "tasks": col_tasks,
                    "count": col_tasks.count(),
                    "story_points_sum": sp_sum,
                }
            )
        ctx["kanban_columns"] = columns

        # Сохранённые фильтры текущего пользователя
        ctx["filter_presets"] = KanbanFilterPreset.objects.filter(
            project=project, user=self.request.user
        ).order_by("name")

        # Может ли пользователь редактировать настройки канбана
        ctx["can_edit_kanban"] = _is_user_manager_in_company(self.request.user, project.company_id)

        # Для обратной совместимости: отдельные списки по статусам (по текущей конфигурации).
        board_qs = base_qs
        ctx["todo"] = board_qs.filter(status=Task.Status.TODO)
        ctx["in_progress"] = board_qs.filter(status=Task.Status.IN_PROGRESS)
        ctx["review"] = board_qs.filter(status=Task.Status.REVIEW)
        ctx["done"] = board_qs.filter(status=Task.Status.DONE)

        # Беклог: задачи без исполнителя в статусе TODO (пул для набора работы).
        ctx["backlog"] = base_qs.filter(status=Task.Status.TODO, assignee__isnull=True)
        dev_ids = list(
            CompanyMembership.objects.filter(
                company=project.company,
                is_approved=True,
                is_developer=True,
            ).values_list("user_id", flat=True)
        )
        ctx["developers"] = (
            User.objects.filter(id__in=dev_ids, is_active=True)
            .order_by("username")
            .only("id", "username", "developer_type")
        )
        return ctx

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Обработка настроек канбана (редактирование колонок, сохранение пресетов фильтра).
        """
        self.object = self.get_object()
        project: Project = self.object

        action = request.POST.get("action")

        # Разрешаем редактирование только менеджерам/владельцам компании
        if not _is_user_manager_in_company(request.user, project.company_id):
            return redirect("crm:kanban_board", pk=project.pk)

        if action == "update_kanban_columns":
            for col in project.kanban_columns.all():
                prefix = f"col_{col.id}_"
                title = (request.POST.get(prefix + "title") or "").strip() or col.title
                order_raw = request.POST.get(prefix + "order") or col.order
                visible_val = request.POST.get(prefix + "visible")
                wip_raw = request.POST.get(prefix + "wip") or col.wip_limit
                try:
                    order_val = int(order_raw)
                except (TypeError, ValueError):
                    order_val = col.order
                try:
                    wip_val = int(wip_raw)
                except (TypeError, ValueError):
                    wip_val = col.wip_limit
                col.title = title
                col.order = max(0, order_val)
                col.is_visible = bool(visible_val)
                col.wip_limit = max(0, wip_val)
                col.save()
            return redirect("crm:kanban_board", pk=project.pk)

        if action == "save_filter_preset":
            name = (request.POST.get("name") or "").strip()
            if not name:
                return JsonResponse({"ok": False, "error": "name_required"}, status=400)
            assignee_raw = request.POST.get("assignee") or ""
            task_type = (request.POST.get("task_type") or "").strip()
            assignee_id = None
            try:
                if assignee_raw:
                    assignee_id = int(assignee_raw)
            except (TypeError, ValueError):
                assignee_id = None
            preset, _created = KanbanFilterPreset.objects.update_or_create(
                project=project,
                user=request.user,
                name=name,
                defaults={
                    "assignee_id": assignee_id,
                    "task_type": task_type,
                },
            )
            return JsonResponse({"ok": True, "id": preset.id})

        return redirect("crm:kanban_board", pk=project.pk)


@method_decorator(require_POST, name='dispatch')
class KanbanMoveApiView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            import json
            payload = json.loads(request.body.decode("utf-8"))
            task_id = int(payload.get("id"))
            new_status = payload.get("status")
            sprint_raw = payload.get("sprint") or payload.get("sprint_id")
        except Exception:
            return JsonResponse({"ok": False, "error": "invalid_payload"}, status=400)

        if new_status not in dict(Task.Status.choices):
            return JsonResponse({"ok": False, "error": "bad_status"}, status=400)

        task = get_object_or_404(Task, pk=task_id)
        # Проверка зависимости: если задача зависит от другой, не даём закрыть раньше неё
        if (
            new_status == Task.Status.DONE
            and task.starts_after_task_id
            and task.starts_after_task.status != Task.Status.DONE
        ):
            return JsonResponse(
                {"ok": False, "error": "dependency_not_done", "blocker_id": task.starts_after_task_id},
                status=400,
            )
        old_status = task.status
        task.status = new_status

        # Если с фронта передали активный спринт — привязываем задачу к нему (вывод из беклога в текущий спринт)
        if sprint_raw not in (None, "", 0):
            try:
                sid = int(sprint_raw)
            except (TypeError, ValueError):
                sid = None
            if sid:
                try:
                    sprint_obj = Sprint.objects.get(pk=sid, project=task.project)
                except Sprint.DoesNotExist:
                    sprint_obj = None
                if sprint_obj is not None:
                    task.sprint = sprint_obj
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
        if old_status != new_status:
            _log_task_activity(
                task=task,
                user=request.user,
                action="status_change",
                field="status",
                old_value=old_status,
                new_value=new_status,
            )
        return JsonResponse({"ok": True})


@method_decorator(require_POST, name="dispatch")
class KanbanCreateTaskApiView(LoginRequiredMixin, View):
    """API создания задачи с канбана (модалка или кнопка в колонке)."""

    def post(self, request: HttpRequest) -> JsonResponse:
        import json

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

        project_id = payload.get("project_id")
        status = payload.get("status", Task.Status.TODO)
        title = (payload.get("title") or "").strip()
        description = (payload.get("description") or "").strip()
        task_type = payload.get("task_type") or "fullstack"
        assignee_id = payload.get("assignee") or None
        due_date = payload.get("due_date") or None
        story_points = int(payload.get("story_points") or 0)
        story_points = max(0, min(100, story_points))
        sprint_id = payload.get("sprint") or payload.get("sprint_id") or None

        if not project_id or not title:
            return JsonResponse({"ok": False, "error": "project_id_and_title_required"}, status=400)
        if status not in dict(Task.Status.choices):
            status = Task.Status.TODO

        project = get_object_or_404(Project, pk=project_id)
        if not (
            _is_user_manager_in_company(request.user, project.company_id)
            or (project.client_request and project.client_request.manager == request.user)
        ):
            return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

        assignee = None
        if assignee_id and project.company_id:
            dev_ids = list(
                CompanyMembership.objects.filter(
                    company=project.company,
                    is_approved=True,
                    is_developer=True,
                ).values_list("user_id", flat=True)
            )
            if int(assignee_id) in dev_ids:
                assignee = get_object_or_404(User, pk=assignee_id)

        if task_type not in dict(Task.TaskType.choices):
            task_type = "fullstack"

        sprint = None
        if sprint_id:
            try:
                sprint_obj = Sprint.objects.get(pk=int(sprint_id), project=project)
            except (ValueError, TypeError, Sprint.DoesNotExist):
                sprint_obj = None
            sprint = sprint_obj

        last_order = (
            Task.objects.filter(project=project, status=status)
            .order_by("-order")
            .values_list("order", flat=True)
            .first()
        ) or 0

        task = Task.objects.create(
            project=project,
            sprint=sprint,
            title=title,
            description=description,
            task_type=task_type,
            status=status,
            created_by=request.user,
            assignee=assignee,
            due_date=due_date,
            story_points=story_points,
            order=last_order + 1,
        )
        _log_task_activity(
            task=task,
            user=request.user,
            action="create",
            field="task",
            old_value="",
            new_value=task.title,
        )
        return JsonResponse({
            "ok": True,
            "task": {
                "id": task.id,
                "title": task.title,
                "task_type": task.task_type,
                "task_type_label": task.get_task_type_display(),
                "status": task.status,
                "story_points": task.story_points,
                "assignee": getattr(task.assignee, "username", None),
                "due_date": task.due_date.isoformat() if task.due_date else None,
            },
        })


@method_decorator(require_POST, name="dispatch")
class RequestCheckpointApiView(LoginRequiredMixin, View):
    """
    JSON‑API для диаграммы чекпоинтов заявки:
    - action=create  (title, comment, is_done?, x?, y?)
    - action=update  (id, title?, comment?, is_done?)
    - action=delete  (id)
    - action=reorder (ids: [id1, id2, ...])
    - action=position (id, x, y) — сдвиг узла на диаграмме
    - action=edge_create (source_id, target_id)
    - action=edge_delete (id) — id ребра
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
            is_done = payload.get("is_done", False)
            x = payload.get("x")
            y = payload.get("y")
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
                is_done=bool(is_done),
                order=last_order + 1,
                x=int(x) if x is not None else 0,
                y=int(y) if y is not None else 0,
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
                        "x": cp.x,
                        "y": cp.y,
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

        if action == "position":
            cp_id = payload.get("id")
            x = payload.get("x")
            y = payload.get("y")
            if cp_id is None or x is None or y is None:
                return JsonResponse({"ok": False, "error": "id_x_y_required"}, status=400)
            cp = get_object_or_404(RequestCheckpoint, pk=cp_id, request=client_request)
            cp.x = int(x)
            cp.y = int(y)
            cp.save(update_fields=["x", "y"])
            return JsonResponse({"ok": True})

        if action == "edge_create":
            source_id = payload.get("source_id")
            target_id = payload.get("target_id")
            if not source_id or not target_id:
                return JsonResponse({"ok": False, "error": "source_id_target_id_required"}, status=400)
            if source_id == target_id:
                return JsonResponse({"ok": False, "error": "no_self_edge"}, status=400)
            source = get_object_or_404(RequestCheckpoint, pk=source_id, request=client_request)
            target = get_object_or_404(RequestCheckpoint, pk=target_id, request=client_request)
            edge, created = RequestCheckpointEdge.objects.get_or_create(
                request=client_request,
                source=source,
                target=target,
            )
            return JsonResponse({
                "ok": True,
                "edge": {"id": edge.id, "source_id": edge.source_id, "target_id": edge.target_id},
            })

        if action == "edge_delete":
            edge_id = payload.get("id")
            if not edge_id:
                return JsonResponse({"ok": False, "error": "id_required"}, status=400)
            edge = get_object_or_404(RequestCheckpointEdge, pk=edge_id, request=client_request)
            edge.delete()
            return JsonResponse({"ok": True})

        return JsonResponse({"ok": False, "error": "bad_action"}, status=400)


@method_decorator(require_POST, name="dispatch")
class TaskPanelApiView(LoginRequiredMixin, View):
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
            activity = list(
                task.activities.select_related("author")
                .order_by("-created_at")[:30]
                .values("id", "action", "field", "old_value", "new_value", "created_at", "author__username")
            )[::-1]
            # Готовим человекочитаемый текст для фронта
            activity_payload = []
            status_labels = dict(Task.Status.choices)
            field_labels = {
                "task": "Задача",
                "status": "Статус",
                "assignee": "Исполнитель",
                "due_date": "Дедлайн",
                "story_points": "Важность",
                "title": "Название",
            }
            action_prefixes = {
                "create": "Создана задача",
                "status_change": "Изменён статус",
                "assignee_change": "Изменён исполнитель",
                "field_change": "Изменено поле",
            }

            from datetime import datetime

            def _fmt_date(val: str) -> str:
                if not val:
                    return "—"
                try:
                    dt = datetime.fromisoformat(str(val))
                    return dt.strftime("%d.%m.%Y")
                except Exception:
                    try:
                        dt = datetime.strptime(str(val), "%Y-%m-%d")
                        return dt.strftime("%d.%m.%Y")
                    except Exception:
                        return str(val)

            for a in activity:
                raw_field = (a.get("field") or "").strip()
                action_code = (a.get("action") or "").strip()
                raw_old = a.get("old_value") or ""
                raw_new = a.get("new_value") or ""

                if raw_field == "status":
                    old_val = status_labels.get(raw_old, raw_old or "—")
                    new_val = status_labels.get(raw_new, raw_new or "—")
                elif raw_field == "due_date":
                    old_val = _fmt_date(raw_old)
                    new_val = _fmt_date(raw_new)
                elif raw_field == "story_points":
                    old_val = str(raw_old or "0")
                    new_val = str(raw_new or "0")
                else:
                    old_val = str(raw_old or "—")
                    new_val = str(raw_new or "—")

                if action_code == "create":
                    title_part = new_val if new_val != "—" else task.title
                    text = f"Создана задача «{title_part}»"
                elif raw_field:
                    field_label = field_labels.get(raw_field, raw_field)
                    prefix = action_prefixes.get(action_code, "Изменено поле")
                    text = f"{prefix} «{field_label}»: «{old_val}» → «{new_val}»"
                else:
                    prefix = action_prefixes.get(action_code, "Действие")
                    text = f"{prefix}: «{new_val or '—'}»"

                activity_payload.append(
                    {
                        "id": a["id"],
                        "text": text,
                        "created_at": a["created_at"],
                        "author__username": a["author__username"],
                    }
                )
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
                        "assignee_id": task.assignee_id,
                        "created_by": getattr(task.created_by, "username", None),
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "sprint_id": task.sprint_id,
                        "sprint_name": task.sprint.name if task.sprint_id else None,
                        "project_id": task.project_id,
                    },
                    "checkpoints": checkpoints,
                    "chat": chat,
                    "activity": activity_payload,
                }
            )

        # ---- Обновление полей задачи ----
        if action == "task_update":
            assignee_id = payload.get("assignee")
            due_date_raw = payload.get("due_date")
            story_points_raw = payload.get("story_points")
            title_new = payload.get("title")
            sprint_raw = payload.get("sprint") or payload.get("sprint_id")
            status_raw = payload.get("status")

            if not _is_user_manager_in_company(request.user, task.project.company_id) and request.user != task.assignee:
                return JsonResponse({"ok": False, "error": "forbidden"}, status=403)

            changed = False
            # Проверяем зависимость перед сменой статуса
            # Статус / стадия задачи
            if status_raw is not None and status_raw in dict(Task.Status.choices):
                if (
                    status_raw == Task.Status.DONE
                    and task.starts_after_task_id
                    and task.starts_after_task.status != Task.Status.DONE
                ):
                    return JsonResponse(
                        {"ok": False, "error": "dependency_not_done", "blocker_id": task.starts_after_task_id},
                        status=400,
                    )
                if status_raw != task.status:
                    old_status = task.status
                    task.status = status_raw
                    # Помещаем задачу в конец соответствующей колонки
                    last_order = (
                        Task.objects.filter(project=task.project, status=status_raw)
                        .exclude(pk=task.pk)
                        .order_by("-order")
                        .values_list("order", flat=True)
                        .first()
                    ) or 0
                    task.order = last_order + 1
                    changed = True
                    _log_task_activity(
                        task=task,
                        user=request.user,
                        action="status_change",
                        field="status",
                        old_value=old_status,
                        new_value=status_raw,
                    )
            if assignee_id is not None:
                if assignee_id in (None, "", 0):
                    if task.assignee_id:
                        _log_task_activity(
                            task=task,
                            user=request.user,
                            action="assignee_change",
                            field="assignee",
                            old_value=getattr(task.assignee, "username", ""),
                            new_value="",
                        )
                    task.assignee = None
                    changed = True
                else:
                    try:
                        aid = int(assignee_id)
                    except (ValueError, TypeError):
                        aid = None
                    if aid and task.project.company_id:
                        dev_ids = list(
                            CompanyMembership.objects.filter(
                                company=task.project.company,
                                is_approved=True,
                                is_developer=True,
                            ).values_list("user_id", flat=True)
                        )
                        if aid in dev_ids:
                            old_name = getattr(task.assignee, "username", "")
                            new_user = get_object_or_404(User, pk=aid)
                            task.assignee = new_user
                            changed = True
                            _log_task_activity(
                                task=task,
                                user=request.user,
                                action="assignee_change",
                                field="assignee",
                                old_value=old_name,
                                new_value=new_user.username,
                            )
            if due_date_raw is not None:
                from datetime import date
                old_due_date = task.due_date
                old_due = old_due_date.isoformat() if old_due_date else ""
                if due_date_raw:
                    try:
                        new_due_date = date.fromisoformat(str(due_date_raw))
                    except (ValueError, TypeError):
                        new_due_date = task.due_date
                else:
                    new_due_date = None

                if new_due_date != task.due_date:
                    task.due_date = new_due_date
                    changed = True
                    _log_task_activity(
                        task=task,
                        user=request.user,
                        action="field_change",
                        field="due_date",
                        old_value=old_due,
                        new_value=task.due_date.isoformat() if task.due_date else "",
                    )
            if story_points_raw is not None:
                old_sp = task.story_points
                sp = max(0, min(100, int(story_points_raw)))
                task.story_points = sp
                changed = True
                if old_sp != sp:
                    _log_task_activity(
                        task=task,
                        user=request.user,
                        action="field_change",
                        field="story_points",
                        old_value=str(old_sp),
                        new_value=str(sp),
                    )
            if title_new is not None:
                t = (title_new or "").strip()
                if t:
                    old_title = task.title
                    task.title = t
                    changed = True
                    if old_title != t:
                        _log_task_activity(
                            task=task,
                            user=request.user,
                            action="field_change",
                            field="title",
                            old_value=old_title,
                            new_value=t,
                        )
            if sprint_raw is not None:
                if sprint_raw in ("", None, 0):
                    task.sprint = None
                    changed = True
                else:
                    try:
                        sid = int(sprint_raw)
                    except (TypeError, ValueError):
                        sid = None
                    if sid:
                        try:
                            sprint_obj = Sprint.objects.get(pk=sid, project=task.project)
                        except Sprint.DoesNotExist:
                            sprint_obj = None
                        if sprint_obj is not None:
                            task.sprint = sprint_obj
                            changed = True

            if changed:
                task.save()
            return JsonResponse({"ok": True})

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
