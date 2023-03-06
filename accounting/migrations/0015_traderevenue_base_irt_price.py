# Generated by Django 4.1.3 on 2023-03-01 08:11

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0014_alter_assetprice_price_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='traderevenue',
            name='base_irt_price',
            field=models.DecimalField(decimal_places=8, default=1, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
    ]