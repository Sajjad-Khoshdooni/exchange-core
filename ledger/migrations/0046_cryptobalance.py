# Generated by Django 4.0 on 2022-02-08 14:17

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0045_alter_trx_scope'),
    ]

    operations = [
        migrations.CreateModel(
            name='CryptoBalance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=18, default=Decimal('0'), max_digits=40, validators=[django.core.validators.MinValueValidator(0)])),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ledger.asset')),
                ('deposit_address', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ledger.depositaddress')),
            ],
            options={
                'unique_together': {('deposit_address', 'asset')},
            },
        ),
    ]