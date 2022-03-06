from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.viewsets import ModelViewSet

from accounts.models import User, VerificationCode
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from multimedia.fields import ImageField


class FullVerificationSerializer(serializers.ModelSerializer):
    national_card_image = ImageField()
    selfie_image = ImageField()

    def update(self, user, validated_data):
        if user and user.verify_status in (User.PENDING, User.VERIFIED):
            raise ValidationError('امکان تغییر اطلاعات وجود ندارد.')

        if user.level > User.LEVEL2:
            raise ValidationError('کاربر تایید شده است.')

        need_manual = False
        need_telephone_otp = False

        if not user.telephone_verified:
            user.telephone = validated_data['telephone']
            user.telephone_verified = None
            need_telephone_otp = True

        if not user.national_card_image_verified:
            user.national_card_image = validated_data['national_card_image']
            user.national_card_image_verified = None

            need_manual = True

        if not user.selfie_image_verified:
            user.selfie_image = validated_data['selfie_image']
            user.selfie_image_verified = None

            need_manual = True

        user.change_status(User.PENDING)

        if need_manual:
            link = url_to_edit_object(user)
            send_support_message(
                message='لطفا کاربر را برای احراز هویت کامل بررسی کنید.',
                link=link
            )

        if need_telephone_otp and user.telephone:
            VerificationCode.send_otp_code(user.telephone, scope=VerificationCode.SCOPE_TELEPHONE)

        return user

    class Meta:
        fields = (
            'verify_status', 'level', 'telephone', 'national_card_image', 'selfie_image',
            'telephone_verified', 'national_card_image_verified', 'selfie_image_verified',
        )
        model = User
        read_only_fields = (
            'verify_status', 'level', 'telephone_verified', 'national_card_image_verified', 'selfie_image_verified',
        )
        extra_kwargs = {
            'telephone': {'required': True},
            'national_card_image': {'required': True},
            'selfie_image': {'required': True},
        }


class FullVerificationViewSet(ModelViewSet):
    serializer_class = FullVerificationSerializer

    def get_object(self):
        return self.request.user


class TelephoneOTPSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        code = validated_data['code']
        user = validated_data['user']

        otp_code = VerificationCode.get_by_code(code=code, phone=user.telephone, scope=VerificationCode.SCOPE_TELEPHONE)

        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است.'})

        otp_code.code_used = True
        otp_code.save()

        user.telephone_verified = True
        user.save()

        return otp_code

    class Meta:
        model = VerificationCode
        fields = ('code', 'scope')
        read_only_fields = ('scope', )

        extra_kwargs = {
            'code': {'required': True},
        }


class TelephoneOTPView(CreateAPIView):
    serializer_class = TelephoneOTPSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
