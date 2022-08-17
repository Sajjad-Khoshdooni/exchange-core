from django.db import models
from django.db.models import Sum

from ledger.utils.fields import get_amount_field


class Investment(models.Model):
    SELF, TRADE, STAKE = 'self', 'trade', 'stake'
    created = models.DateTimeField(auto_now_add=True)

    title = models.CharField(max_length=32)
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    done = models.BooleanField(default=False)
    type = models.CharField(max_length=16, default=SELF, choices=((SELF, SELF), (TRADE, TRADE), (STAKE, STAKE)))

    exclude_from_total_assets = models.BooleanField(default=False)

    description = models.TextField(blank=True)

    class Meta:
        verbose_name = verbose_name_plural = 'سرمایه‌گذاری'

    def __str__(self):
        return '%s %s' % (self.title, self.asset)

    def get_base_amount(self):
        return InvestmentRevenue.objects.filter(
            investment=self, revenue=False
        ).aggregate(revenue=Sum('amount'))['revenue'] or 0

    def get_revenue_amount(self):
        return InvestmentRevenue.objects.filter(
            investment=self, revenue=True
        ).aggregate(revenue=Sum('amount'))['revenue'] or 0

    def get_total_amount(self):
        return InvestmentRevenue.objects.filter(
            investment=self
        ).aggregate(revenue=Sum('amount'))['revenue'] or 0


class InvestmentRevenue(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    investment = models.ForeignKey(Investment, on_delete=models.CASCADE)
    amount = get_amount_field(validators=())
    description = models.CharField(blank=True, max_length=256)
    revenue = models.BooleanField(default=False)

    class Meta:
        verbose_name = verbose_name_plural = 'درآمد سرمایه‌گذاری'
