# Generated by Django 4.1.3 on 2023-01-09 20:51

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0153_alter_closerequest_reason'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketSpread',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('side', models.CharField(choices=[('buy', 'bid'), ('sell', 'ask')], max_length=8)),
                ('step', models.PositiveIntegerField(choices=[(1, '0$ - 3$'), (2, '3$ - 10$'), (3, '10$ - 1000$'), (4, '1000$ - 2000$'), (5, '> 2000$')], validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ('spread', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(Decimal('0.1')), django.core.validators.MaxValueValidator(15)])),
            ],
        ),
    ]