from django.db import models, IntegrityError
from django.db.models import UniqueConstraint, Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from financial.validators import iban_validator, bank_card_pan_validator


class LiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)


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
    deleted = models.BooleanField(default=False)

    history = HistoricalRecords()

    objects = models.Manager()
    live_objects = LiveManager()

    def __str__(self):
        if len(self.card_pan) < 10:
            return self.card_pan

        return self.card_pan[:4] + '********' + self.card_pan[-4:]

    class Meta:
        verbose_name = 'کارت بانکی'
        verbose_name_plural = 'کارت‌های بانکی'


class BankAccount(models.Model):
    ACTIVE, DEPOSITABLE_SUSPENDED, NON_DEPOSITABLE_SUSPENDED, STAGNANT, UNKNOWN = 'active', 'suspend', 'nsuspend', 'stagnant', 'unknown'

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
    deleted = models.BooleanField(default=False)

    history = HistoricalRecords()

    objects = models.Manager()
    live_objects = LiveManager()

    def __str__(self):
        return self.iban[:6] + '********' + self.iban[-4:]

    class Meta:
        verbose_name = 'حساب بانکی'
        verbose_name_plural = 'حساب‌های بانکی'


class BankCardSerializer(serializers.ModelSerializer):

    class Meta:
        model = BankCard
        fields = ('id', 'card_pan', 'verified')
        read_only_fields = ('verified', )

    def create(self, validated_data: dict):
        user = validated_data['user']
        card_pan = validated_data['card_pan']

        if BankCard.live_objects.filter(Q(user=user) | Q(verified=True), card_pan=card_pan).exists():
            raise ValidationError('این شماره کارت قبلا ثبت شده است.')

        bank_card = super().create(validated_data)

        from financial.tasks.verify import verify_bank_card_task
        verify_bank_card_task.delay(bank_card.id)

        return bank_card


class BankAccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = BankAccount
        fields = ('id', 'iban', 'verified')
        read_only_fields = ('verified', )

    def create(self, validated_data: dict):
        user = validated_data['user']
        iban = validated_data['iban']

        if BankAccount.live_objects.filter(Q(user=user) | Q(verified=True), iban=iban).exists():
            raise ValidationError('این شماره شما قبلا ثبت شده است.')

        bank_account = super().create(validated_data)

        from financial.tasks.verify import verify_bank_account_task
        verify_bank_account_task.delay(bank_account.id)

        return bank_account
