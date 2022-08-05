from django.db import models
from django.db.models import Sum

from ledger.utils.fields import get_amount_field


class Investment(models.Model):
    SELF, TRADE, STAKE = 'self', 'trade', 'stake'
    created = models.DateTimeField(auto_now_add=True)

    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    amount = get_amount_field(validators=())
    done = models.BooleanField(default=False)
    type = models.CharField(max_length=16, default=SELF, choices=((SELF, SELF), (TRADE, TRADE), (STAKE, STAKE)))

    description = models.TextField(blank=True)

    class Meta:
        verbose_name = verbose_name_plural = 'سرمایه‌گذاری'

    def __str__(self):
        return '%s %s' % (self.asset, self.amount)

    def get_revenue(self):
        return InvestmentRevenue.objects.filter(investment=self).aggregate(revenue=Sum('amount'))['revenue'] or 0

    def get_total_amount(self):
        return self.amount + self.get_revenue()


class InvestmentRevenue(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    investment = models.ForeignKey(Investment, on_delete=models.CASCADE)
    amount = get_amount_field()
    description = models.CharField(blank=True, max_length=256)

    class Meta:
        verbose_name = verbose_name_plural = 'درآمد سرمایه‌گذاری'
