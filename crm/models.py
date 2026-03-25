from django.db import models
from django.conf import settings
from django.db.models import Max
from django.utils.crypto import get_random_string


class Company(models.Model):
    """
    Компания‑арендатор системы (аналог организации в Jira).
    Все проекты, заявки и задачи принадлежат конкретной компании.
    """

    name = models.CharField("Название компании", max_length=255)
    slug = models.SlugField(
        "Слаг компании",
        max_length=64,
        unique=True,
        help_text="Короткий идентификатор компании в URL",
    )
    description = models.TextField("Описание", blank=True)
    industry = models.CharField("Сфера деятельности", max_length=255, blank=True)
    public_token = models.CharField(
        "Токен публичной формы",
        max_length=32,
        unique=True,
        editable=False,
        help_text="Используется в публичной ссылке для заявок клиентов",
    )
    join_code = models.CharField(
        "Код для подключения сотрудников",
        max_length=16,
        unique=True,
        editable=False,
        null=True,
        blank=True,
        help_text="Секретный код, который сотрудники вводят при регистрации",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # Генерируем токен для публичной формы и секретный код один раз
        if not self.public_token:
            self.public_token = get_random_string(24)
        if not self.join_code:
            self.join_code = get_random_string(10)
        super().save(*args, **kwargs)


class CompanyMembership(models.Model):
    """
    Принадлежность пользователя к компании и его роль внутри неё.
    Пользователь может быть менеджером, разработчиком или обоими одновременно.
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name="Компания",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_memberships",
        verbose_name="Пользователь",
    )
    is_owner = models.BooleanField(
        "Владелец компании",
        default=False,
        help_text="Администратор компании, имеет полный доступ",
    )
    is_manager = models.BooleanField(
        "Менеджер",
        default=False,
        help_text="Может работать с заявками и проектами",
    )
    is_developer = models.BooleanField(
        "Разработчик",
        default=False,
        help_text="Может работать с задачами в проектах",
    )
    is_approved = models.BooleanField(
        "Подтверждён администратором",
        default=False,
        help_text="Администратор должен подтвердить участие пользователя в компании",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Участник компании"
        verbose_name_plural = "Участники компаний"
        unique_together = ("company", "user")

    def __str__(self) -> str:
        roles = []
        if self.is_owner:
            roles.append("Владелец")
        if self.is_manager:
            roles.append("Менеджер")
        if self.is_developer:
            roles.append("Разработчик")
        role_str = ", ".join(roles) if roles else "Без роли"
        return f"{self.user} @ {self.company} ({role_str})"


class ClientRequest(models.Model):
    class ProjectType(models.TextChoices):
        WEBSITE = "website", "Сайт"
        BOT = "bot", "Бот (Telegram и др.)"
        MOBILE = "mobile", "Мобильное приложение"

    class Status(models.TextChoices):
        NEW = "new", "Новая"
        DISCUSS = "discuss", "В обсуждении"
        IN_PROGRESS = "in_progress", "В работе"
        DONE = "done", "Завершена"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="client_requests",
        null=True,
        blank=True,
        help_text="Компания, для которой оставлена заявка",
    )
    project_type = models.CharField(max_length=20, choices=ProjectType.choices)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    contact_email = models.EmailField()
    contact_telegram = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="client_requests"
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="managed_requests"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.title} ({self.get_project_type_display()})"


class Project(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="projects",
        null=True,
        blank=True,
        help_text="Компания‑владелец проекта",
    )
    client_request = models.OneToOneField(
        ClientRequest,
        on_delete=models.CASCADE,
        related_name="project",
        null=True,
        blank=True,
        help_text="Исходная клиентская заявка (если проект создан по заявке)",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    definition_of_done = models.TextField(
        "Definition of Done",
        blank=True,
        help_text="Общие критерии готовности для задач проекта (Scrum)",
    )
    issue_key_prefix = models.CharField(
        "Префикс ключа задачи",
        max_length=16,
        default="PRJ",
        help_text="Например PRJ для ключа PRJ-12",
    )
    product_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_projects",
        verbose_name="Product Owner",
    )
    scrum_master = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scrummaster_projects",
        verbose_name="Scrum Master",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Epic(models.Model):
    """Крупная цель (эпик) в рамках проекта."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="epics",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#6366f1")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.project}: {self.title}"


