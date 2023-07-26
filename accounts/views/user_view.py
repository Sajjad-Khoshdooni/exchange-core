from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.core.exceptions import ValidationError

from accounts.models import VerificationCode
from accounts.models import User, CustomToken
from accounts.utils.hijack import get_hijacker_id
from accounts.verifiers.legal import possible_time_for_withdraw
from financial.models.bank_card import BankCardSerializer, BankAccountSerializer


class UserSerializer(serializers.ModelSerializer):
    possible_time_for_withdraw = serializers.SerializerMethodField()
    chat_uuid = serializers.CharField()
    show_staking = serializers.SerializerMethodField()
    is_auth2fa_active = serializers.SerializerMethodField()

    def get_chat_uuid(self, user: User):
        request = self.context['request']

        if get_hijacker_id(request):
            return ''
        else:
            return user.chat_uuid

    def get_is_auth2fa_active(self, user: User):
        device = TOTPDevice.objects.filter(user=user).first()
        is_active = device is not None and device.confirmed
        return is_active

    def get_show_staking(self, user: User):
        return True

    class Meta:
        model = User
        fields = (
            'id', 'phone', 'email', 'first_name', 'last_name', 'level', 'margin_quiz_pass_date', 'is_staff',
            'show_margin', 'show_strategy_bot', 'show_community', 'show_staking', 'possible_time_for_withdraw',
            'chat_uuid', 'is_auth2fa_active',
        )
        ref_name = "User"

    def get_possible_time_for_withdraw(self, user: User):
        return possible_time_for_withdraw(user)


class ProfileSerializer(UserSerializer):
    bank_cards = serializers.SerializerMethodField()
    bank_accounts = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = UserSerializer.Meta.fields + (
            'national_code', 'birth_date', 'level',
            'national_code_verified', 'first_name_verified', 'last_name_verified', 'birth_date_verified',
            'verify_status', 'bank_cards', 'bank_accounts'
        )

    def get_bank_cards(self, user: User):
        return BankCardSerializer(instance=user.bankcard_set.all(), many=True).data

    def get_bank_accounts(self, user: User):
        return BankAccountSerializer(instance=user.bankaccount_set.all(), many=True).data


class UserDetailView(RetrieveAPIView):
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.request.query_params.get('profile') == '1':
            return ProfileSerializer
        else:
            return UserSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({'user': serializer.data})

    def get_object(self):
        return self.request.user


class AuthTokenSerializer(serializers.ModelSerializer):
    ip_list = serializers.CharField()
    sms_code = serializers.CharField(write_only=True, required=True)
    totp = serializers.CharField(allow_null=True, allow_blank=True, required=False)

    class Meta:
        model = CustomToken
        fields = ('ip_list', 'sms_code', 'totp')

    def validate(self, data):
        user = self.context['request'].user
        totp = data.get('totp')
        sms_code = data.get('sms_code')
        sms_code_verified = VerificationCode.get_by_code(sms_code, user.phone, VerificationCode.API_TOKEN, user)
        device = TOTPDevice.objects.filter(user=user).first()
        if not sms_code_verified:
            raise ValidationError({'code': 'کد نامعتبر است.'})
        if not (device is None or not device.confirmed or device.verify_token(totp)):
            raise ValidationError({'token': 'رمز موقت صحیح نمی‌باشد.'})
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        customtoken = CustomToken.objects.create(**validated_data)

        return customtoken

    def update(self, instance, validated_data):
        instance.ip_list = validated_data['ip_list']

        instance.save()
        return instance


class CreateAuthToken(APIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    serializer_class = AuthTokenSerializer

    def get(self, request):
        custom_token = get_object_or_404(CustomToken, user=request.user)
        return Response({
            'token': ('*' * (len(custom_token.key) - 4)) + custom_token.key[-4:],
            'user_id': request.user.pk,
            'ip_white_list': custom_token.ip_list
        })

    def post(self, request):
        custom_token = CustomToken.objects.filter(user=request.user)
        if custom_token:
            custom_token = custom_token.get()
            return Response({
                'token': ('*' * (len(custom_token.key) - 4)) + custom_token.key[-4:],
                'user_id': request.user.pk,
                'ip_white_list': custom_token.ip_list,
            })
        else:
            auth_token_serializer = AuthTokenSerializer(
                data=request.data,
                context={'request': self.request}
            )
            auth_token_serializer.is_valid(raise_exception='data is invalid')
            auth_token_serializer.save()
            token = CustomToken.objects.get(user=request.user)
            return Response({
                'token': token.key,
                'user_id': request.user.pk,
                'ip_white_list': token.ip_list,
            })

    def delete(self, request, *args, **kwargs):
        token = get_object_or_404(CustomToken, user=request.user)
        token.delete()
        return Response({'msg': 'Token deleted successfully'})

    def put(self, request):
        tokent = get_object_or_404(CustomToken, user=request.user)
        token_serializer = AuthTokenSerializer(
            instance=tokent,
            data=request.data,
            partial=True
        )
        if token_serializer.is_valid():
            token_serializer.save()
            return Response({'message': 'token updated successfully!'})

        return Response({'message': token_serializer.errors})
