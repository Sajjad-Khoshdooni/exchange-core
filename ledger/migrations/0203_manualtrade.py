# Generated by Django 4.1.3 on 2023-08-14 11:43

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0139_alter_notification_unique_together_and_more'),
        ('ledger', '0201_alter_wallet_variant'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManualTrade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('group_id', models.UUIDField(default=uuid.uuid4)),
                ('side', models.CharField(choices=[('buy', 'buy'), ('sell', 'sell')], default='buy', max_length=8)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('price', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('filled_price', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('status', models.CharField(choices=[('process', 'در حال پردازش'), ('pending', 'در انتظار تایید'), ('canceled', 'لغو شده'), ('done', 'انجام شده')], default='pending', max_length=8)),
                ('account', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.account')),
            ],
        ),
    ]
