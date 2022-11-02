# Generated by Django 4.0 on 2022-09-18 11:36

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stake', '0005_alter_stakerequest_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='stakeoption',
            name='fee',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
    ]