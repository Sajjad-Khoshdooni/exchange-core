from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet
from yekta_config.config import config

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
    reason = serializers.SerializerMethodField()

    def get_reason(self, user: User):
        if user.verify_status == User.REJECTED and user.level == User.LEVEL1:

            if not user.birth_date_verified:
                return 'کد ملی،‌ شماره کارت و تاریخ تولد متعلق به یک نفر نیستند.'

            if not user.first_name_verified or not user.last_name_verified:
                return 'نام و نام خانوادگی با دیگر اطلاعات مغایر است.'

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

        bank_card = BankCard.live_objects.filter(user=user, card_pan=card_pan).first()

        if not bank_card:
            # new bank_card
            if BankCard.live_objects.filter(user=user, verified=True).exists():
                raise ValidationError('امکان تغییر شماره کارت تایید شده وجود ندارد.')

            BankCard.objects.create(user=user, card_pan=card_pan)

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
            basic_verify_user.s(user.id).apply_async(countdown=config('KYC_DELAY', cast=int, default=60))

        return user

    class Meta:
        model = User
        fields = (
            'verify_status', 'level', 'first_name', 'last_name', 'birth_date', 'national_code', 'card_pan',
            'first_name_verified', 'last_name_verified', 'birth_date_verified', 'reason'
        )
        read_only_fields = (
            'verify_status', 'level',
            'first_name_verified', 'last_name_verified', 'birth_date_verified'
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
