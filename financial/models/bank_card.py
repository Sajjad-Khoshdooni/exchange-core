from django.db import models
from django.db.models import UniqueConstraint, Q
from rest_framework import serializers

from financial.validators import iban_validator, bank_card_pan_validator


class BankCard(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(to='accounts.User', on_delete=models.PROTECT)

    card_pan = models.CharField(
        verbose_name='شماره کارت',
        max_length=20,
        validators=[bank_card_pan_validator],
    )

    verified = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.card_pan

    class Meta:
        verbose_name = 'کارت بانکی'
        verbose_name_plural = 'کارت‌های بانکی'

        constraints = [
            UniqueConstraint(
                fields=["card_pan"],
                name="unique_bank_card_card_pan",
                condition=Q(verified=True),
            )
        ]


class BankAccount(models.Model):
    ACTIVE, DEPOSITABLE_SUSPENDED, NON_DEPOSITABLE_SUSPENDED, STAGNANT = 'active', 'suspend', 'nsuspend', 'stagnant'

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    user = models.ForeignKey(to='accounts.User', on_delete=models.PROTECT)

    iban = models.CharField(
        max_length=26,
        validators=[iban_validator],
        verbose_name='شبا'
    )

    bank_name = models.CharField(max_length=256, blank=True)
    deposit_address = models.CharField(max_length=64, blank=True)
    card_pan = models.CharField(max_length=20, blank=True)

    deposit_status = models.CharField(
        max_length=8,
        blank=True,
        choices=(
            (ACTIVE, 'active'), (DEPOSITABLE_SUSPENDED, 'suspend'), (NON_DEPOSITABLE_SUSPENDED, 'nodep suspend'),
            (STAGNANT, 'stagnant')
        )
    )

    owners = models.JSONField(blank=True, null=True)

    verified = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.iban

    class Meta:
        verbose_name = 'حساب بانکی'
        verbose_name_plural = 'حساب‌های بانکی'

        constraints = [
            UniqueConstraint(
                fields=["iban"],
                name="unique_bank_account_iban",
                condition=Q(verified=True),
            )
        ]


class BankCardSerializer(serializers.ModelSerializer):

    class Meta:
        model = BankCard
        fields = ('id', 'card_pan', 'verified')
        read_only_fields = ('verified', )


class BankAccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = BankAccount
        fields = ('id', 'iban', 'verified')
        read_only_fields = ('verified', )
