# Generated by Django 4.1.3 on 2024-02-08 15:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0182_alter_bulknotification_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalsystemconfig',
            name='default_max_allowed_coin_network_daily_deposit_value',
            field=models.PositiveSmallIntegerField(default=300),
        ),
        migrations.AddField(
            model_name='systemconfig',
            name='default_max_allowed_coin_network_daily_deposit_value',
            field=models.PositiveSmallIntegerField(default=300),
        ),
    ]
