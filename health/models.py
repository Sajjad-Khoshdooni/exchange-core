from typing import Type

from django.db import models

from health.alert.types import ALERTS, Status, BaseAlertHandler
from ledger.utils.fields import get_amount_field


class AlertType(models.Model):

    type = models.CharField(max_length=32, choices=[(t, t) for t in ALERTS])
    warning_threshold = get_amount_field(default=0)
    error_threshold = get_amount_field(default=0)

    def get_status(self) -> Status:
        alert_class = ALERTS[self.type]  # type: Type[BaseAlertHandler]
        alert = alert_class(self.warning_threshold, self.error_threshold)
        return alert.get_status()

    def __str__(self):
        return f'{self.type} warning_th = {self.warning_threshold}, error_th = {self.error_threshold}'


class AlertChange:
    pass
    # IDLE, WARNING, ERROR =

    # status =
