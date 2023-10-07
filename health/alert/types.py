from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from ledger.models import Transfer


@dataclass
class Status:
    IDLE, WARNING, ERROR = 'idle', 'warning', 'error'

    status: str
    count: int = 0

    def __str__(self):
        if self.status == self.IDLE:
            return self.IDLE.upper()

        return f'{self.status.upper()} {self.count}'


class BaseAlertHandler:
    NAME = None

    def __init__(self, warning_threshold: Decimal, error_threshold: Decimal):
        self.warning_threshold = warning_threshold
        self.error_threshold = error_threshold

    def get_status(self) -> Status:
        error_count = self.is_alerting(self.error_threshold)
        if error_count:
            return Status(Status.ERROR, error_count)

        warning_count = self.is_alerting(self.warning_threshold)
        if warning_count:
            return Status(Status.WARNING, count=warning_count)

        return Status(Status.IDLE)

    def is_alerting(self, threshold: Decimal):
        raise NotImplemented


class UnhandledCryptoWithdraw(BaseAlertHandler):
    NAME = 'unhandled_crypto_withdraw'

    def is_alerting(self, threshold: Decimal):
        return Transfer.objects.filter(
            status__in=[Transfer.PROCESSING, Transfer.PENDING],
            created__lt=timezone.now() - timedelta(minutes=int(threshold)),
        ).exists()


_ALERT_TYPES = [UnhandledCryptoWithdraw, ]

ALERTS = {t.NAME: t for t in _ALERT_TYPES}
