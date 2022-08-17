from decimal import Decimal

from django.db.models import Sum

from accounts.models import Account
from financial.models import InvestmentRevenue, FiatWithdrawRequest
from financial.utils.stats import get_total_fiat_irt
from ledger.models import Asset, Wallet, Transfer
from ledger.requester.internal_assets_requester import InternalAssetsRequester
from ledger.utils.price import SELL, get_prices_dict, get_tether_irt_price, BUY
from provider.exchanges import BinanceFuturesHandler, BinanceSpotHandler


def get_internal_asset_deposits():
    assets = InternalAssetsRequester().get_assets()
    return {
        asset['coin']: Decimal(asset['amount']) for asset in assets
    }


class AssetOverview:
    def __init__(self):
        self._future = BinanceFuturesHandler().get_account_details()

        self._future_positions = {
            pos['symbol']: pos for pos in self._future['positions']
        }

        wallets = Wallet.objects.filter(account__type=Account.ORDINARY).values('asset__symbol').annotate(amount=Sum('balance'))
        self._users_per_asset_balances = {w['asset__symbol']: w['amount'] for w in wallets}

        self.prices = get_prices_dict(
            coins=list(Asset.candid_objects.values_list('symbol', flat=True)),
            side=SELL
        )
        self.prices[Asset.IRT] = 1 / get_tether_irt_price(BUY)

        self.usdt_irt = get_tether_irt_price(SELL)

        balances_list = BinanceSpotHandler().get_account_details()['balances']
        self._binance_spot_balance_map = {b['asset']: float(b['free']) for b in balances_list}

        self._internal_deposits = get_internal_asset_deposits()

        self._investment = dict(
            InvestmentRevenue.objects.filter(
                investment__exclude_from_total_assets=False,
                investment__invested=True
            ).values('investment__asset__symbol').annotate(
                amount=Sum('amount')
            ).values_list('investment__asset__symbol', 'amount')
        )
        self._cash = dict(
            InvestmentRevenue.objects.filter(
                investment__exclude_from_total_assets=False,
                investment__invested=False
            ).values('investment__asset__symbol').annotate(
                amount=Sum('amount')
            ).values_list('investment__asset__symbol', 'amount')
        )

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

    def get_internal_deposits_balance(self, asset: Asset) -> Decimal:
        return self._internal_deposits.get(asset.symbol, 0)

    def get_futures_available_usdt(self):
        return self._future['availableBalance']

    def get_future_position_amount(self, asset: Asset):
        if asset.symbol == Asset.USDT:
            return self._future['availableBalance']

        if Asset.hedge_method == Asset.HEDGE_KUCOIN_SPOT:
            return

        handler = asset.get_hedger()
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
        handler = asset.get_hedger()
        return float(self._future_positions.get(handler.get_trading_symbol(asset.future_symbol), {}).get('notional', 0))

    def get_total_cash(self) -> Decimal:
        value = Decimal(0)

        for symbol, amount in self._cash.items():
            value += Decimal(amount) * (self.prices.get(symbol) or 0)

        return value

    def get_total_investment(self) -> Decimal:
        value = Decimal(0)

        for symbol, amount in self._investment.items():
            value += Decimal(amount) * (self.prices.get(symbol) or 0)

        return value

    def get_total_assets(self, asset: Asset):
        if asset.symbol == Asset.IRT:
            return get_total_fiat_irt()
        else:
            return self.get_binance_balance(asset) + \
                   self.get_internal_deposits_balance(asset)

    def get_hedge_amount(self, asset: Asset):
        # Hedge = Real assets - Promised assets to users (user)
        return self.get_total_assets(asset) - self._users_per_asset_balances.get(asset.symbol, 0)

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

    def get_users_asset_amount(self, asset: Asset) -> Decimal:
        return self._users_per_asset_balances.get(asset.symbol, 0)

    def get_users_asset_value(self, asset: Asset) -> Decimal:
        balance = self.get_users_asset_amount(asset)
        return balance * (self.prices.get(asset.symbol) or 0)

    def get_all_users_asset_value(self) -> Decimal:
        value = Decimal(0)

        for asset in Asset.candid_objects.all():
            value += self.get_users_asset_value(asset)

        pending_withdraws = FiatWithdrawRequest.objects.filter(
            status=FiatWithdrawRequest.PENDING
        ).aggregate(amount=Sum('amount'))['amount'] or 0

        return value - pending_withdraws / self.usdt_irt

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

    def get_all_assets_usdt(self):
        return float(self.get_binance_spot_total_value()) + self.total_margin_balance + \
               float(self.get_internal_usdt_value()) + self.get_fiat_usdt() + float(self.get_total_investment() + self.get_total_cash())

    def get_exchange_assets_usdt(self):
        return self.get_all_assets_usdt() - float(self.get_all_users_asset_value())

    def get_exchange_potential_usdt(self):
        value = Decimal(0)

        non_deposited = self.get_non_deposited_accounts_per_asset_balance()

        for symbol, balance in non_deposited.items():
            value += balance * (self.prices.get(symbol) or 0)

        return self.get_exchange_assets_usdt() + float(value)

    @classmethod
    def get_non_deposited_accounts_per_asset_balance(cls) -> dict:
        transferred_accounts = list(Transfer.objects.filter(deposit=True).values_list('wallet__account_id', flat=True))

        non_deposited_wallets = Wallet.objects.filter(
            account__type=Account.ORDINARY,
            account__user__first_fiat_deposit_date__isnull=True
        ).exclude(account__in=transferred_accounts).values('asset__symbol').annotate(amount=Sum('balance'))

        return {w['asset__symbol']: w['amount'] for w in non_deposited_wallets}
