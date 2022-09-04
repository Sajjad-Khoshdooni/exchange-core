from django.db import models
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import humanize_number


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
