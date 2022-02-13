from django.core.validators import RegexValidator
from django.db import models

from accounts.models import User
from accounts.validators import iban_validator, bank_card_number_validator
from rest_framework import serializers


class BankCard(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(to=User, on_delete=models.PROTECT)

    name = models.CharField(max_length=256)
    card_number = models.CharField(
        verbose_name='شماره کارت',
        max_length=20,
        validators=[bank_card_number_validator],
        unique=True,
    )
    iban = models.CharField(
        max_length=26,
        validators=[iban_validator],
        unique=True,
        verbose_name='شبا'
    )
    verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'کارت بانکی'
        verbose_name_plural = 'کارت‌های بانکی'


class BankCardSerializer(serializers.ModelSerializer):

    class Meta:
        model = BankCard
        fields = ('id', 'name', 'card_number', 'iban', 'verified')
        read_only_fields = ('verified', )
