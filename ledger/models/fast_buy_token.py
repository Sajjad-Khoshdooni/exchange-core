import logging
from decimal import Decimal

from django.db import models

from accounts.models import Notification
from financial.models.payment import Payment
from ledger.models import OTCRequest, Asset, Wallet, OTCTrade
from ledger.utils.fields import DONE
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import humanize_number

logger = logging.getLogger(__name__)


class FastBuyToken(models.Model):
    PROCESS, DEPOSIT, DONE = 'process', 'deposit', 'done'
    MIN_ADMISSIBLE_VALUE = 300_000

    CHOICE_STATUS = ((PROCESS, PROCESS), (DEPOSIT, DEPOSIT), (DONE, DONE))

    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    status = models.CharField(max_length=16, choices=CHOICE_STATUS, default=PROCESS)
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    price = get_amount_field()

    payment_request = models.OneToOneField('financial.PaymentRequest', on_delete=models.CASCADE)
    otc_request = models.OneToOneField('OTCRequest', on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = verbose_name_plural = 'خرید سریع رمزارز'

    def __str__(self):
        return '%s %s %s' % (self.payment_request.bank_card, self.asset, humanize_number(self.amount))

    @property
    def user(self):
        return self.payment_request.bank_card.user

    def create_otc_for_fast_buy_token(self, payment: Payment):

        self.status = FastBuyToken.DEPOSIT
        self.save(update_fields=['status'])
        if payment.status == DONE:
            otc_request = OTCRequest.new_trade(
                account=self.user.account,
                from_asset=Asset.get('IRT'),
                to_asset=self.asset,
                from_amount=Decimal(self.amount),
                market=Wallet.SPOT,
            )
            self.otc_request = otc_request
            self.save(update_fields=['otc_request'])

            try:
                otc_trade = OTCTrade.execute_trade(otc_request)
                self.status = FastBuyToken.DONE
                self.save(update_fields=['status'])

                Notification.send(
                    recipient=self.user,
                    title='خرید رمز ارز.',
                    message='خرید {} {} با موفقیت انجام شد.'.format(self.asset.symbol, self.amount),
                    level=Notification.SUCCESS
                )
                return otc_trade
            except Exception as exp:
                logger.exception('Error in create otc_trade for fast_buy', extra={
                    'exp': exp
                })
