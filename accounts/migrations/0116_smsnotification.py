# Generated by Django 4.1.3 on 2023-05-09 09:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0115_merge_20230507_1408'),
    ]

    operations = [
        migrations.CreateModel(
            name='SmsNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('template', models.CharField(max_length=32)),
                ('data', models.JSONField(blank=True, null=True)),
                ('sent', models.BooleanField(db_index=True, default=False)),
                ('group_id', models.UUIDField(blank=True, db_index=True, default=None, null=True)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created',),
                'unique_together': {('recipient', 'group_id')},
            },
        ),
    ]
