# Generated by Django 4.1.3 on 2023-02-09 13:57

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
        ('ledger', '0162_remove_otcrequest_check_ledger_otc_request_amounts_and_more'),
    ]

    operations = [
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
    ]
