# Generated by Django 4.1.3 on 2023-02-08 14:58
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def populate_amounts(apps, schema_editor):
    OTCRequest = apps.get_model('ledger', 'OTCRequest')
    PairSymbol = apps.get_model('market', 'PairSymbol')

    symbols = list(PairSymbol.objects.select_for_update())
    symbols_dict = {(s.asset, s.base_asset): s for s in symbols}

    for o in OTCRequest.objects.all().prefetch_related('from_asset', 'to_asset'):
        from_asset = o.from_asset
        from_amount = o.from_amount

        to_asset = o.to_asset
        to_amount = o.to_amount

        if from_asset.symbol in ('IRT', 'USDT') and to_asset.symbol != 'IRT':
            side = 'buy'
            asset = to_asset
            base_asset = from_asset
            coin_amount = to_amount
            base_amount = from_amount
        else:
            side = 'sell'
            asset = from_asset
            base_asset = to_asset
            coin_amount = from_amount
            base_amount = to_amount

        if base_asset.symbol == 'IRT':
            o.base_irt_price = 1
            o.base_usdt_price = 1 / 35000
        else:
            o.base_irt_price = 35000
            o.base_usdt_price = 1

        o.symbol = symbols_dict[asset, base_asset]
        o.amount = coin_amount
        o.price = base_amount / coin_amount
        o.fee_amount = Decimal('0.002') * to_amount
        o.fee_usdt_value = o.fee_revenue = 0
        o.side = side

        o.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0102_historicaluser_first_crypto_deposit_date_and_more'),
        ('market', '0041_remove_trade_gap_revenue_remove_trade_hedge_price_and_more'),
        ('ledger', '0161_systemsnapshot_reserved'),
    ]

    operations = [
        migrations.AddField(
            model_name='otcrequest',
            name='amount',
            field=models.DecimalField(decimal_places=8, max_digits=30, null=True,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='otcrequest',
            name='base_irt_price',
            field=models.DecimalField(decimal_places=8,  null=True, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='otcrequest',
            name='base_usdt_price',
            field=models.DecimalField(decimal_places=8, null=True, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='otcrequest',
            name='fee_amount',
            field=models.DecimalField(decimal_places=8, null=True, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='otcrequest',
            name='fee_revenue',
            field=models.DecimalField(decimal_places=8, null=True, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='otcrequest',
            name='fee_usdt_value',
            field=models.DecimalField(decimal_places=8, null=True, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='otcrequest',
            name='price',
            field=models.DecimalField(decimal_places=8, null=True, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='otcrequest',
            name='side',
            field=models.CharField(choices=[('buy', 'buy'), ('sell', 'sell')], null=True, max_length=8),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='otcrequest',
            name='symbol',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='market.pairsymbol'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='otctrade',
            name='execution_type',
            field=models.CharField(choices=[('m', 'market'), ('p', 'provider')], default='p', max_length=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='otctrade',
            name='gap_revenue',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='otctrade',
            name='order_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),

        migrations.RunPython(populate_amounts, migrations.RunPython.noop),

        migrations.AlterField(
            model_name='otcrequest',
            name='amount',
            field=models.DecimalField(decimal_places=8, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='base_irt_price',
            field=models.DecimalField(decimal_places=8, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='base_usdt_price',
            field=models.DecimalField(decimal_places=8, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='fee_amount',
            field=models.DecimalField(decimal_places=8, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='fee_revenue',
            field=models.DecimalField(decimal_places=8, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='fee_usdt_value',
            field=models.DecimalField(decimal_places=8, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='price',
            field=models.DecimalField(decimal_places=8, max_digits=30,
                                      validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='side',
            field=models.CharField(choices=[('buy', 'buy'), ('sell', 'sell')], max_length=8),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='symbol',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='market.pairsymbol'),
            preserve_default=False,
        ),

        migrations.RemoveConstraint(
            model_name='otcrequest',
            name='check_ledger_otc_request_amounts',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='max_trade_quantity',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='min_trade_quantity',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='trade_quantity_step',
        ),
        migrations.RemoveField(
            model_name='otcrequest',
            name='to_price',
        ),
        migrations.RemoveField(
            model_name='otcrequest',
            name='to_price_absolute_irt',
        ),
        migrations.RemoveField(
            model_name='otcrequest',
            name='to_price_absolute_usdt',
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.account'),
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='from_amount',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=30, null=True, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='market',
            field=models.CharField(choices=[('spot', 'spot'), ('margin', 'margin'), ('loan', 'loan'), ('stake', 'stake'), ('voucher', 'voucher'), ('debt', 'debt')], max_length=8),
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='to_amount',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=30, null=True, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='otctrade',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='otctrade',
            name='status',
            field=models.CharField(choices=[('pending', 'pending'), ('canceled', 'canceled'), ('done', 'done'), ('revert', 'revert')], default='pending', max_length=8),
        ),
        migrations.AddConstraint(
            model_name='otcrequest',
            constraint=models.CheckConstraint(check=models.Q(('from_amount__gte', 0), ('to_amount__gte', 0)), name='check_ledger_otc_request_amounts'),
        ),
        migrations.AddConstraint(
            model_name='otcrequest',
            constraint=models.CheckConstraint(check=models.Q(('amount__gte', 0), ('fee_amount__gte', 0), ('price__gte', 0)), name='otc_request_check_trade_amounts'),
        ),
    ]
