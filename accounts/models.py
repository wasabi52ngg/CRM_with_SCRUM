from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "client", "Клиент"
        MANAGER = "manager", "Менеджер проектов"
        DEVELOPER = "developer", "Разработчик"

    class DeveloperType(models.TextChoices):
        NONE = "none", "Не задано"
        FRONTEND = "frontend", "Фронтенд"
        BACKEND = "backend", "Бэкенд"
        FULLSTACK = "fullstack", "Фулстек"
        DEVOPS = "devops", "DevOps"
        QA = "qa", "Тестировщик"
        ANDROID = "android", "Android"
        DB = "db", "Разработчик БД"

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
        help_text="Тип разработчика, актуально для роли 'Разработчик'",
    )

    def is_manager(self) -> bool:
        return self.role == self.Role.MANAGER

    def is_developer(self) -> bool:
        return self.role == self.Role.DEVELOPER

    def is_client(self) -> bool:
        return self.role == self.Role.CLIENT

    def save(self, *args, **kwargs):
        # Если не разработчик, то обнуляем developer_type
        if self.role != self.Role.DEVELOPER:
            self.developer_type = self.DeveloperType.NONE
        super().save(*args, **kwargs)


# Create your models here.