class RequestCheckpoint(models.Model):
    """
    Узел диаграммы этапов заявки. Имеет позицию (x, y) на холсте и связи через RequestCheckpointEdge.
    """

    request = models.ForeignKey(
        ClientRequest,
        on_delete=models.CASCADE,
        related_name="checkpoints",
    )
    title = models.CharField("Заголовок", max_length=255)
    comment = models.TextField("Комментарий / детали этапа", blank=True)
    is_done = models.BooleanField("Выполнен", default=False)
    order = models.PositiveIntegerField("Порядок", default=0)
    x = models.IntegerField("Позиция X на диаграмме", default=0)
    y = models.IntegerField("Позиция Y на диаграмме", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"{self.request_id}: {self.title}"


class RequestCheckpointEdge(models.Model):
    """
    Связь между двумя чекпоинтами на диаграмме (как рёбра в графе).
    """

    request = models.ForeignKey(
        ClientRequest,
        on_delete=models.CASCADE,
        related_name="checkpoint_edges",
    )
    source = models.ForeignKey(
        RequestCheckpoint,
        on_delete=models.CASCADE,
        related_name="outgoing_edges",
    )
    target = models.ForeignKey(
        RequestCheckpoint,
        on_delete=models.CASCADE,
        related_name="incoming_edges",
    )

    class Meta:
        unique_together = ("request", "source", "target")
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.source_id} → {self.target_id}"


