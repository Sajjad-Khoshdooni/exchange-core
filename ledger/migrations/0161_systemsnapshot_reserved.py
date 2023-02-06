# Generated by Django 4.1.3 on 2023-01-30 11:25

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0160_alter_assetsnapshot_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemsnapshot',
            name='reserved',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
    ]