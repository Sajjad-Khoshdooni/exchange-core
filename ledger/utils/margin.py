from dataclasses import dataclass
from decimal import Decimal

from accounts.models import Account
from ledger.models import Wallet, Asset
from ledger.utils.price import SELL, BUY


TRANSFER_OUT_BLOCK_ML = Decimal('2')
BORROW_BLOCK_ML = Decimal('1.5')  # leverage = 3
MARGIN_CALL_ML_THRESHOLD = Decimal('1.35')
LIQUIDATION_ML_THRESHOLD = Decimal('1.15')


@dataclass
class MarginInfo:
    total_debt: Decimal
    total_assets: Decimal

    @classmethod
    def get(cls, account: Account) -> 'MarginInfo':
        total_debt, total_assets = get_total_debt(account), get_total_assets(account)

        return MarginInfo(
            total_debt=total_debt,
            total_assets=total_assets
        )

    def get_margin_level(self) -> Decimal:
        return get_margin_level(self.total_assets, self.total_debt)

    def get_total_equity(self):
        return self.total_assets - self.total_debt

    def get_max_borrowable(self) -> Decimal:
        return (self.total_assets - BORROW_BLOCK_ML * self.total_debt) / (BORROW_BLOCK_ML - 1)

    def get_max_transferable(self) -> Decimal:
        return (self.total_assets - BORROW_BLOCK_ML * self.total_debt) / (BORROW_BLOCK_ML - 1)


def get_total_debt(account: Account) -> Decimal:
    return account.get_total_balance_usdt(Wallet.BORROW, SELL)


def get_total_assets(account: Account) -> Decimal:
    return account.get_total_balance_usdt(Wallet.MARGIN, BUY)


def get_margin_level(total_assets: Decimal, total_debt: Decimal):
    if total_debt <= 0:
        return Decimal(999)
    else:
        return total_assets / total_debt
