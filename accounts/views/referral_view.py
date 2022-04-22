from decimal import Decimal
import logging

from django.db.models import Q, DateField, Case, When, F, Sum
from django.db.models.functions import Cast
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from accounts.models import Referral, User
from market.models import ReferralTrx

logger = logging.getLogger(__name__)


class ReferralSerializer(serializers.ModelSerializer):
    revenue = serializers.SerializerMethodField()

    def get_revenue(self, referral: Referral):
        account = self.context['account']
        if referral.owner == account:
            revenue = ReferralTrx.objects.filter(referral=referral).aggregate(total=Sum('referrer_amount'))
        else:
            revenue = ReferralTrx.objects.filter(trader=account).aggregate(total=Sum('trader_amount'))
        return revenue['total'] or Decimal(0)

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
        fields = ('id', 'owner', 'created', 'code', 'owner_share_percent', 'revenue')
        read_only_fields = ('id', 'created', 'code', 'revenue')
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
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    serializer_class = ReferralSerializer

    def get_queryset(self):
        # if self.action == 'list':
        #     return Referral.objects.filter(owner=self.request.user.account).union(
        #         Referral.objects.filter(id=self.request.user.account.referred_by_id)
        #     )
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


class ReferralReportAPIView(ListAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

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