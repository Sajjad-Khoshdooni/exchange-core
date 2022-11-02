# Generated by Django 4.0 on 2022-08-18 06:47

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0120_alter_coincategory_coins'),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True, unique=True)),
                ('usdt_price', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('total', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('users', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('exchange', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('exchange_potential', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('binance_futures', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('binance_spot', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('internal', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('fiat_gateway', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('investment', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('cash', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('margin_insurance', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('margin_futures_initial_margin', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('margin_futures_maintenance_margin', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
            ],
        ),
        migrations.CreateModel(
            name='AssetSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True, unique=True)),
                ('price', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('hedge_amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('hedge_value', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('calc_hedge_amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('total_amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('users_amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('provider_amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('internal_amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('investment_amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('cash_amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ledger.asset')),
            ],
        ),
    ]