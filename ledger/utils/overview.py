from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum, F

from accounts.models import Account
from financial.models import ManualTransferHistory
from financial.utils.stats import get_total_fiat_irt
from ledger.models import Asset, CryptoBalance, Wallet
from ledger.utils.price import SELL, get_prices_dict, get_tether_irt_price, BUY
from provider.exchanges import BinanceFuturesHandler, BinanceSpotHandler


def get_ledger_user_type_asset_balances():
    wallets = Wallet.objects.values('account__type', 'asset__symbol').annotate(amount=Sum('balance'))
    return {(w['account__type'], w['asset__symbol']): w['amount'] for w in wallets}


def get_internal_asset_deposits():
    deposits = CryptoBalance.objects.values('asset__symbol').annotate(amount=Sum('amount'))

    return {
        d['asset__symbol']: d['amount'] for d in deposits
    }


class AssetOverview:
    def __init__(self):
        self._future = BinanceFuturesHandler().get_account_details()

        self._future_positions = {
            pos['symbol']: pos for pos in self._future['positions']
        }

        self._user_type_asset_balances = get_ledger_user_type_asset_balances()

        self._user_type_balances = defaultdict(int)
        for key, amount in self._user_type_asset_balances.items():
            self._user_type_balances[key[0]] += amount

        self.prices = get_prices_dict(
            coins=list(Asset.candid_objects.values_list('symbol', flat=True)),
            side=SELL
        )
        self.prices[Asset.IRT] = 1 / get_tether_irt_price(BUY)

        self.usdt_irt = get_tether_irt_price(SELL)

        balances_list = BinanceSpotHandler().get_account_details()['balances']
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

    def get_ledger_balance(self, user_type: str, asset: Asset):
        return self._user_type_asset_balances.get((user_type, asset.symbol), 0)

    def get_internal_deposits_balance(self, asset: Asset) -> Decimal:
        return self._internal_deposits.get(asset.symbol, 0)

    def get_future_position_amount(self, asset: Asset):
        if Asset.hedge_method == Asset.HEDGE_KUCOIN_SPOT:
            return
        handler = Asset.get_hedger()
        symbol = handler.get_trading_symbol(asset.future_symbol)
        amount = float(self._future_positions.get(symbol, {}).get('positionAmt', 0))

        if asset.symbol == Asset.SHIB:
            amount *= 1000

        return amount

    def get_binance_spot_amount(self, asset: Asset) -> float:
        return self._binance_spot_balance_map.get(asset.symbol, 0)

    def get_binance_spot_total_value(self) -> Decimal:
        value = Decimal(0)

        for symbol, amount in self._binance_spot_balance_map.items():
            if amount > 0:
                value += Decimal(amount) * (self.prices.get(symbol) or 0)

        return value

    def get_future_position_value(self, asset: Asset):
        handler = Asset.get_hedger()
        return float(self._future_positions.get(handler.get_trading_symbol(asset.future_symbol), {}).get('notional', 0))

    def get_total_assets(self, asset: Asset):
        if asset.symbol == Asset.IRT:
            return get_total_fiat_irt()
        else:
            return self.get_binance_balance(asset) + self.get_internal_deposits_balance(asset)

    def get_hedge_amount(self, asset: Asset):
        # Hedge = Real assets - Promised assets to users (user)
        return self.get_total_assets(asset) - self.get_ledger_balance(Account.ORDINARY, asset)

    def get_internal_usdt_value(self) -> Decimal:
        total = Decimal(0)

        for symbol, amount in self._internal_deposits.items():
            total += amount * (self.prices.get(symbol) or 0)

        return total

    def get_hedge_value(self, asset: Asset):
        price = self.prices.get(asset.symbol)
        if price is None:
            return None

        return Decimal(self.get_hedge_amount(asset)) * price

    def get_users_asset_value(self, asset: Asset) -> Decimal:
        balance = self.get_ledger_balance(Account.ORDINARY, asset)
        return balance * (self.prices.get(asset.symbol) or 0)

    def get_all_users_asset_value(self) -> Decimal:
        value = Decimal(0)

        for asset in Asset.candid_objects.all():
            value += self.get_users_asset_value(asset)

        return value

    def get_total_hedge_value(self):
        return sum([
            abs(self.get_hedge_value(asset) or 0) for asset in Asset.objects.exclude(hedge_method=Asset.HEDGE_NONE)
        ])

    def get_binance_balance(self, asset: Asset) -> Decimal:
        future_amount = Decimal(self.get_future_position_amount(asset))
        spot_amount = Decimal(self.get_binance_spot_amount(asset))

        return future_amount + spot_amount

    def get_fiat_irt(self):
        return self.get_total_assets(Asset.get(Asset.IRT))

    def get_fiat_usdt(self) -> float:
        return float(self.get_fiat_irt() / self.usdt_irt)

    def get_promised_value(self):
        promised_value = 0

        for manual in ManualTransferHistory.objects.filter(done=False):
            value = self.prices[manual.asset.symbol] * max(manual.amount - manual.full_fill_amount, 0)

            if manual.deposit:
                promised_value += value
            else:
                promised_value -= value

        return promised_value

    def get_all_assets_usdt(self):
        return float(self.get_binance_spot_total_value()) + self.total_margin_balance + \
               float(self.get_internal_usdt_value()) + self.get_fiat_usdt() + float(self.get_promised_value())

    def get_exchange_assets_usdt(self):
        return self.get_all_assets_usdt() - float(self.get_all_users_asset_value())
