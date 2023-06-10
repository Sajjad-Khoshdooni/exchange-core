# Generated by Django 4.1.3 on 2023-05-18 10:33

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0179_alter_assetsnapshot_created_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsnapshot',
            name='binance_margin_ratio',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='systemsnapshot',
            name='cum_hedge',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
    ]
