# Generated by Django 4.0 on 2022-03-28 09:23

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0065_alter_asset_ask_diff_alter_asset_bid_diff'),
    ]

    operations = [
        migrations.AddField(
            model_name='otcrequest',
            name='to_price_absolute_usdt',
            field=models.DecimalField(decimal_places=18, default=0, max_digits=40, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
    ]