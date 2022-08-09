# Generated by Django 4.0 on 2022-08-09 05:36

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('provider', '0014_merge_20220731_1006'),
    ]

    operations = [
        migrations.AddField(
            model_name='binancewallet',
            name='usdt_value',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
