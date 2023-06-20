from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.authentication import CustomTokenAuthentication
from accounts.throttle import BursAPIRateThrottle, SustainedAPIRateThrottle
from ledger.models import Transfer
from ledger.views.transactions_history_view import TransferSerializer


class WithdrawViewSet(ModelViewSet):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    throttle_classes = [BursAPIRateThrottle, SustainedAPIRateThrottle]

    serializer_class = TransferSerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def perform_destroy(self, transfer: Transfer):
        if transfer.status != Transfer.INIT and not transfer.in_freeze_time():
            raise ValidationError({'status': 'زمان لازم برای لغو برداشت تمام شده است.'})

        transfer.reject()

    def get_queryset(self):
        return Transfer.objects.filter(
            deposit=False,
            wallet__account=self.request.user.get_account(),
        ).order_by('-created')
