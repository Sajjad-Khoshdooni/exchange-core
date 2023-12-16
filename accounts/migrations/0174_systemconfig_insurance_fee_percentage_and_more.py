# Generated by Django 4.1.3 on 2023-12-16 13:52

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0173_merge_20231214_0934'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemconfig',
            name='insurance_fee_percentage',
            field=models.DecimalField(decimal_places=8, default=Decimal('0.02'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='systemconfig',
            name='liquidation_level',
            field=models.DecimalField(decimal_places=8, default=Decimal('1.1'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='systemconfig',
            name='mean_leverage',
            field=models.DecimalField(decimal_places=8, default=Decimal('3'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
