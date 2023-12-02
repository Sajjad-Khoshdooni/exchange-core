# Generated by Django 4.1.3 on 2023-08-20 12:23

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0052_cancelrequest_login_activity_order_login_activity_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pairsymbol',
            name='step_size',
            field=models.PositiveSmallIntegerField(default=4, validators=[django.core.validators.MaxValueValidator(8)]),
        ),
        migrations.AlterField(
            model_name='pairsymbol',
            name='tick_size',
            field=models.PositiveSmallIntegerField(default=2, validators=[django.core.validators.MaxValueValidator(8)]),
        ),
    ]
