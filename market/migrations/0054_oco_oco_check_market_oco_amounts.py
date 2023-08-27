# Generated by Django 4.1.3 on 2023-08-27 13:18

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0212_historicaltransfer_accepted_by_transfer_accepted_by'),
        ('accounts', '0141_merge_20230822_1235'),
        ('market', '0053_alter_pairsymbol_step_size_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='OCO',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('filled_amount', models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('stop_loss_price', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('stop_loss_trigger_price', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('price', models.DecimalField(blank=True, decimal_places=8, max_digits=30, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('side', models.CharField(choices=[('buy', 'buy'), ('sell', 'sell')], max_length=8)),
                ('canceled_at', models.DateTimeField(blank=True, null=True)),
                ('group_id', models.UUIDField(default=uuid.uuid4)),
                ('login_activity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.loginactivity')),
                ('symbol', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='market.pairsymbol')),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='oco_set', to='ledger.wallet')),
            ],
        ),
        migrations.AddConstraint(
            model_name='oco',
            constraint=models.CheckConstraint(check=models.Q(('amount__gte', 0), ('filled_amount__gte', 0), ('price__gte', 0)), name='check_market_OCO_amounts'),
        ),
    ]
