from decimal import Decimal

from django.db.models import Sum

from accounts.models import Account
from financial.models import InvestmentRevenue, FiatWithdrawRequest
from financial.utils.stats import get_total_fiat_irt
from ledger.margin.closer import MARGIN_INSURANCE_ACCOUNT
from ledger.models import Asset, Wallet, Transfer, Prize
from ledger.requester.internal_assets_requester import InternalAssetsRequester
from ledger.utils.cache import cache_for
from ledger.utils.price import SELL, get_prices_dict, get_tether_irt_price, BUY, PriceFetchError
from ledger.utils.provider import get_provider_requester, BINANCE, KUCOIN, MEXC, CoinOrders


@cache_for(60)
def get_internal_asset_deposits() -> dict:
    assets = InternalAssetsRequester().get_assets()

    if not assets:
        return {}

    return {
        asset['coin']: Decimal(asset['amount']) for asset in assets
    }


class AssetOverview:
    def __init__(self, strict: bool = True, calculated_hedge: bool = False):
        self._strict = strict
        self._coin_total_orders = None
        self.provider = get_provider_requester()

        if calculated_hedge:
            self._coin_total_orders = {
                coin_order.coin: coin_order for coin_order in self.provider.get_total_orders_amount_sum()
            }

        self._binance_futures = self.provider.get_futures_info(BINANCE)
        self._disabled_assets = set(Asset.objects.filter(enable=False).values_list('symbol', flat=True))

        self._future_positions = {
            pos['coin']: pos for pos in self._binance_futures.get('positions', [])
        }

        self._binance_spot_balance_map = self.provider.get_spot_balance_map(BINANCE)
        self._kucoin_spot_balance_map = self.provider.get_spot_balance_map(KUCOIN)
        self._mexc_spot_balance_map = self.provider.get_spot_balance_map(MEXC)

        wallets = Wallet.objects.filter(
            account__type=Account.ORDINARY
        ).exclude(market=Wallet.VOUCHER).values('asset__symbol').annotate(amount=Sum('balance'))
        self._users_per_asset_balances = {w['asset__symbol']: w['amount'] for w in wallets}

        self._valid_symbols = set(Asset.objects.filter(enable=True).values_list('symbol', flat=True))

        self.prices = get_prices_dict(
            coins=list(Asset.live_objects.values_list('symbol', flat=True)),
            side=SELL,
            allow_stale=True
        )
        self.prices[Asset.IRT] = 1 / get_tether_irt_price(BUY)

        self.usdt_irt = get_tether_irt_price(SELL)

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

        self._hedged_investment = dict(
            InvestmentRevenue.objects.filter(
                investment__hedged=True,
                investment__exclude_from_total_assets=False,
                investment__invested=True
            ).values('investment__asset__symbol').annotate(
                amount=Sum('amount')
            ).values_list('investment__asset__symbol', 'amount')
        )
        self._hedged_cash = dict(
            InvestmentRevenue.objects.filter(
                investment__hedged=True,
                investment__exclude_from_total_assets=False,
                investment__invested=False
            ).values('investment__asset__symbol').annotate(
                amount=Sum('amount')
            ).values_list('investment__asset__symbol', 'amount')
        )

    @property
    def total_initial_margin(self):
        return float(self._binance_futures['total_initial_margin'])

    @property
    def total_maintenance_margin(self):
        return float(self._binance_futures['total_maint_margin'])

    @property
    def total_margin_balance(self):
        return float(self._binance_futures['total_margin_balance'])

    def get_calculated_hedge(self, asset: Asset):
        assert self._coin_total_orders is not None
        coin_orders = self._coin_total_orders.get(asset.symbol, CoinOrders(coin=asset.symbol, buy=Decimal(), sell=Decimal()))
        return self.provider.get_hedge_amount(asset, coin_orders)

    def get_price(self, symbol: str) -> Decimal:
        if symbol in self._disabled_assets:
            return Decimal(0)

        price = self.prices.get(symbol)

        if self._strict and price is None:
            raise PriceFetchError(symbol)

        return price or 0

    @property
    def margin_ratio(self):
        return self.total_margin_balance / max(self.total_initial_margin, 1e-10)

    def get_internal_deposits_balance(self, asset: Asset) -> Decimal:
        return self._internal_deposits.get(asset.symbol, 0)

    def get_futures_available_usdt(self):
        return self._binance_futures['available_balance']

    def get_future_position_amount(self, asset: Asset):
        return self._future_positions.get(asset.symbol, {}).get('balance', 0)

    def get_binance_spot_amount(self, asset: Asset) -> float:
        return self._binance_spot_balance_map.get(asset.symbol, 0)

    def get_kucoin_spot_amount(self, asset: Asset) -> float:
        return self._kucoin_spot_balance_map.get(asset.symbol, 0)

    def get_mexc_spot_amount(self, asset: Asset) ->float:
        return self._mexc_spot_balance_map.get(asset.symbol, 0)

    def get_binance_spot_total_value(self) -> Decimal:
        value = Decimal(0)

        for symbol, amount in self._binance_spot_balance_map.items():
            if amount > 0:
                value += Decimal(amount) * (self.prices.get(symbol) or 0)

        return value

    def get_kucoin_spot_total_value(self) -> Decimal:
        value = Decimal(0)
        for symbol, amount in self._kucoin_spot_balance_map.items():
            if amount > 0:
                value += Decimal(amount) * (self.prices.get(symbol) or 0)

        return value

    def get_mexc_spot_total_value(self) -> Decimal:
        value = Decimal(0)
        for symbol, amount in self._mexc_spot_balance_map.items():
            if amount > 0:
                value += Decimal(amount) * (self.prices.get(symbol) or 0)
        return value

    def get_future_position_value(self, asset: Asset):
        return float(self._future_positions.get(asset.symbol, {}).get('notional', 0))

    def get_total_cash(self) -> Decimal:
        value = Decimal(0)

        for symbol, amount in self._cash.items():
            value += Decimal(amount) * self.get_price(symbol)

        return value

    def get_hedged_investment_amount(self, asset: Asset) -> Decimal:
        return self._hedged_investment.get(asset.symbol, 0)

    def get_hedged_cash_amount(self, asset: Asset) -> Decimal:
        return self._hedged_cash.get(asset.symbol, 0)

    def get_total_investment(self) -> Decimal:
        value = Decimal(0)

        for symbol, amount in self._investment.items():
            value += Decimal(amount) * self.get_price(symbol)

        return value

    def get_total_assets(self, asset: Asset):
        if asset.symbol == Asset.IRT:
            assets = get_total_fiat_irt()
        else:
            assets = self.get_provider_balance(asset) + \
                   self.get_internal_deposits_balance(asset)

        assets += self.get_hedged_investment_amount(asset) + self.get_hedged_cash_amount(asset)

        return assets

    def get_hedge_amount(self, asset: Asset):
        # Hedge = Real assets - Promised assets to users (user)
        return self.get_total_assets(asset) - self._users_per_asset_balances.get(asset.symbol, 0)

    def get_internal_usdt_value(self) -> Decimal:
        total = Decimal(0)

        for symbol, amount in self._internal_deposits.items():
            if symbol not in self._valid_symbols or not amount:
                continue

            total += amount * self.get_price(symbol)

        return total

    def get_hedge_value(self, asset: Asset) -> Decimal:
        amount = Decimal(self.get_hedge_amount(asset))

        if not amount:
            return Decimal(0)

        return amount * self.get_price(asset.symbol)

    def get_users_asset_amount(self, asset: Asset) -> Decimal:
        return self._users_per_asset_balances.get(asset.symbol, 0)

    def get_users_asset_value(self, asset: Asset) -> Decimal:
        balance = self.get_users_asset_amount(asset)

        if not balance:
            return Decimal(0)

        return balance * self.get_price(asset.symbol)

    def get_all_users_asset_value(self) -> Decimal:
        value = Decimal(0)

        for asset in Asset.live_objects.all():
            value += self.get_users_asset_value(asset)

        pending_withdraws = FiatWithdrawRequest.objects.filter(
            status=FiatWithdrawRequest.PENDING
        ).aggregate(amount=Sum('amount'))['amount'] or 0

        return value - pending_withdraws / self.usdt_irt

    def get_all_prize_value(self) -> Decimal:
        return Prize.objects.filter(
            redeemed=True
        ).aggregate(value=Sum('value'))['value'] or 0

    def get_total_hedge_value(self):
        return sum([
            abs(self.get_hedge_value(asset) or 0) for asset in Asset.live_objects.filter(hedge=True)
        ])

    def get_cumulated_hedge_value(self):
        return abs(sum([
            self.get_hedge_value(asset) for asset in Asset.live_objects.filter(hedge=True)
        ]))

    def get_binance_balance(self, asset: Asset) -> Decimal:
        future_amount = Decimal(self.get_future_position_amount(asset))
        spot_amount = Decimal(self.get_binance_spot_amount(asset))

        return future_amount + spot_amount

    def get_kucoin_balance(self, asset: Asset) -> Decimal:
        spot_amount = Decimal(self.get_kucoin_spot_amount(asset))
        return spot_amount

    def get_mexc_balance(self, asset: Asset) -> Decimal:
        sot_amount = Decimal(self.get_mexc_spot_amount(asset))
        return sot_amount

    def get_provider_balance(self, asset: Asset) -> Decimal:
        return self.get_binance_balance(asset) + self.get_kucoin_balance(asset) + self.get_mexc_balance(asset)

    def get_fiat_irt(self):
        return self.get_total_assets(Asset.get(Asset.IRT))

    def get_fiat_usdt(self) -> float:
        return float(self.get_fiat_irt() / self.usdt_irt)

    def get_gateway_usdt(self):
        return get_total_fiat_irt(self._strict) / self.usdt_irt

    def get_all_assets_usdt(self):
        return float(self.get_binance_spot_total_value()) + self.total_margin_balance + \
               float(self.get_internal_usdt_value()) + float(self.get_gateway_usdt()) + \
               float(self.get_total_investment() + self.get_total_cash()) + \
               float(self.get_kucoin_spot_total_value()) + \
               float(self.get_mexc_spot_total_value())

    def get_exchange_assets_usdt(self):
        return self.get_all_assets_usdt() - float(self.get_all_users_asset_value())

    def get_exchange_potential_usdt(self):
        value = Decimal(0)

        non_deposited = self.get_non_deposited_accounts_per_asset_balance()

        for symbol, balance in non_deposited.items():
            value += balance * self.get_price(symbol)

        return self.get_exchange_assets_usdt() + float(value)

    @classmethod
    def get_non_deposited_accounts_per_asset_balance(cls) -> dict:
        transferred_accounts = list(Transfer.objects.filter(deposit=True).values_list('wallet__account_id', flat=True))

        non_deposited_wallets = Wallet.objects.filter(
            account__type=Account.ORDINARY,
            account__user__first_fiat_deposit_date__isnull=True
        ).exclude(account__in=transferred_accounts).values('asset__symbol').annotate(amount=Sum('balance'))

        return {w['asset__symbol']: w['amount'] for w in non_deposited_wallets}

    def get_margin_insurance_balance(self):
        return Asset.get(Asset.USDT).get_wallet(MARGIN_INSURANCE_ACCOUNT).balance
