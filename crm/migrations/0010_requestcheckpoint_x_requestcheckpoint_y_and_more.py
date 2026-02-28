# Generated manually for diagram editor

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0009_remove_companymembership_role_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='requestcheckpoint',
            name='x',
            field=models.IntegerField(default=0, verbose_name='Позиция X на диаграмме'),
        ),
        migrations.AddField(
            model_name='requestcheckpoint',
            name='y',
            field=models.IntegerField(default=0, verbose_name='Позиция Y на диаграмме'),
        ),
        migrations.CreateModel(
            name='RequestCheckpointEdge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='checkpoint_edges', to='crm.clientrequest')),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outgoing_edges', to='crm.requestcheckpoint')),
                ('target', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incoming_edges', to='crm.requestcheckpoint')),
            ],
            options={
                'ordering': ['id'],
                'unique_together': {('request', 'source', 'target')},
            },
        ),
    ]
