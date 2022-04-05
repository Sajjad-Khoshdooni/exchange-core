from django.db import models
from .asset import Asset
from .network import Network
from accounts.models import Account


class AddressBook(models.Model):

    name = models.CharField(max_length=100, verbose_name='نام')
    address = models.CharField(max_length=100, verbose_name='آدرس')
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE, verbose_name='کاربر')
    network = models.ForeignKey(to=Network, on_delete=models.CASCADE, verbose_name='شبکه')
    asset = models.ForeignKey(to=Asset, blank=True, null=True, on_delete=models.CASCADE, verbose_name='رمزارز')
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'دفترچه آدرس‌ها'
        verbose_name_plural = 'دفترچه‌های آدرس'
