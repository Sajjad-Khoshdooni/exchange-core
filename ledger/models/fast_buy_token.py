from django.db import models
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import get_presentation_amount


class FastBuyToken(models.Model):
    PROCESS, DEPOSIT, DONE = 'process', 'deposit', 'done'
    MIN_ADMISSIBLE_VALUE = 300000

    CHOICE_STATUS = ((PROCESS, PROCESS), (DEPOSIT, DEPOSIT), (DONE, DONE))

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, verbose_name='کاربر')
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE)
    amount = get_amount_field()
    price = get_amount_field()
    payment_request = models.OneToOneField('financial.PaymentRequest', on_delete=models.CASCADE)
    otc_request = models.OneToOneField('OTCRequest', on_delete=models.CASCADE, null=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    status = models.CharField(max_length=16, choices=CHOICE_STATUS, default=PROCESS)

    class Meta:
        verbose_name = verbose_name_plural = 'خرید سریع رمزارز'

    def __str__(self):
        return str(get_presentation_amount(self.amount)) + ' ' + self.asset.symbol