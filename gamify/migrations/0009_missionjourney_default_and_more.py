# Generated by Django 4.0 on 2022-11-17 15:33

from django.db import migrations, models


def change_user_promotions(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    MissionJourney = apps.get_model('gamify', 'MissionJourney')

    MissionJourney.objects.filter(promotion='default').update(promotion='shib')
    User.objects.exclude(promotion='voucher').update(promotion='true')


class Migration(migrations.Migration):

    dependencies = [
        ('gamify', '0008_alter_task_app_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='missionjourney',
            name='default',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='missionjourney',
            name='promotion',
            field=models.CharField(choices=[('shib', 'shib'), ('voucher', 'voucher')], max_length=8, unique=True),
        ),
        migrations.RunPython(
            code=change_user_promotions, reverse_code=migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name='missionjourney',
            name='promotion',
            field=models.CharField(choices=[('true', 'true'), ('voucher', 'voucher')], max_length=8, unique=True),
        ),
    ]
