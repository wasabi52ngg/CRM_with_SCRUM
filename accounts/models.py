from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from .validators import validate_email, validate_phone_number


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "client", "Клиент"
        MANAGER = "manager", "Менеджер проектов"
        DEVELOPER = "developer", "Разработчик"

    class DeveloperType(models.TextChoices):
        NONE = "none", "Профиль не указан"
        FRONTEND = "frontend", "Фронтенд"
        BACKEND = "backend", "Бэкенд"
        FULLSTACK = "fullstack", "Фулстек"
        DEVOPS = "devops", "DevOps"
        QA = "qa", "Тестировщик"
        ANDROID = "android", "Android"
        DB = "db", "Разработчик БД"

    def user_directory_path(self, filename):
        return f"users/{slugify(self.username)}/{filename}"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
        help_text="Роль пользователя в системе",
    )

    developer_type = models.CharField(
        max_length=20,
        choices=DeveloperType.choices,
        default=DeveloperType.NONE,
        help_text="Профиль разработчика, актуально для роли 'Разработчик'",
    )

    phone = models.CharField(
        verbose_name='Телефон',
        max_length=20,
        null=False,
        blank=False,
        validators=[validate_phone_number]
    )

    photo = models.ImageField(
        verbose_name='Фото',
        upload_to=user_directory_path,
        default=None,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время создания"
    )

    def is_manager(self) -> bool:
        return self.role == self.Role.MANAGER

    def is_developer(self) -> bool:
        return self.role == self.Role.DEVELOPER

    def is_client(self) -> bool:
        return self.role == self.Role.CLIENT

    def save(self, *args, **kwargs):
        # Обнуляем developer_type только если пользователь не разработчик (ни по роли, ни в компании)
        # ВАЖНО: для нового пользователя (ещё без pk) нельзя обращаться к reverse relation менеджерам,
        # иначе Django выбросит:
        # "'User' instance needs to have a primary key value before this relationship can be used."
        if self.pk:
            is_dev_in_company = self.company_memberships.filter(
                is_approved=True, is_developer=True
            ).exists()
        else:
            is_dev_in_company = False
        if self.role != self.Role.DEVELOPER and not is_dev_in_company:
            self.developer_type = self.DeveloperType.NONE
        super().save(*args, **kwargs)


# Create your models here.
