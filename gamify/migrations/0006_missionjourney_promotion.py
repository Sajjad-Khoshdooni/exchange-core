# Generated by Django 4.0 on 2022-10-09 09:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gamify', '0005_remove_achievement_scope'),
    ]

    operations = [
        migrations.AddField(
            model_name='missionjourney',
            name='promotion',
            field=models.CharField(choices=[('default', 'default'), ('voucher', 'voucher')], default='default', max_length=8, unique=True),
            preserve_default=False,
        ),
    ]