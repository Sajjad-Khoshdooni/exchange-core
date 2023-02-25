# Generated by Django 4.1.3 on 2023-02-23 16:16

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0172_alter_wallet_market'),
    ]

    operations = [
        migrations.AlterField(
            model_name='categoryspread',
            name='step',
            field=models.PositiveIntegerField(choices=[(1, '0$ - 3$'), (2, '3$ - 10$'), (3, '10$ - 1000$'), (4, '1000$ - 2000$'), (5, '> 2000$')], validators=[django.core.validators.MinValueValidator(-5), django.core.validators.MaxValueValidator(10)]),
        ),
        migrations.AlterField(
            model_name='marketspread',
            name='spread',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(-5), django.core.validators.MaxValueValidator(10)]),
        ),
    ]