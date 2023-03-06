# Generated by Django 4.1.3 on 2023-02-28 17:24

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0013_remove_traderevenue_base_price'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assetprice',
            name='price',
            field=models.DecimalField(decimal_places=12, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='historicalassetprice',
            name='price',
            field=models.DecimalField(decimal_places=12, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]