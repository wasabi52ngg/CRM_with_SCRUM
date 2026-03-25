# Generated manually for CompanyReview

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("crm", "0015_inappnotification"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyReview",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField(help_text="От 1 до 5", verbose_name="Оценка")),
                ("text", models.TextField(blank=True, verbose_name="Текст отзыва")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="company_reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "client_request",
                    models.OneToOneField(
                        help_text="Один отзыв на завершённую заявку",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="review",
                        to="crm.clientrequest",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews",
                        to="crm.company",
                    ),
                ),
            ],
            options={
                "verbose_name": "Отзыв о компании",
                "verbose_name_plural": "Отзывы о компаниях",
                "ordering": ["-created_at"],
            },
        ),
    ]
