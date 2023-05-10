import logging
import random

from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from decouple import config

from accounts.models import User, TrafficSource, Referral
from accounts.models.phone_verification import VerificationCode
from accounts.throttle import BurstRateThrottle, SustainedRateThrottle
from accounts.utils.ip import get_client_ip
from accounts.utils.validation import set_login_activity
from accounts.validators import mobile_number_validator, password_validator
from experiment.models.experiment import Experiment
from experiment.models.link import Link
from experiment.models.variant import Variant
from experiment.models.variant_user import VariantUser
from experiment.utils.exceptions import TokenCreationError


logger = logging.getLogger(__name__)


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
    source = serializers.CharField(allow_null=True, required=False, write_only=True, allow_blank=True)

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
        promotion = validated_data.get('promotion') or ''

        user = User.objects.create_user(
            username=phone,
            phone=phone,
            promotion=promotion
        )

        with transaction.atomic():
            if not config('ENABLE_MARGIN_SHOW_TO_ALL', cast=bool, default=True):
                user.show_margin = False

            if config('SHOW_NINJA_TO_ALL', cast=bool, default=False):
                user.show_community = True

            user.set_password(password)
            user.save()

            if validated_data.get('referral_code'):
                account = user.get_account()
                account.referred_by = Referral.objects.get(code=validated_data['referral_code'])
                account.save()

                from gamify.utils import check_prize_achievements, Task
                check_prize_achievements(account.referred_by.owner, Task.REFERRAL)

            # otp_code.set_token_used()

        utm = validated_data.get('utm') or {}

        self.create_traffic_source(user, utm)

        try:
            self.user_experiment_assign(user)
        except Exception as e:
            logger.exception(
                'Experiment assigning failed',
                extra={
                    'exp': e,
                    'user': user
                }
            )

        return user

    def create_traffic_source(self, user, utm: dict):
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
        )

    @classmethod
    def user_experiment_assign(cls, user):
        for experiment in Experiment.objects.filter(active=True):
            variant_list = Variant.objects.filter(experiment=experiment).order_by('id')
            variant = variant_list[random.randint(0, 1)]  # todo :: generalize

            if variant is None:
                return

            link = None
            if variant.type == Variant.SMS_NOTIF:
                try:
                    link = Link.create(user=user)
                except TokenCreationError:
                    logger.info('TokenCreationError', extra={
                        'user': user.id
                    })
                    return

            VariantUser.objects.create(
                variant=variant,
                user=user,
                link=link
            )


class SignupView(CreateAPIView):
    permission_classes = []
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]
    serializer_class = SignupSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        login(self.request, user)
        set_login_activity(
            request=self.request,
            user=user,
            is_sign_up=True,
            native_app=serializer.validated_data.get('source') == 'app'
        )
