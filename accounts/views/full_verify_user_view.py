from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet
from accounts.models import User
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from multimedia.fields import ImageField


class FullVerificationSerializer(serializers.ModelSerializer):
    selfie_image = ImageField()

    def update(self, user, validated_data):
        if user and user.verify_status in (User.PENDING, User.VERIFIED):
            raise ValidationError('امکان تغییر اطلاعات وجود ندارد.')

        if user.level >= User.LEVEL3:
            raise ValidationError('کاربر تایید شده است.')

        need_manual = False

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

        # if need_telephone_otp and user.telephone:
        #     VerificationCode.send_otp_code(user.telephone, scope=VerificationCode.SCOPE_TELEPHONE)

        return user

    class Meta:
        fields = (
            'verify_status', 'level', 'telephone', 'selfie_image',
            'telephone_verified', 'selfie_image_verified',
        )
        model = User
        read_only_fields = (
            'verify_status', 'level', 'selfie_image_verified', 'telephone_verified', 'telephone'
        )
        extra_kwargs = {
            'selfie_image': {'required': True},
        }


class FullVerificationViewSet(ModelViewSet):
    serializer_class = FullVerificationSerializer

    def get_object(self):
        return self.request.user
