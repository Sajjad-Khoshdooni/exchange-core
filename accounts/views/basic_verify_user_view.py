from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from accounts.models import User
from financial.models.bank_card import BankCard, BankCardSerializer
from financial.validators import bank_card_pan_validator


class CardPanField(serializers.CharField):
    def to_representation(self, value):
        if value:
            return BankCardSerializer(instance=value).data

    def get_attribute(self, user: User):
        return BankCard.live_objects.filter(user=user).order_by('verified', 'id').first()


class BasicInfoSerializer(serializers.ModelSerializer):
    card_pan = CardPanField(validators=[bank_card_pan_validator])

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

        if BankCard.live_objects.filter(card_pan=card_pan, verified=True).exclude(user=user).exists():
            raise ValidationError('این شماره کارت قبلا ثبت شده است.')

        bank_card = BankCard.live_objects.filter(user=user, card_pan=card_pan).first()

        if not bank_card:
            # new bank_card
            if BankCard.live_objects.filter(user=user, verified=True).exists():
                raise ValidationError('امکان تغییر شماره کارت تایید شده وجود ندارد.')

            BankCard.objects.create(user=user, card_pan=card_pan)

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

        user.save()
        user.change_status(User.PENDING)

        from accounts.tasks import basic_verify_user

        if not settings.DEBUG_OR_TESTING:
            basic_verify_user.s(user.id).apply_async(countdown=60)

        return user

    class Meta:
        model = User
        fields = (
            'verify_status', 'level', 'first_name', 'last_name', 'birth_date', 'national_code', 'card_pan',
            'first_name_verified', 'last_name_verified', 'birth_date_verified', 'national_code_verified',
        )
        read_only_fields = (
            'verify_status', 'level',
            'first_name_verified', 'last_name_verified', 'birth_date_verified', 'national_code_verified',
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'national_code': {'required': True},
            'birth_date': {'required': True},
        }


class BasicInfoVerificationViewSet(ModelViewSet):
    serializer_class = BasicInfoSerializer
    queryset = User.objects.all()

    def get_object(self):
        return self.request.user
