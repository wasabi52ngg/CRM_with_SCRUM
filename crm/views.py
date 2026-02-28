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
from .models import Company, CompanyMembership, ClientRequest, Project, Task, RequestCheckpoint, TaskCheckpoint
from .models import Message


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
        # Все чекпоинты заявки в удобном для таймлайна виде
        ctx["checkpoints"] = list(
            client_request.checkpoints.all().values(
                "id", "title", "comment", "is_done", "order", "created_at", "updated_at"
            )
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
    Важно: клиент может создать и самую первую заявку (раньше это было заблокировано).
    """

    template_name = "crm/client/request_create.html"

    def get_client_companies(self, user):
        # Для клиентского портала показываем все компании.
        # Если нужно ограничивать видимость — здесь можно добавить фильтр (например, только активные компании).
        return Company.objects.all().order_by("name")

    def get(self, request: HttpRequest) -> HttpResponse:
        companies = self.get_client_companies(request.user)
        if not companies.exists():
            # В системе нет компаний — создавать заявку некуда
            return render(request, self.template_name, {"companies": companies, "no_companies": True})
        ctx = {"companies": companies}
        return render(request, self.template_name, ctx)

    def post(self, request: HttpRequest) -> HttpResponse:
        companies = self.get_client_companies(request.user)
        if not companies.exists():
            return render(request, self.template_name, {"companies": companies, "no_companies": True})
        company_id = request.POST.get("company")
        company = get_object_or_404(Company, pk=company_id)
        # Безопасность: выбранная компания должна быть в доступном списке
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
        ctx["todo"] = project.tasks.filter(status=Task.Status.TODO).order_by("order", "created_at")
        ctx["in_progress"] = project.tasks.filter(status=Task.Status.IN_PROGRESS).order_by("order", "created_at")
        ctx["review"] = project.tasks.filter(status=Task.Status.REVIEW).order_by("order", "created_at")
        ctx["done"] = project.tasks.filter(status=Task.Status.DONE).order_by("order", "created_at")
        return ctx


@method_decorator(require_POST, name='dispatch')
class KanbanMoveApiView(LoginRequiredMixin, View):
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
class RequestCheckpointApiView(LoginRequiredMixin, View):
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
