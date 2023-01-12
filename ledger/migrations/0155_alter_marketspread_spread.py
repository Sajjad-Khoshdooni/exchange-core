# Generated by Django 4.1.3 on 2023-01-09 21:10

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0154_marketspread'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketspread',
            name='spread',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(15)]),
        ),
    ]