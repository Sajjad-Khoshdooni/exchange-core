import logging

from django.core.validators import RegexValidator, MaxValueValidator, MinValueValidator
from django.db import models

from accounts.utils.validation import generate_random_code

logger = logging.getLogger(__name__)


class Referral(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    owner = models.ForeignKey(
        to='accounts.Account',
        on_delete=models.CASCADE,
    )

    code = models.CharField(
        max_length=8,
        validators=[RegexValidator(r'^\d{4,8}$')],
        unique=True
    )

    owner_share_percent = models.SmallIntegerField(default=100,
                                                   validators=[MinValueValidator(0), MaxValueValidator(100)])

    def save(self, **kwargs):
        if not self.id:
            self.code = generate_random_code(6)
        return super(Referral, self).save(**kwargs)
