from django.contrib import admin

from .models import ClientRequest, Project, Sprint, Task, Comment, Attachment, Message


@admin.register(ClientRequest)
class ClientRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "project_type", "status", "manager", "created_at")
    list_filter = ("project_type", "status", "manager")
    search_fields = ("title", "description", "contact_email")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_archived", "created_at")
    list_filter = ("is_archived",)
    search_fields = ("name", "description")


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "project")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "task_type", "status", "assignee", "project", "created_at")
    list_filter = ("task_type", "status", "assignee")
    search_fields = ("title", "description")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("task", "author", "created_at")
    search_fields = ("text",)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("task", "file", "uploaded_by", "created_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("request", "author", "created_at")
    search_fields = ("text",)

# Register your models here.
