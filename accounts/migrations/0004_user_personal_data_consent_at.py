# Generated manually for personal_data_consent_at

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_user_developer_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='personal_data_consent_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Дата и время получения согласия на обработку персональных данных (152-ФЗ)',
                null=True,
                verbose_name='Согласие на обработку ПДн',
            ),
        ),
    ]