class Sprint(models.Model):
    project = models.ForeignKey("Project", on_delete=models.CASCADE, related_name="sprints")
    name = models.CharField(max_length=255)
    goal = models.TextField("Цель спринта", blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date", "-id"]

    def __str__(self) -> str:
        return f"{self.project.name}: {self.name}"


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "К выполнению"
        IN_PROGRESS = "in_progress", "В работе"
        REVIEW = "review", "К проверке/QA"
        DONE = "done", "Готово"

    class TaskType(models.TextChoices):
        FRONTEND = "frontend", "Фронтенд"
        BACKEND = "backend", "Бэкенд"
        FULLSTACK = "fullstack", "Фулстек"
        DEVOPS = "devops", "DevOps"
        QA = "qa", "Тестирование"
        ANDROID = "android", "Android"
        DB = "db", "База данных"

    class Priority(models.TextChoices):
        LOW = "low", "Низкий"
        MEDIUM = "medium", "Средний"
        HIGH = "high", "Высокий"
        CRITICAL = "critical", "Критический"

    class WorkItemType(models.TextChoices):
        USER_STORY = "story", "User Story"
        BUG = "bug", "Баг"
        TASK = "task", "Задача"
        SUBTASK = "subtask", "Подзадача"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    sprint = models.ForeignKey(Sprint, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    epic = models.ForeignKey(
        "Epic",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    acceptance_criteria = models.TextField("Критерии приёмки", blank=True)
    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    work_item_type = models.CharField(
        max_length=20,
        choices=WorkItemType.choices,
        default=WorkItemType.TASK,
    )
    priority = models.CharField(
        max_length=16,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_tasks",
        help_text="Постановщик задачи",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks"
    )
    due_date = models.DateField(null=True, blank=True, help_text="Дедлайн/дата завершения")
    story_points = models.PositiveSmallIntegerField(default=0)
    backlog_rank = models.PositiveIntegerField(
        default=0,
        help_text="Порядок в Product Backlog (меньше — выше в списке)",
    )
    issue_number = models.PositiveIntegerField(null=True, blank=True, editable=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    starts_after_task = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="unblocks"
    )

    class Meta:
        indexes = [
            models.Index(fields=["project", "issue_number"], name="crm_task_proj_issue_idx"),
            models.Index(fields=["project", "backlog_rank"], name="crm_task_proj_bkrank_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.get_task_type_display()}] {self.title}"

    @property
    def issue_key(self) -> str:
        if not self.issue_number:
            return ""
        prefix = (self.project.issue_key_prefix or "PRJ").strip() or "PRJ"
        return f"{prefix}-{self.issue_number}"

    def save(self, *args, **kwargs):
        if self.issue_number is None and self.project_id:
            agg = Task.objects.filter(project_id=self.project_id).aggregate(m=Max("issue_number"))
            max_n = agg["m"]
            self.issue_number = (max_n or 0) + 1
        super().save(*args, **kwargs)


class KanbanColumnConfig(models.Model):
    """
    Настройки колонок канбана для проекта.
    Колонки привязаны к фиксированным статусам задачи, но можно настраивать
    их название, порядок отображения, видимость и WIP‑лимит.
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="kanban_columns",
    )
    status = models.CharField(
        max_length=20,
        choices=Task.Status.choices,
        help_text="Какой статус задач отображается в колонке",
    )
    title = models.CharField(
        max_length=255,
        help_text="Отображаемое название колонки на доске",
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Порядок отображения колонки слева направо",
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="Показывать ли колонку на доске",
    )
    wip_limit = models.PositiveSmallIntegerField(
        default=0,
        help_text="Максимальное количество задач в колонке (0 — без ограничения)",
    )
    policy_note = models.TextField(
        "Политика колонки",
        blank=True,
        help_text="Кто двигает карточки, что означает колонка (Kanban/Scrum)",
    )

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("project", "status")

    def __str__(self) -> str:
        return f"{self.project}: {self.title} ({self.status})"


class KanbanFilterPreset(models.Model):
    """
    Сохранённый фильтр доски канбана для конкретного пользователя и проекта.
    Хранит выбранного исполнителя и тип задачи.
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="kanban_filter_presets",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kanban_filter_presets",
    )
    name = models.CharField(max_length=100)
    assignee_id = models.IntegerField(null=True, blank=True)
    task_type = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user", "name")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.project}: {self.name}"


class TaskActivity(models.Model):
    """
    История изменений задачи: кто и что поменял.
    """

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="activities")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="task_activities",
    )
    action = models.CharField(max_length=64)
    field = models.CharField(max_length=64, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.task_id}: {self.action} {self.field}"


class TaskCheckpoint(models.Model):
    """
    Чекпоинты/этапы внутри задачи (для менеджера и исполнителя).
    Отображаются в карточке задачи на канбане.
    """

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="checkpoints")
    title = models.CharField("Заголовок", max_length=255)
    comment = models.TextField("Комментарий / детали", blank=True)
    is_done = models.BooleanField("Выполнен", default=False)
    order = models.PositiveIntegerField("Порядок", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"Task {self.task_id}: {self.title}"


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Комментарий к {self.task_id} от {self.author_id}"


class Attachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="attachments/%Y/%m/%d/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Файл {self.file.name}"


class Release(models.Model):
    """Версия / релиз: набор задач для поставки."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="releases")
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=64)
    released_at = models.DateField(null=True, blank=True)
    tasks = models.ManyToManyField(Task, blank=True, related_name="releases")

    class Meta:
        ordering = ["-released_at", "-id"]

    def __str__(self) -> str:
        return f"{self.project}: {self.version}"


class TaskLink(models.Model):
    class LinkType(models.TextChoices):
        BLOCKS = "blocks", "Блокирует"
        RELATES = "relates", "Связана с"
        DUPLICATES = "duplicates", "Дубликат"

    source = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="links_from")
    target = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="links_to")
    link_type = models.CharField(max_length=20, choices=LinkType.choices)

    class Meta:
        unique_together = ("source", "target", "link_type")

    def __str__(self) -> str:
        return f"{self.source_id} {self.get_link_type_display()} {self.target_id}"


class TaskWatcher(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="watchers_rel")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watched_tasks",
    )

    class Meta:
        unique_together = ("task", "user")

    def __str__(self) -> str:
        return f"{self.user_id} watches {self.task_id}"


class SprintRetrospective(models.Model):
    sprint = models.OneToOneField(Sprint, on_delete=models.CASCADE, related_name="retrospective")
    went_well = models.TextField("Что прошло хорошо", blank=True)
    to_improve = models.TextField("Что улучшить", blank=True)
    action_items = models.TextField("Действия", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Retro {self.sprint_id}"


class SprintBurndownSnapshot(models.Model):
    sprint = models.ForeignKey(Sprint, on_delete=models.CASCADE, related_name="burndown_snapshots")
    day = models.DateField()
    remaining_points = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("sprint", "day")
        ordering = ["day"]

    def __str__(self) -> str:
        return f"{self.sprint_id} {self.day}: {self.remaining_points}"


class InAppNotification(models.Model):
    """Внутриигровые уведомления (колокольчик в шапке)."""

    class Kind(models.TextChoices):
        TASK_COMMENT = "task_comment", "Комментарий в задаче"
        TASK_ASSIGNED = "task_assigned", "Назначена задача"
        TASK_UPDATED = "task_updated", "Задача изменена"
        TASK_STATUS_CHANGED = "task_status_changed", "Изменён этап задачи"
        CLIENT_MESSAGE = "client_message", "Сообщение от клиента в заявке"
        NEW_CLIENT_REQUEST = "new_client_request", "Новая заявка клиента"
        REQUEST_STAFF_MESSAGE = "request_staff_message", "Сообщение по заявке от команды"
        SPRINT_STARTED = "sprint_started", "Спринт активирован"
        SPRINT_COMPLETED = "sprint_completed", "Спринт завершён"
        NEW_OPEN_TASK = "new_open_task", "Свободная задача"
        EMPLOYEE_JOIN_PENDING = "employee_join_pending", "Заявка сотрудника на вступление"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="in_app_notifications",
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    link_url = models.CharField(max_length=500, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.kind} → {self.user_id}"


class Message(models.Model):
    request = models.ForeignKey(ClientRequest, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Сообщение {self.author_id} -> {self.request_id}"


class CompanyReview(models.Model):
    """Отзыв клиента о компании после завершения заявки (рейтинг 1–5)."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="reviews")
    client_request = models.OneToOneField(
        ClientRequest,
        on_delete=models.CASCADE,
        related_name="review",
        help_text="Один отзыв на завершённую заявку",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_reviews",
    )
    rating = models.PositiveSmallIntegerField("Оценка", help_text="От 1 до 5")
    text = models.TextField("Текст отзыва", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Отзыв о компании"
        verbose_name_plural = "Отзывы о компаниях"

    def __str__(self) -> str:
        return f"{self.company_id} ★{self.rating} от {self.client_id}"


# Create your models here.
