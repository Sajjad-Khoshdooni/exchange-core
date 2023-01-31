# Generated by Django 4.1.3 on 2023-01-30 10:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0006_historicalvault'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalreservedasset',
            name='value_irt',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='historicalreservedasset',
            name='value_usdt',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='reservedasset',
            name='value_irt',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='reservedasset',
            name='value_usdt',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30),
            preserve_default=False,
        ),
    ]
