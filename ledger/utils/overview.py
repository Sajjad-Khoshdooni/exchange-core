from decimal import Decimal

from django.db.models import Sum

from accounting.models import VaultItem
from accounts.models import Account
from financial.models import FiatWithdrawRequest
from ledger.margin.closer import MARGIN_INSURANCE_ACCOUNT
from ledger.models import Wallet, Prize, Asset
from ledger.requester.internal_assets_requester import InternalAssetsRequester
from ledger.utils.cache import cache_for
from ledger.utils.price import SELL, get_tether_irt_price, BUY, get_price
from ledger.utils.provider import get_provider_requester, BINANCE, CoinOrders


@cache_for(60)
def get_internal_asset_deposits() -> dict:
    assets = InternalAssetsRequester().get_assets()

    if not assets:
        return {}

    return {
        asset['coin']: Decimal(asset['amount']) for asset in assets
    }


class AssetOverview:
    def __init__(self, calculated_hedge: bool = False):
        self._coin_total_orders = None
        self.provider = get_provider_requester()

        if calculated_hedge:
            self._coin_total_orders = {
                coin_order.coin: coin_order for coin_order in self.provider.get_total_orders_amount_sum()
            }

        self._binance_futures = self.provider.get_futures_info(BINANCE)

        wallets = Wallet.objects.filter(
            account__type=Account.ORDINARY
        ).exclude(market__in=(Wallet.VOUCHER, Wallet.DEBT)).values('asset__symbol').annotate(amount=Sum('balance'))
        self.users_balances = {w['asset__symbol']: w['amount'] for w in wallets}

        self.usdt_irt = get_tether_irt_price(SELL)

        self.assets_map = {a.symbol: a for a in Asset.objects.all()}

    def get_calculated_hedge(self, coin: str):
        assert self._coin_total_orders is not None
        coin_orders = self._coin_total_orders.get(coin, CoinOrders(coin=coin, buy=Decimal(), sell=Decimal()))
        return self.provider.get_hedge_amount(self.assets_map[coin], coin_orders)

    def get_binance_margin_ratio(self):
        margin_balance = float(self._binance_futures['total_margin_balance'])
        initial_margin = float(self._binance_futures['total_initial_margin'])
        return margin_balance / max(initial_margin, 1e-10)

    def get_real_assets(self, coin: str):
        return VaultItem.objects.filter(coin=coin).aggregate(balance=Sum('balance'))['balance'] or 0

    def get_all_real_assets_value(self):
        return VaultItem.objects.aggregate(value=Sum('value_usdt'))['value'] or 0

    def get_hedge_amount(self, coin: str):
        return self.get_real_assets(coin) - self.users_balances.get(coin, 0)

    def get_hedge_value(self, coin: str) -> Decimal:
        amount = Decimal(self.get_hedge_amount(coin))

        if not amount:
            return Decimal(0)

        price = get_price(coin=coin, side=BUY) or 0
        return amount * price

    def get_users_asset_amount(self, coin: str) -> Decimal:
        return self.users_balances.get(coin, 0)

    def get_users_asset_value(self, coin: str) -> Decimal:
        balance = self.get_users_asset_amount(coin)

        if not balance:
            return Decimal(0)

        price = get_price(coin=coin, side=BUY) or 0
        
        return balance * price

    def get_all_users_asset_value(self) -> Decimal:
        value = Decimal(0)

        for coin, balance in self.users_balances.items():
            value += self.get_users_asset_value(coin)

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
            abs(self.get_hedge_value(asset.symbol) or 0) for asset in Asset.live_objects.filter(hedge=True)
        ])

    def get_exchange_assets_usdt(self):
        return self.get_all_real_assets_value() - self.get_all_users_asset_value()

    def get_exchange_potential_usdt(self):
        value = Decimal(0)

        non_deposited = self.get_non_deposited_accounts_per_asset_balance()

        for coin, balance in non_deposited.items():
            price = get_price(coin=coin, side=BUY) or 0
            value += balance * price

        return self.get_exchange_assets_usdt() + value

    @classmethod
    def get_non_deposited_accounts_per_asset_balance(cls) -> dict:
        non_deposited_wallets = Wallet.objects.filter(
            account__type=Account.ORDINARY,
            account__user__first_fiat_deposit_date__isnull=True,
            account__user__first_crypto_deposit_date__isnull=True,
        ).exclude(
            market=Wallet.VOUCHER
        ).values('asset__symbol').annotate(amount=Sum('balance'))

        return {w['asset__symbol']: w['amount'] for w in non_deposited_wallets}

    def get_margin_insurance_balance(self):
        return Asset.get(Asset.USDT).get_wallet(MARGIN_INSURANCE_ACCOUNT).balance
