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
from rest_framework.viewsets import ModelViewSet

from accounts.models import Referral
from market.models import ReferralTrx

logger = logging.getLogger(__name__)


class ReferralSerializer(serializers.ModelSerializer):
    is_editable = serializers.SerializerMethodField()

    def get_is_editable(self, referral: Referral):
        return referral.owner == self.context['account']

    def to_internal_value(self, data):
        try:
            owner_share_percent = int(data['owner_share_percent'])
        except ValueError:
            raise ValidationError({'owner_share_percent': _('A valid integer is required.')})
        return super(ReferralSerializer, self).to_internal_value(
            {'owner_share_percent': owner_share_percent, 'owner': self.context['account'].id}
        )

    class Meta:
        model = Referral
        fields = ('id', 'owner', 'created', 'code', 'owner_share_percent', 'is_editable')
        read_only_fields = ('id', 'created', 'code', 'is_editable')
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


class ReferralViewSet(ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    serializer_class = ReferralSerializer

    def get_queryset(self):
        if self.action == 'list':
            return Referral.objects.filter(owner=self.request.user.account).union(
                Referral.objects.filter(id=self.request.user.account.referred_by_id)
            )
        return Referral.objects.filter(owner=self.request.user.account)

    def get_serializer_context(self):
        return {
            **super(ReferralViewSet, self).get_serializer_context(),
            'account': self.request.user.account
        }


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
