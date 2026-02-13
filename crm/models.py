from django.db import models
from django.conf import settings
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
    Это основа мульти‑тенантной модели (несколько компаний в одной системе).
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Владелец организации"
        PRODUCT_OWNER = "product_owner", "Владелец продукта"
        SCRUM_MASTER = "scrum_master", "Scrum-мастер"
        MANAGER = "manager", "Менеджер проектов"
        DEVELOPER = "developer", "Разработчик"

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
    role = models.CharField(
        "Роль в компании",
        max_length=32,
        choices=Role.choices,
        default=Role.DEVELOPER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Участник компании"
        verbose_name_plural = "Участники компаний"
        unique_together = ("company", "user")

    def __str__(self) -> str:
        return f"{self.user} @ {self.company} ({self.get_role_display()})"


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class RequestCheckpoint(models.Model):
    """
    Этапы обработки заявки менеджером, отображаются как чекпоинты на таймлайне.
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"{self.request_id}: {self.title}"


class Sprint(models.Model):
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='sprints')
    name = models.CharField(max_length=255)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

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

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    sprint = models.ForeignKey(Sprint, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=20, choices=TaskType.choices)
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
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    starts_after_task = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='unblocks'
    )

    def __str__(self) -> str:
        return f"[{self.get_task_type_display()}] {self.title}"


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


class Message(models.Model):
    request = models.ForeignKey(ClientRequest, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Сообщение {self.author_id} -> {self.request_id}"


# Create your models here.
