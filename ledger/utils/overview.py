from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum

from accounts.models import Account
from ledger.models import Trx, Asset, CryptoBalance
from ledger.utils.price import SELL, get_prices_dict, get_tether_irt_price, get_binance_trading_symbol
from provider.exchanges import BinanceFuturesHandler, BinanceSpotHandler


def get_ledger_user_type_asset_balances():

    received = Trx.objects.values('receiver__account__type', 'receiver__asset__symbol').annotate(amount=Sum('amount'))
    sent = Trx.objects.values('sender__account__type', 'sender__asset__symbol').annotate(amount=Sum('amount'))

    received_dict = {(r['receiver__account__type'], r['receiver__asset__symbol']): r['amount'] for r in received}
    sent_dict = {(r['sender__account__type'], r['sender__asset__symbol']): r['amount'] for r in sent}

    keys = set(received_dict.keys()) | set(sent_dict.keys())
    total_dict = {}

    for key in keys:
        total_dict[key] = received_dict.get(key, 0) - sent_dict.get(key, 0)

    return total_dict


def get_internal_asset_deposits():
    deposits = CryptoBalance.objects.values('asset__symbol').annotate(amount=Sum('amount'))

    return {
        d['asset__symbol']: d['amount'] for d in deposits
    }


class AssetOverview:
    def __init__(self):
        self._future = BinanceFuturesHandler.get_account_details()

        self._future_positions = {
            pos['symbol']: pos for pos in self._future['positions']
        }

        self._user_type_asset_balances = get_ledger_user_type_asset_balances()

        self._user_type_balances = defaultdict(int)
        for key, amount in self._user_type_asset_balances.items():
            self._user_type_balances[key[0]] += amount

        self._prices = get_prices_dict(
            coins=list(Asset.candid_objects.values_list('symbol', flat=True)),
            side=SELL
        )

        self._usdt_irt = get_tether_irt_price(SELL)

        balances_list = BinanceSpotHandler.get_account_details()['balances']
        self._binance_spot_balance_map = {b['asset']: float(b['free']) for b in balances_list}

        self._internal_deposits = get_internal_asset_deposits()

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
        return self.total_margin_balance / max(self.total_initial_margin, 1e-10)

    def get_ledger_balance(self, user_type: str, asset: Asset = None):
        if asset:
            return self._user_type_asset_balances.get((user_type, asset.symbol), 0)
        else:
            return self._user_type_balances[user_type]

    def get_internal_deposits_balance(self, asset: Asset) -> Decimal:
        return self._internal_deposits.get(asset.symbol, 0)

    def get_future_position_amount(self, asset: Asset):
        symbol = get_binance_trading_symbol(asset.future_symbol)
        amount = float(self._future_positions.get(symbol, {}).get('positionAmt', 0))

        if asset.symbol == Asset.SHIB:
            amount *= 1000

        return amount

    def get_binance_spot_amount(self, asset: Asset) -> float:
        return self._binance_spot_balance_map.get(asset.symbol, 0)

    def get_binance_spot_total_value(self) -> float:
        value = 0

        for symbol, amount in self._binance_spot_balance_map.items():
            if amount > 0:
                value += Decimal(amount) * (self._prices.get(symbol) or 0)

        return value

    def get_future_position_value(self, asset: Asset):
        return float(self._future_positions.get(get_binance_trading_symbol(asset.future_symbol), {}).get('notional', 0))

    def get_total_assets(self, asset: Asset):
        if asset.symbol == Asset.IRT:
            return -asset.get_wallet(Account.out()).get_balance()
        else:
            return self.get_binance_balance(asset) + self.get_internal_deposits_balance(asset)

    def get_hedge_amount(self, asset: Asset):
        # Hedge = Real assets - Promised assets to users (user)
        return self.get_total_assets(asset) - self.get_ledger_balance(Account.ORDINARY, asset)

    def get_internal_usdt_value(self):
        total = 0

        for symbol, amount in self._internal_deposits.items():
            total += amount * (self._prices.get(symbol) or 0)

        return total

    def get_hedge_value(self, asset: Asset):
        price = self._prices.get(asset.symbol)
        if price is None:
            return None

        return Decimal(self.get_hedge_amount(asset)) * price

    def get_total_hedge_value(self):
        return sum([
            abs(self.get_hedge_value(asset) or 0) for asset in Asset.objects.exclude(hedge_method=Asset.HEDGE_NONE)
        ])

    def get_binance_balance(self, asset: Asset) -> Decimal:
        future_amount = Decimal(self.get_future_position_amount(asset))
        spot_amount = Decimal(self.get_binance_spot_amount(asset))

        return future_amount + spot_amount
