# Generated by Django 4.0 on 2022-10-04 12:29

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0138_transfer_irt_value_transfer_usdt_value'),
        ('gamify', '0002_mission_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='achievement',
            name='amount',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='achievement',
            name='asset',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='ledger.asset'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='achievement',
            name='voucher',
            field=models.BooleanField(default=False),
        ),
    ]