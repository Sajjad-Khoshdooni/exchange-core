from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from yekta_config.config import config

from accounts.models import User, TrafficSource, Referral
from accounts.models.phone_verification import VerificationCode
from accounts.throttle import BurstRateThrottle, SustainedRateThrottle
from accounts.utils.ip import get_client_ip
from accounts.utils.validation import set_login_activity
from accounts.validators import mobile_number_validator, password_validator


class InitiateSignupSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True, validators=[mobile_number_validator], trim_whitespace=True)


class InitiateSignupView(APIView):
    permission_classes = []
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]

    def post(self, request):
        print('signup/init app ip: %s' % get_client_ip(request))

        if request.user.is_authenticated:
            return Response({'msg': 'already logged in', 'code': 1})

        serializer = InitiateSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']

        VerificationCode.send_otp_code(phone, VerificationCode.SCOPE_VERIFY_PHONE)

        return Response({'msg': 'otp sent', 'code': 0})


class SignupSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    token = serializers.UUIDField(write_only=True, required=True)
    password = serializers.CharField(required=True, write_only=True, validators=[password_validator])
    utm = serializers.JSONField(allow_null=True, required=False, write_only=True)
    referral_code = serializers.CharField(allow_null=True, required=False, write_only=True, allow_blank=True)
    promotion = serializers.CharField(allow_null=True, required=False, write_only=True, allow_blank=True)

    @staticmethod
    def validate_referral_code(code):
        if code and not Referral.objects.filter(code=code).exists():
            raise ValidationError(_('Referral code is invalid'))
        return code

    def create(self, validated_data):
        token = validated_data.pop('token')
        otp_code = VerificationCode.get_by_token(token, VerificationCode.SCOPE_VERIFY_PHONE)
        password = validated_data.pop('password')

        if not otp_code:
            raise ValidationError({'token': 'توکن نامعتبر است.'})

        if User.objects.filter(phone=otp_code.phone).exists():
            raise ValidationError({'phone': 'شما قبلا در سیستم ثبت‌نام کرده‌اید. لطفا از قسمت ورود، وارد شوید.'})

        validate_password(password=password)

        phone = otp_code.phone
        # otp_code.set_token_used()

        user = User.objects.create_user(
            username=phone,
            phone=phone,
        )

        with transaction.atomic():
            if not config('ENABLE_MARGIN_SHOW_TO_ALL', cast=bool, default=True):
                user.show_margin = False

            user.set_password(password)
            user.save()

            if validated_data.get('referral_code'):
                user.account.referred_by = Referral.objects.get(code=validated_data['referral_code'])
                user.account.save()

                from gamify.utils import check_prize_achievements, Task
                check_prize_achievements(user.account.referred_by.owner, Task.REFERRAL)

            # otp_code.set_token_used()

        utm = validated_data.get('utm') or {}
        promotion = validated_data.get('promotion') or ''

        self.create_traffic_source(user, utm, promotion)

        return user

    def create_traffic_source(self, user, utm: dict, promotion: str):
        utm_source = utm.get('utm_source', '')[:256]

        if not utm_source:
            return

        utm_medium = utm.get('utm_medium', '')[:256]
        utm_campaign = utm.get('utm_campaign', '')[:256]
        utm_content = utm.get('utm_content', '')[:256]
        utm_term = utm.get('utm_term', '')[:256]
        gps_adid = utm.get('gps_adid', '')[:256]

        if utm_source == 'pwa_app':
            if utm_term.startswith('gclid'):
                utm_medium = 'google_ads'
            elif 'google-play' in utm_term and 'organic' in utm_term:
                utm_medium = 'organic'
                utm_content = 'google_play'
            elif not gps_adid:
                utm_medium = 'organic'
            else:
                from accounts.models import Attribution

                attribution = Attribution.objects.filter(gps_adid=gps_adid).order_by('created').last()

                if not attribution or not attribution.tracker_code:
                    utm_medium = 'organic'
                else:
                    utm_medium = attribution.network_name
                    utm_campaign = attribution.campaign_name
                    utm_content = attribution.adgroup_name
                    utm_term = attribution.creative_name

        TrafficSource.objects.create(
            user=user,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            gps_adid=gps_adid,
            ip=get_client_ip(self.context['request']),
            user_agent=self.context['request'].META['HTTP_USER_AGENT'][:256],
            promotion=promotion,
        )


class SignupView(CreateAPIView):
    permission_classes = []
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]
    serializer_class = SignupSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        login(self.request, user)
        set_login_activity(self.request, user, is_sign_up=True)
