import logging
from decimal import Decimal

from django.db.models import Q, DateField, Case, When, F, Sum
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from accounts.models import Referral, User, Account
from market.models import ReferralTrx

logger = logging.getLogger(__name__)


class ReferralSerializer(serializers.ModelSerializer):
    revenue = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    def get_revenue(self, referral: Referral):
        revenue = ReferralTrx.objects.filter(referral=referral).aggregate(total=Sum('referrer_amount'))
        return int(revenue['total'])

    def get_members(self, referral: Referral):
        return Account.objects.filter(referred_by=referral).count()

    def to_internal_value(self, data):
        try:
            owner_share_percent = int(data['owner_share_percent'])
        except ValueError:
            raise ValidationError({'owner_share_percent': _('A valid integer is required.')})
        return super(ReferralSerializer, self).to_internal_value(
            {'owner_share_percent': owner_share_percent, 'owner': self.context['account'].id}
        )

    @staticmethod
    def validate_owner_share_percent(value):
        if value < 0:
            raise ValidationError(_('Invalid share percent'))

        if value > ReferralTrx.REFERRAL_MAX_RETURN_PERCENT:
            raise ValidationError(_('Input value is greater than {max_percent}').format(max_percent=ReferralTrx.REFERRAL_MAX_RETURN_PERCENT))
        return value

    class Meta:
        model = Referral
        fields = ('id', 'owner', 'created', 'code', 'owner_share_percent', 'revenue', 'members')
        read_only_fields = ('id', 'created', 'code')
        extra_kwargs = {
            'owner': {'write_only': True},
        }


class ReferralTrxSerializer(serializers.Serializer):
    date = serializers.DateField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=0)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ReferralViewSet(
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        GenericViewSet):

    serializer_class = ReferralSerializer

    def get_queryset(self):
        return Referral.objects.filter(owner=self.request.user.account)

    def get_serializer_context(self):
        return {
            **super(ReferralViewSet, self).get_serializer_context(),
            'account': self.request.user.account
        }

    def perform_create(self, serializer):
        if self.request.user.level < User.LEVEL2:
            raise ValidationError('برای ساخت کد معرف، ابتدا باید احراز هویت سطح دو را انجام دهید.')

        serializer.save()


class ReferralOverviewAPIView(APIView):

    def get(self, request):

        account = request.user.account

        members = Account.objects.filter(referred_by__owner=account).count()
        referred_revenue = ReferralTrx.objects.filter(
            trader=account
        ).aggregate(total=Sum('trader_amount'))['total'] or 0

        referral_revenue = ReferralTrx.objects.filter(
            referral__owner=account
        ).aggregate(total=Sum('referrer_amount'))['total'] or 0

        return Response({
            'members': members,
            'referred_revenue': int(referred_revenue),
            'referral_revenue': int(referral_revenue),
            'total_revenue': int(referred_revenue + referral_revenue)
        })


class ReferralReportAPIView(ListAPIView):
    serializer_class = ReferralTrxSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['referral']

    def get_queryset(self):
        qs = ReferralTrx.objects.filter(
            Q(referral__owner=self.request.user.account) | Q(trader=self.request.user.account)
        ).annotate(
            date=Cast('created', DateField()),
            received_amount=Case(
                When(trader=self.request.user.account, then=F('trader_amount')),
                When(referral__owner=self.request.user.account, then=F('referrer_amount'))
            )
        ).values('date').annotate(amount=Sum('received_amount'))
        return qs
