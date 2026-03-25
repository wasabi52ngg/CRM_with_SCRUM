# Generated manually for Scrum/Agile features

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_issue_numbers_and_backlog(apps, schema_editor):
    Task = apps.get_model("crm", "Task")
    Project = apps.get_model("crm", "Project")
    for proj in Project.objects.all():
        tasks = Task.objects.filter(project=proj).order_by("id")
        for i, t in enumerate(tasks, start=1):
            Task.objects.filter(pk=t.pk).update(issue_number=i)
        backlog = Task.objects.filter(project=proj, sprint__isnull=True, parent__isnull=True).order_by(
            "id"
        )
        for i, t in enumerate(backlog):
            Task.objects.filter(pk=t.pk).update(backlog_rank=i * 10)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0012_taskactivity_kanbanfilterpreset"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Epic",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("color", models.CharField(default="#6366f1", max_length=7)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="epics",
                        to="crm.project",
                    ),
                ),
            ],
            options={
                "ordering": ["order", "id"],
            },
        ),
        migrations.AddField(
            model_name="project",
            name="definition_of_done",
            field=models.TextField(
                blank=True,
                help_text="Общие критерии готовности для задач проекта (Scrum)",
                verbose_name="Definition of Done",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="issue_key_prefix",
            field=models.CharField(
                default="PRJ",
                help_text="Например PRJ для ключа PRJ-12",
                max_length=16,
                verbose_name="Префикс ключа задачи",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="product_owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="owned_projects",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Product Owner",
            ),
        ),
        migrations.AddField(
            model_name="project",
            name="scrum_master",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="scrummaster_projects",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Scrum Master",
            ),
        ),
        migrations.AddField(
            model_name="sprint",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sprint",
            name="goal",
            field=models.TextField(blank=True, verbose_name="Цель спринта"),
        ),
        migrations.AlterModelOptions(
            name="sprint",
            options={"ordering": ["-start_date", "-id"]},
        ),
        migrations.AddField(
            model_name="task",
            name="acceptance_criteria",
            field=models.TextField(blank=True, verbose_name="Критерии приёмки"),
        ),
        migrations.AddField(
            model_name="task",
            name="backlog_rank",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Порядок в Product Backlog (меньше — выше в списке)",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="issue_number",
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="priority",
            field=models.CharField(
                choices=[
                    ("low", "Низкий"),
                    ("medium", "Средний"),
                    ("high", "Высокий"),
                    ("critical", "Критический"),
                ],
                default="medium",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="work_item_type",
            field=models.CharField(
                choices=[
                    ("story", "User Story"),
                    ("bug", "Баг"),
                    ("task", "Задача"),
                    ("subtask", "Подзадача"),
                ],
                default="task",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="epic",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tasks",
                to="crm.epic",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="children",
                to="crm.task",
            ),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["project", "issue_number"], name="crm_task_proj_issue_idx"),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["project", "backlog_rank"], name="crm_task_proj_bkrank_idx"),
        ),
        migrations.CreateModel(
            name="Release",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("version", models.CharField(max_length=64)),
                ("released_at", models.DateField(blank=True, null=True)),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="releases",
                        to="crm.project",
                    ),
                ),
                (
                    "tasks",
                    models.ManyToManyField(blank=True, related_name="releases", to="crm.task"),
                ),
            ],
            options={
                "ordering": ["-released_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="TaskLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "link_type",
                    models.CharField(
                        choices=[
                            ("blocks", "Блокирует"),
                            ("relates", "Связана с"),
                            ("duplicates", "Дубликат"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="links_from",
                        to="crm.task",
                    ),
                ),
                (
                    "target",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="links_to",
                        to="crm.task",
                    ),
                ),
            ],
            options={
                "unique_together": {("source", "target", "link_type")},
            },
        ),
        migrations.CreateModel(
            name="TaskWatcher",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="watchers_rel",
                        to="crm.task",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="watched_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("task", "user")},
            },
        ),
        migrations.CreateModel(
            name="SprintRetrospective",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("went_well", models.TextField(blank=True, verbose_name="Что прошло хорошо")),
                ("to_improve", models.TextField(blank=True, verbose_name="Что улучшить")),
                ("action_items", models.TextField(blank=True, verbose_name="Действия")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "sprint",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="retrospective",
                        to="crm.sprint",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SprintBurndownSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("day", models.DateField()),
                ("remaining_points", models.PositiveIntegerField(default=0)),
                (
                    "sprint",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="burndown_snapshots",
                        to="crm.sprint",
                    ),
                ),
            ],
            options={
                "ordering": ["day"],
                "unique_together": {("sprint", "day")},
            },
        ),
        migrations.RunPython(populate_issue_numbers_and_backlog, noop_reverse),
    ]
