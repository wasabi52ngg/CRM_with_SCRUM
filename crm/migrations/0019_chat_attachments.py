from django.db import migrations, models

import crm.chat_attachments


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0018_taskcheckpoint_created_by"),
    ]

    operations = [
        migrations.AlterField(
            model_name="comment",
            name="text",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="comment",
            name="attachment",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=crm.chat_attachments.task_comment_upload_to,
                verbose_name="Вложение",
            ),
        ),
        migrations.AlterField(
            model_name="message",
            name="text",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="message",
            name="attachment",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=crm.chat_attachments.request_message_upload_to,
                verbose_name="Вложение",
            ),
        ),
    ]
