# Generated by Django 4.1.3 on 2023-07-22 11:44

from decimal import Decimal
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0138_merge_20230711_1255'),
        ('ledger', '0190_merge_20230711_1138'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalTransfer',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('created', models.DateTimeField(blank=True, editable=False)),
                ('accepted_datetime', models.DateTimeField(blank=True, editable=False, null=True)),
                ('finished_datetime', models.DateTimeField(blank=True, null=True)),
                ('group_id', models.UUIDField(db_index=True, default=uuid.uuid4)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('fee_amount', models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('deposit', models.BooleanField()),
                ('status', models.CharField(choices=[('init', 'init'), ('process', 'process'), ('pending', 'pending'), ('canceled', 'canceled'), ('done', 'done')], db_index=True, default='process', max_length=8)),
                ('trx_hash', models.CharField(blank=True, db_index=True, max_length=128, null=True)),
                ('out_address', models.CharField(max_length=256)),
                ('memo', models.CharField(blank=True, max_length=64)),
                ('source', models.CharField(choices=[('self', 'self'), ('internal', 'internal'), ('provider', 'provider'), ('manual', 'manual')], default='self', max_length=8)),
                ('irt_value', models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('usdt_value', models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('comment', models.TextField(blank=True, verbose_name='نظر')),
                ('risks', models.JSONField(blank=True, null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('address_book', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='ledger.addressbook')),
                ('deposit_address', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='ledger.depositaddress')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('login_activity', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='accounts.loginactivity')),
                ('network', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='ledger.network')),
                ('wallet', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='ledger.wallet')),
            ],
            options={
                'verbose_name': 'historical transfer',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
