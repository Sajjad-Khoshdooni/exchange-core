# Generated by Django 4.1.3 on 2023-12-11 06:43

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0236_merge_20231207_1753'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='margin_interest_fee',
            field=models.DecimalField(decimal_places=8, default=Decimal('0.00015'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]
