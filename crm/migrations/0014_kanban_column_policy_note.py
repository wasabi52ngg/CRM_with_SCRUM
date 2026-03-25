from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0013_scrum_agile_features"),
    ]

    operations = [
        migrations.AddField(
            model_name="kanbancolumnconfig",
            name="policy_note",
            field=models.TextField(
                blank=True,
                help_text="Кто двигает карточки, что означает колонка (Kanban/Scrum)",
                verbose_name="Политика колонки",
            ),
        ),
    ]
