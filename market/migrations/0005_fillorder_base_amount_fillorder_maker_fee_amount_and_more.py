# Generated by Django 4.0 on 2022-03-16 05:57

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0004_alter_pairsymbol_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='fillorder',
            name='base_amount',
            field=models.DecimalField(decimal_places=18, default=0, max_digits=40, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='fillorder',
            name='maker_fee_amount',
            field=models.DecimalField(decimal_places=18, default=0, max_digits=40, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='fillorder',
            name='taker_fee_amount',
            field=models.DecimalField(decimal_places=18, default=0, max_digits=40, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
    ]