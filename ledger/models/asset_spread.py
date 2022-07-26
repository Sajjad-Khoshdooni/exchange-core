from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from ledger.utils.fields import get_amount_field


class AssetSpreadCategory(models.Model):
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return self.name


class CategorySpread(models.Model):
    BUY, SELL = 'buy', 'sell'
    SIDE_CHOICES = [(BUY, BUY), (SELL, SELL)]
    DEFAULT_SPREAD = Decimal('0.25')

    category = models.ForeignKey(AssetSpreadCategory, null=True, blank=True, on_delete=models.CASCADE)
    side = models.CharField(max_length=8, choices=SIDE_CHOICES)

    step = models.PositiveIntegerField(
        choices=[(1, '0$ - 3$'), (2, '3$ - 10$'), (3, '10$ - 1000$'), (4, '1000$ - 2000$'), (5, '> 2000$')],
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    spread = get_amount_field(
        default=DEFAULT_SPREAD,
        validators=(MinValueValidator(Decimal('0.1')), MaxValueValidator(10))
    )

    def __str__(self):
        return '%s %s step: %s = %s' % (self.category, self.side, self.step, self.spread)

    class Meta:
        unique_together = [
            ('category', 'side', 'step')
        ]

    @classmethod
    def get_step(cls, value: Decimal = None) -> int:
        if not value or value <= 3:
            return 1
        elif value <= 10:
            return 2
        elif value <= 1000:
            return 3
        elif value <= 2000:
            return 4
        else:
            return 5
