# Generated by Django 4.1.3 on 2024-02-15 12:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0184_alter_userfeatureperm_feature'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalsystemconfig',
            name='fiat_daily_auto_verify_limit',
            field=models.PositiveIntegerField(default=200000000),
        ),
        migrations.AddField(
            model_name='systemconfig',
            name='fiat_daily_auto_verify_limit',
            field=models.PositiveIntegerField(default=200000000),
        ),
    ]
