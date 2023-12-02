# Generated by Django 4.1.3 on 2023-06-20 06:43

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0129_userfeatureperm'),
    ]

    operations = [
        migrations.AddField(
            model_name='userfeatureperm',
            name='limit',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=30, null=True, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='userfeatureperm',
            name='feature',
            field=models.CharField(choices=[('pay_id', 'pay_id'), ('fiat_deposit_limit', 'fiat_deposit_limit')], max_length=32),
        ),
    ]
