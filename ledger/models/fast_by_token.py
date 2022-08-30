from django.db import models
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import get_presentation_amount


class FastBuyToken(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, verbose_name='کاربر')
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE)
    amount = get_amount_field()
    price = get_amount_field()
    payment_request = models.ForeignKey('financial.PaymentRequest', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')

    def __str__(self):
        return str(get_presentation_amount(self.amount)) + ' ' + self.asset.symbol