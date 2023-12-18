from uuid import uuid4

from django.db import models
from rest_framework import serializers

from accounts.models import Account
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset, Wallet, Trx
from ledger.utils.fields import get_amount_field
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import PairSymbol

BORROW, REPAY, OPEN = 'borrow', 'repay', 'open'


class MarginTransfer(models.Model):
    SPOT_TO_MARGIN = 'sm'
    MARGIN_TO_SPOT = 'ms'
    MARGIN_TO_POSITION = 'mp'
    POSITION_TO_MARGIN = 'pm'

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)

    amount = get_amount_field()

    type = models.CharField(
        max_length=2,
        choices=(
            (SPOT_TO_MARGIN, 'spot to margin'), (MARGIN_TO_SPOT, 'margin to spot'),
            (MARGIN_TO_POSITION, 'margin to position'), (POSITION_TO_MARGIN, 'position to margin')),
    )

    asset = models.ForeignKey(to=Asset, on_delete=models.PROTECT)
    position_symbol = models.ForeignKey(to=PairSymbol, null=True, blank=True, on_delete=models.PROTECT)

    group_id = models.UUIDField(default=uuid4)

    def save(self, *args, **kwargs):
        spot_wallet = self.asset.get_wallet(self.account, Wallet.SPOT)
        margin_wallet = self.asset.get_wallet(self.account, Wallet.MARGIN)
        position_wallet = position = None

        if self.type in (self.MARGIN_TO_POSITION, self.POSITION_TO_MARGIN):
            if not self.position_symbol:
                raise ValueError('position_symbol is required')
            from ledger.models import MarginPosition
            position = MarginPosition.objects.filter(
                account=self.account,
                symbol=self.position_symbol,
                status=MarginPosition.OPEN
            ).first()
            if not position:
                raise ValueError('No open position found for this symbol')
            position_wallet = self.asset.get_wallet(self.account, Wallet.MARGIN, position.group_id)

        from ledger.models import MarginHistoryModel
        if self.type == self.SPOT_TO_MARGIN:
            sender, receiver = spot_wallet, margin_wallet
            MarginHistoryModel.objects.create(
                asset=self.asset,
                amount=self.amount,
                group_id=self.group_id,
                type=MarginHistoryModel.POSITION_TRANSFER
            )

        elif self.type == self.MARGIN_TO_SPOT:
            sender, receiver = margin_wallet, spot_wallet
            MarginHistoryModel.objects.create(
                asset=self.asset,
                amount=-self.amount,
                group_id=self.group_id,
                type=MarginHistoryModel.POSITION_TRANSFER
            )

        elif self.type == self.MARGIN_TO_POSITION:
            sender, receiver = margin_wallet, position_wallet

            position.equity += self.amount

        elif self.type == self.POSITION_TO_MARGIN:
            sender, receiver = position_wallet, margin_wallet
            if position.withdrawable_base_asset < self.amount:
                raise InsufficientBalance

            position.equity -= self.amount
        else:
            raise NotImplementedError

        sender.has_balance(self.amount, raise_exception=True)

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            super(MarginTransfer, self).save(*args)
            pipeline.new_trx(sender, receiver, self.amount, Trx.MARGIN_TRANSFER, self.group_id)
            if position:
                position.set_liquidation_price(pipeline)
                position.save(update_fields=['equity', 'liquidation_price'])


class SymbolField(serializers.CharField):
    def to_representation(self, value: PairSymbol):
        if value:
            return value.name

    def to_internal_value(self, data: str):
        if not data:
            return
        else:
            return PairSymbol.get_by(name=data)
