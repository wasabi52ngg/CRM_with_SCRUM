from django.db import models
from django.conf import settings


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
    client_request = models.OneToOneField(ClientRequest, on_delete=models.CASCADE, related_name="project")
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
