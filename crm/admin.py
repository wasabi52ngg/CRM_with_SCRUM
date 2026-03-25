from django.contrib import admin

from .models import (
    Company,
    CompanyMembership,
    ClientRequest,
    Project,
    Sprint,
    Task,
    Comment,
    Attachment,
    Message,
    Epic,
    Release,
    TaskLink,
    TaskWatcher,
    SprintRetrospective,
    SprintBurndownSnapshot,
    InAppNotification,
)


@admin.register(ClientRequest)
class ClientRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "project_type", "status", "manager", "created_at")
    list_filter = ("project_type", "status", "manager")
    search_fields = ("title", "description", "contact_email")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_archived", "issue_key_prefix", "created_at")
    list_filter = ("is_archived",)
    search_fields = ("name", "description")


@admin.register(Epic)
class EpicAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "order")
    list_filter = ("project",)


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "project", "released_at")
    list_filter = ("project",)
    filter_horizontal = ("tasks",)


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "start_date", "end_date", "is_active", "completed_at")
    list_filter = ("is_active", "project")


@admin.register(SprintRetrospective)
class SprintRetrospectiveAdmin(admin.ModelAdmin):
    list_display = ("sprint", "updated_at")


@admin.register(SprintBurndownSnapshot)
class SprintBurndownSnapshotAdmin(admin.ModelAdmin):
    list_display = ("sprint", "day", "remaining_points")


@admin.register(TaskLink)
class TaskLinkAdmin(admin.ModelAdmin):
    list_display = ("source", "link_type", "target")


@admin.register(TaskWatcher)
class TaskWatcherAdmin(admin.ModelAdmin):
    list_display = ("task", "user")


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


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "join_code", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_token", "join_code", "created_at", "updated_at")


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "is_owner", "is_manager", "is_developer", "is_approved", "created_at")
    list_filter = ("is_owner", "is_manager", "is_developer", "is_approved", "company", "created_at")
    search_fields = ("user__username", "user__email", "company__name")
    list_editable = ("is_manager", "is_developer", "is_approved")
    readonly_fields = ("created_at", "is_owner")  # is_owner нельзя редактировать напрямую, только через создание компании


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "kind", "read_at", "created_at")
    list_filter = ("kind", "read_at")
    search_fields = ("title", "body", "user__username")
    readonly_fields = ("created_at",)

# Register your models here.
