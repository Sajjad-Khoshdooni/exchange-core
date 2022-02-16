from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum

from accounts.models import Account
from ledger.models import Trx, Asset
from ledger.utils.price import SELL, get_prices_dict, get_tether_irt_price
from provider.exchanges import BinanceFuturesHandler, BinanceSpotHandler


def get_user_type_asset_balances():

    received = Trx.objects.values('receiver__account__type', 'receiver__asset__symbol').annotate(amount=Sum('amount'))
    sent = Trx.objects.values('sender__account__type', 'sender__asset__symbol').annotate(amount=Sum('amount'))

    received_dict = {(r['receiver__account__type'], r['receiver__asset__symbol']): r['amount'] for r in received}
    sent_dict = {(r['sender__account__type'], r['sender__asset__symbol']): r['amount'] for r in sent}

    keys = set(received_dict.keys()) | set(sent_dict.keys())
    total_dict = {}

    for key in keys:
        total_dict[key] = received_dict.get(key, 0) - sent_dict.get(key, 0)

    return total_dict


class AssetOverview:
    def __init__(self):
        self._future = BinanceFuturesHandler.get_account_details()

        self._future_positions = {
            pos['symbol']: pos for pos in self._future['positions']
        }

        self._user_type_asset_balances = get_user_type_asset_balances()

        self._user_type_balances = defaultdict(int)
        for key, amount in self._user_type_asset_balances.items():
            self._user_type_balances[key[0]] += amount

        self._prices = get_prices_dict(
            coins=list(Asset.objects.all().values_list('symbol', flat=True)),
            side=SELL
        )

        self._usdt_irt = get_tether_irt_price(SELL)

        balances_list = BinanceSpotHandler.get_account_details()['balances']
        self._binance_spot_balance_map = {b['asset']: float(b['free']) for b in balances_list}


    @property
    def total_initial_margin(self):
        return float(self._future['totalInitialMargin'])

    @property
    def total_maintenance_margin(self):
        return float(self._future['totalMaintMargin'])

    @property
    def total_margin_balance(self):
        return float(self._future['totalMarginBalance'])

    @property
    def margin_ratio(self):
        return self.total_margin_balance / max(self.total_maintenance_margin, 1e-10)

    def get_balance(self, user_type: str, asset: Asset = None):
        if asset:
            return self._user_type_asset_balances.get((user_type, asset.symbol), 0)
        else:
            return self._user_type_balances[user_type]

    def get_future_position_amount(self, asset: Asset):
        amount = float(self._future_positions.get(asset.future_symbol + 'USDT', {}).get('positionAmt', 0))

        if asset.symbol == Asset.SHIB:
            amount *= 1000

        return amount

    def get_future_position_value(self, asset: Asset):
        return float(self._future_positions.get(asset.future_symbol + 'USDT', {}).get('notional', 0))

    def get_hedge_amount(self, asset: Asset):
        if asset.symbol in (Asset.IRT, Asset.USDT):
            return 0

        balance = self.get_balance(Account.SYSTEM, asset)
        future_amount = Decimal(self.get_future_position_amount(asset))
        return future_amount + balance

    def get_hedge_value(self, asset: Asset):
        price = self._prices.get(asset.symbol, 0)

        return Decimal(self.get_hedge_amount(asset)) * price

    def get_total_hedge_value(self):
        return sum([
            self.get_hedge_value(asset) for asset in Asset.objects.all()
        ])

    def get_binance_spot_amount(self, asset: Asset):
        return self._binance_spot_balance_map.get(asset.symbol, 0)
