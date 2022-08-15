from django.conf import settings
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet
from yekta_config.config import config

from accounts.models import User
from accounts.utils.similarity import clean_persian_name
from financial.models.bank_card import BankCard, BankCardSerializer
from financial.validators import bank_card_pan_validator


class CardPanField(serializers.CharField):
    def to_representation(self, value):
        if value:
            return BankCardSerializer(instance=value).data

    def get_attribute(self, user: User):
        return user.bankcard_set.filter(kyc=True).order_by('id').last()


class BasicInfoSerializer(serializers.ModelSerializer):
    card_pan = CardPanField(validators=[bank_card_pan_validator])
    reason = serializers.SerializerMethodField()

    def get_reason(self, user: User):
        if user.verify_status == User.REJECTED and user.level == User.LEVEL1:

            if user.reject_reason == User.NATIONAL_CODE_DUPLICATED:
                return 'کد ملی تکراری است. لطفا به پنل اصلی‌تان وارد شوید. در صورتی که می‌خواهید کد ملی‌تان را عوض کنید با پشتیبانی صحبت کنید.'

            if not user.birth_date_verified:
                return 'کد ملی،‌ شماره کارت و تاریخ تولد متعلق به یک نفر نیستند.'

            if not user.first_name_verified or not user.last_name_verified:
                return 'نام و نام خانوادگی با دیگر اطلاعات مغایر است.'

    def update_bank_card(self, user: User, card_pan: str):
        if BankCard.live_objects.filter(user=user, kyc=True, verified=True).exclude(card_pan=card_pan):
            raise ValidationError({'card_pan': 'امکان تغییر شماره کارت تایید شده وجود ندارد.'})

        bank_card = BankCard.live_objects.filter(user=user, kyc=True).first()

        if bank_card and bank_card.card_pan != card_pan:
            BankCard.live_objects.filter(user=user, card_pan=card_pan).update(deleted=True)

            bank_card.card_pan = card_pan
            bank_card.save()

        elif not bank_card:
            bank_card, _ = BankCard.live_objects.update_or_create(user=user, card_pan=card_pan, defaults={'kyc': True})

        if not bank_card.verified:
            bank_card.verified = None
            bank_card.save()

    def update(self, user, validated_data):
        if user and user.verify_status in (User.PENDING, User.VERIFIED):
            raise ValidationError('امکان تغییر اطلاعات وجود ندارد.')

        if user.level > User.LEVEL1:
            raise ValidationError('کاربر تایید شده است.')

        if user.national_code_verified is False:
            raise ValidationError('کد ملی شما رد شده است. برای ارتقای حساب با پشتیبانی صحبت کنید.')

        date_delta = timezone.now().date() - validated_data['birth_date']
        age = date_delta.days / 365

        if age < 18:
            raise ValidationError('سن باید بالای ۱۸ سال باشد.')
        elif age > 120:
            raise ValidationError('تاریخ تولد نامعتبر است.')

        card_pan = validated_data.pop('card_pan')
        self.update_bank_card(user, card_pan)

        if not user.national_code_verified:
            user.national_code = validated_data['national_code']
            user.national_code_verified = None

        if not user.first_name_verified:
            user.first_name = clean_persian_name(validated_data['first_name'])
            user.first_name_verified = None

        if not user.last_name_verified:
            user.last_name = clean_persian_name(validated_data['last_name'])
            user.last_name_verified = None

        if not user.birth_date_verified:
            user.birth_date = validated_data['birth_date']
            user.birth_date_verified = None

        user.save()
        user.change_status(User.PENDING)

        if User.objects.filter(level__gte=User.LEVEL2, national_code=user.national_code).exclude(id=user.id):
            user.national_code_verified = False
            user.save(update_fields=['national_code_verified'])
            user.change_status(User.REJECTED, User.NATIONAL_CODE_DUPLICATED)

            raise ValidationError('کد ملی تکراری است. لطفا به پنل اصلی‌تان وارد شوید.')
        else:
            from accounts.tasks import basic_verify_user

            if not settings.DEBUG_OR_TESTING:
                basic_verify_user.s(user.id).apply_async(countdown=config('KYC_DELAY', cast=int, default=60))

        return user

    class Meta:
        model = User
        fields = (
            'verify_status', 'level', 'first_name', 'last_name', 'birth_date', 'national_code', 'card_pan',
            'national_code_verified', 'first_name_verified', 'last_name_verified', 'birth_date_verified', 'reason'
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
