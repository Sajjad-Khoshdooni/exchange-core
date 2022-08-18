from django.db import models

from ledger.utils.fields import get_amount_field


class AssetSnapshot(models.Model):
    created = models.DateTimeField(auto_now_add=True, unique=True, db_index=True)
    asset = models.ForeignKey('ledger.Asset', on_delete=models.CASCADE)

    price = get_amount_field()
    hedge_amount = get_amount_field()
    hedge_value = get_amount_field()
    calc_hedge_amount = get_amount_field()

    total_amount = get_amount_field()
    users_amount = get_amount_field()

    provider_amount = get_amount_field()
    internal_amount = get_amount_field()
    investment_amount = get_amount_field()
    cash_amount = get_amount_field()


class SystemSnapshot(models.Model):
    created = models.DateTimeField(auto_now_add=True, unique=True, db_index=True)

    usdt_price = get_amount_field()

    total = get_amount_field()
    users = get_amount_field()
    exchange = get_amount_field()
    exchange_potential = get_amount_field()

    binance_futures = get_amount_field()
    binance_spot = get_amount_field()
    internal = get_amount_field()
    fiat_gateway = get_amount_field()
    investment = get_amount_field()
    cash = get_amount_field()
    margin_insurance = get_amount_field()

    margin_futures_initial_margin = get_amount_field()
    margin_futures_maintenance_margin = get_amount_field()
