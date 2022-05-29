# Generated by Django 4.0 on 2022-05-29 13:15

from django.db import migrations, models
import uuid


def populate_chat_uuid(apps, schema_editor):
    User = apps.get_model('accounts', 'User')

    users = User.objects.all()
    for u in users:
        u.chat_uuid = uuid.uuid4()

    User.objects.bulk_update(users, fields=['chat_uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0055_account_bookmark_assets'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaluser',
            name='chat_uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AddField(
            model_name='user',
            name='chat_uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.RunPython(
            populate_chat_uuid, migrations.RunPython.noop
        )
    ]
