# Generated by Django 4.1.3 on 2023-07-30 11:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gamify', '0017_alter_missionjourney_promotion'),
    ]

    operations = [
        migrations.AddField(
            model_name='usermission',
            name='finished',
            field=models.BooleanField(default=False),
        ),
    ]