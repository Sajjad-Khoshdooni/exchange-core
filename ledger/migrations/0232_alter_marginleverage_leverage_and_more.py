# Generated by Django 4.1.3 on 2023-12-26 09:22

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0231_marginhistorymodel_marginleverage_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marginleverage',
            name='leverage',
            field=models.PositiveSmallIntegerField(default=3, validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name='marginposition',
            name='leverage',
            field=models.PositiveSmallIntegerField(),
        ),
    ]