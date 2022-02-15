from collections import defaultdict

from django.db.models import Sum

from ledger.models import Trx, Asset
from provider.exchanges import BinanceFuturesHandler


def get_user_type_asset_balances():

    received = Trx.objects.values('receiver__account__type', 'receiver__asset').annotate(amount=Sum('amount'))
    sent = Trx.objects.values('sender__account__type', 'sender__asset').annotate(amount=Sum('amount'))

    received_dict = {(r['receiver__account__type'], r['receiver__asset']): r['amount'] for r in received}
    sent_dict = {(r['sender__account__type'], r['sender__asset']): r['amount'] for r in sent}

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

    def get_user_type_asset_balance(self, user_type: str, asset: Asset):
        return self._user_type_asset_balances[user_type, asset.symbol]

    def get_user_type_balance(self, user_type: str):
        return self._user_type_balances[user_type]

    def get_future_position_amount(self, asset: Asset):
        return float(self._future_positions.get(asset.symbol + 'USDT', {}).get('positionAmt', 0))

    def get_future_position_value(self, asset: Asset):
        return float(self._future_positions.get(asset.symbol + 'USDT', {}).get('notional', 0))
