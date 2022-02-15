from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework import serializers

from accounts.models import BasicAccountInfo
from financial.validators import bank_card_pan_validator, iban_validator
from financial.models.bank_card import BankCard, BankCardSerializer, BankAccountSerializer, BankAccount
from multimedia.fields import ImageField


class BankCardListSerializer(serializers.ListSerializer):
    child = BankCardSerializer()


class CardPanField(serializers.CharField):
    def to_representation(self, value):
        if value:
            return BankCardSerializer(instance=value).data

    def get_attribute(self, instance: BasicAccountInfo):
        return BankCard.objects.filter(user=instance.user).order_by('-verified', 'id').first()


class IbanField(serializers.CharField):
    def to_representation(self, value):
        if value:
            return BankAccountSerializer(instance=value).data

    def get_attribute(self, instance: BasicAccountInfo):
        return BankAccount.objects.filter(user=instance.user).order_by('-verified', 'id').first()


class BasicInfoSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    national_card_image = ImageField()
    card_pan = CardPanField(validators=[bank_card_pan_validator])
    iban = IbanField(validators=[iban_validator])

    def save(self, user):
        instance = self.instance

        if instance and instance.status in (BasicAccountInfo.PENDING, BasicAccountInfo.VERIFIED):
            raise ValidationError('امکان تغییر اطلاعات وجود ندارد.')

        date_delta = timezone.now().date() - self.validated_data['birth_date']
        age = date_delta.days / 365

        if age < 18:
            raise ValidationError('سن باید بالای ۱۸ سال باشد.')
        elif age > 120:
            raise ValidationError('تاریخ تولد نامعتبر است.')

        card_pan = self.validated_data['card_pan']
        iban = self.validated_data['iban']

        bank_card = BankCard.objects.filter(user=user, card_pan=card_pan).first()
        bank_account = BankAccount.objects.filter(user=user, iban=iban).first()

        if not bank_card:
            # new bank_card
            if BankCard.objects.filter(user=user, verified=True).exists():
                raise ValidationError('امکان تغییر شماره کارت تایید شده وجود ندارد.')

            BankCard.objects.filter(user=user).delete()
            BankCard.objects.create(user=user, card_pan=card_pan)

        if not bank_account:
            # new bank_card
            if BankAccount.objects.filter(user=user, verified=True).exists():
                raise ValidationError('امکان تغییر شماره شبای تایید شده وجود ندارد.')

            BankAccount.objects.filter(user=user).delete()
            BankAccount.objects.create(user=user, iban=iban)

        with transaction.atomic():
            user.first_name = self.validated_data['user']['first_name']
            user.last_name = self.validated_data['user']['last_name']
            user.save()

            instance = super().save(user=user)

        return instance

    class Meta:
        model = BasicAccountInfo
        fields = ('status', 'first_name', 'last_name', 'gender', 'birth_date', 'national_card_code',
                  'national_card_image', 'card_pan', 'iban')

        read_only_fields = ('status', )


class BasicInfoVerificationViewSet(ModelViewSet):
    serializer_class = BasicInfoSerializer

    def get_object(self):
        user = self.request.user
        return BasicAccountInfo.objects.filter(user=user).first()

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)


class VerifySearchLine(APIView):

    def get(self, request):
        return Response('ok!')
