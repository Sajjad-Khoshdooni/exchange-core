# Generated by Django 4.0 on 2022-08-03 08:07

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0030_alter_order_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pairsymbol',
            name='taker_fee',
            field=models.DecimalField(decimal_places=8, default=Decimal('0.002'), max_digits=9),
        ),
    ]
