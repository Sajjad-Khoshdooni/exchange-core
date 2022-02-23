from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from accounts.models import User
from financial.models.bank_card import BankCard, BankCardSerializer, BankAccountSerializer, BankAccount
from financial.validators import bank_card_pan_validator, iban_validator


class CardPanField(serializers.CharField):
    def to_representation(self, value):
        if value:
            return BankCardSerializer(instance=value).data

    def get_attribute(self, user: User):
        return BankCard.objects.filter(user=user).order_by('-verified', 'id').first()


class IbanField(serializers.CharField):
    def to_representation(self, value):
        if value:
            return BankAccountSerializer(instance=value).data

    def get_attribute(self, user: User):
        return BankAccount.objects.filter(user=user).order_by('-verified', 'id').first()


class BasicInfoSerializer(serializers.ModelSerializer):
    card_pan = CardPanField(validators=[bank_card_pan_validator])
    iban = IbanField(validators=[iban_validator])

    def update(self, user, validated_data):
        if user and user.verify_status in (User.PENDING, User.VERIFIED):
            raise ValidationError('امکان تغییر اطلاعات وجود ندارد.')

        if user.level > User.LEVEL1:
            raise ValidationError('کاربر تایید شده است.')

        date_delta = timezone.now().date() - validated_data['birth_date']
        age = date_delta.days / 365

        if age < 18:
            raise ValidationError('سن باید بالای ۱۸ سال باشد.')
        elif age > 120:
            raise ValidationError('تاریخ تولد نامعتبر است.')

        card_pan = validated_data.pop('card_pan')
        iban = validated_data.pop('iban')

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

        if not user.national_code_verified:
            user.national_code = validated_data['national_code']
            user.national_code_verified = None

        if not user.first_name_verified:
            user.first_name = validated_data['first_name']
            user.first_name_verified = None
            
        if not user.last_name_verified:
            user.last_name = validated_data['last_name']
            user.last_name_verified = None
            
        if not user.birth_date_verified:
            user.birth_date = validated_data['birth_date']
            user.birth_date_verified = None

        user.change_status(User.PENDING)

        from accounts.tasks import basic_verify_user
        basic_verify_user.s(user.id).apply_async(countdown=60)
        # basic_verify_user(user.id)

        return user

    class Meta:
        model = User
        fields = (
            'verify_status', 'first_name', 'last_name', 'birth_date', 'national_code', 'card_pan', 'iban',
            'first_name_verified', 'last_name_verified', 'birth_date_verified', 'national_code_verified'
        )
        read_only_fields = (
            'verify_status', 'first_name_verified', 'last_name_verified', 'birth_date_verified', 'national_code_verified'
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'national_code': {'required': True},
            'birth_date': {'required': True},
        }


class BasicInfoVerificationViewSet(ModelViewSet):
    serializer_class = BasicInfoSerializer

    def get_object(self):
        return self.request.user
